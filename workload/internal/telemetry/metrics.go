// Package telemetry contains adapters only; domain/application code stays neutral.
package telemetry

import (
	"net/http"
	"strconv"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/collectors"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

type Metrics struct {
	registry   *prometheus.Registry
	requests   *prometheus.CounterVec
	duration   *prometheus.HistogramVec
	iterations *prometheus.CounterVec
	processing prometheus.Histogram
	completed  prometheus.Counter
	retried    prometheus.Counter
}

func New(role, revision string) *Metrics {
	registry := prometheus.NewRegistry()
	m := &Metrics{
		registry:   registry,
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
	m.iterations.WithLabelValues(outcome).Inc()
}
