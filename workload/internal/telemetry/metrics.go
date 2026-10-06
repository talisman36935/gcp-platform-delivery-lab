// Package telemetry contains adapters only; domain/application code stays neutral.
package telemetry

import (
	"net/http"
	"strconv"
	"sync/atomic"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/collectors"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

type Metrics struct {
	registry         *prometheus.Registry
	role             string
	iterationOK      atomic.Int64
	dispatchOK       atomic.Int64
	dispatchRequired atomic.Bool
	requests         *prometheus.CounterVec
	duration         *prometheus.HistogramVec
	iterations       *prometheus.CounterVec
	processing       prometheus.Histogram
	completed        prometheus.Counter
	retried          prometheus.Counter
}

func New(role, revision string) *Metrics {
	registry := prometheus.NewRegistry()
	m := &Metrics{
		registry:   registry,
		role:       role,
		requests:   prometheus.NewCounterVec(prometheus.CounterOpts{Name: "workshop_http_requests_total", Help: "HTTP requests by bounded route, method and status."}, []string{"route", "method", "status"}),
		duration:   prometheus.NewHistogramVec(prometheus.HistogramOpts{Name: "workshop_http_request_duration_seconds", Help: "HTTP handler duration.", Buckets: prometheus.DefBuckets}, []string{"route"}),
		iterations: prometheus.NewCounterVec(prometheus.CounterOpts{Name: "workshop_worker_iterations_total", Help: "Worker polling iterations by completed, idle or error outcome."}, []string{"outcome"}),
		processing: prometheus.NewHistogram(prometheus.HistogramOpts{Name: "workshop_worker_completion_duration_seconds", Help: "Successful worker iteration duration including dispatch, claim, analysis and commit.", Buckets: prometheus.DefBuckets}),
		completed:  prometheus.NewCounter(prometheus.CounterOpts{Name: "workshop_jobs_completed_total", Help: "Jobs successfully committed by this worker process."}),
		retried:    prometheus.NewCounter(prometheus.CounterOpts{Name: "workshop_retried_jobs_completed_total", Help: "Completed jobs whose successful attempt token exceeds one."}),
	}
	info := prometheus.NewGaugeVec(prometheus.GaugeOpts{Name: "workshop_build_info", Help: "Process build identity."}, []string{"role", "revision"})
	info.WithLabelValues(role, revision).Set(1)
	registry.MustRegister(m.requests, m.duration, m.iterations, m.processing, m.completed, m.retried, info, collectors.NewGoCollector(), collectors.NewProcessCollector(collectors.ProcessCollectorOpts{}))
	return m
}

func (m *Metrics) Handler() http.Handler {
	return promhttp.HandlerFor(m.registry, promhttp.HandlerOpts{Timeout: 3 * time.Second})
}

func (m *Metrics) SetVariant(variant string) {
	info := prometheus.NewGaugeVec(prometheus.GaugeOpts{Name: "workshop_analysis_variant_info", Help: "Compiled analysis variant."}, []string{"variant"})
	info.WithLabelValues(variant).Set(1)
	m.registry.MustRegister(info)
}

type response struct {
	http.ResponseWriter
	status int
}

func (w *response) WriteHeader(status int) {
	if w.status != 0 {
		return
	}
	w.status = status
	w.ResponseWriter.WriteHeader(status)
}
func (w *response) Write(data []byte) (int, error) {
	if w.status == 0 {
		w.WriteHeader(http.StatusOK)
	}
	return w.ResponseWriter.Write(data)
}
func (w *response) Unwrap() http.ResponseWriter { return w.ResponseWriter }

func (m *Metrics) InstrumentHTTP(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		started := time.Now()
		wrapped := &response{ResponseWriter: w}
		next.ServeHTTP(wrapped, r)
		route := r.Pattern
		if route == "" {
			route = "unmatched"
		}
		method := r.Method
		switch method {
		case "GET", "HEAD", "POST":
		default:
			method = "OTHER"
		}
		status := wrapped.status
		if status == 0 {
			status = http.StatusOK
		}
		m.requests.WithLabelValues(route, method, strconv.Itoa(status)).Inc()
		m.duration.WithLabelValues(route).Observe(time.Since(started).Seconds())
	})
}

// ObserveIteration accepts no user-controlled label values.
func (m *Metrics) ObserveIteration(completed bool, attempt int, err error, elapsed time.Duration) {
	outcome := "idle"
	if err != nil {
		outcome = "error"
	} else if completed {
		outcome = "completed"
		m.completed.Inc()
		if attempt > 1 {
			m.retried.Inc()
		}
		m.processing.Observe(elapsed.Seconds())
	}
	if m.role == "worker" && err == nil {
		m.iterationOK.Store(time.Now().UnixNano())
	}
	m.iterations.WithLabelValues(outcome).Inc()
}

// ObservePoll records only a completed, successful queue/database poll.
func (m *Metrics) ObservePoll(err error) {
	if m.role == "worker" && err == nil {
		m.iterationOK.Store(time.Now().UnixNano())
	}
}

// RequireDispatchHealth includes the independent cloud outbox publisher in readiness.
func (m *Metrics) RequireDispatchHealth(required bool) {
	m.dispatchRequired.Store(required)
}

// ObserveDispatch advances cloud-worker readiness only after an outbox poll succeeds.
func (m *Metrics) ObserveDispatch(err error) {
	if m.role == "worker" && err == nil {
		m.dispatchOK.Store(time.Now().UnixNano())
	}
}

const workerReadinessWindow = 30 * time.Second

func (m *Metrics) workerReadyAt(now time.Time) bool {
	if m.role != "worker" || !fresh(m.iterationOK.Load(), now) {
		return false
	}
	return !m.dispatchRequired.Load() || fresh(m.dispatchOK.Load(), now)
}

func fresh(unixNano int64, now time.Time) bool {
	if unixNano == 0 {
		return false
	}
	age := now.Sub(time.Unix(0, unixNano))
	return age >= 0 && age <= workerReadinessWindow
}
