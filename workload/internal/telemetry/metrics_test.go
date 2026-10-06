package telemetry

import (
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func TestBoundedRoutes(t *testing.T) {
	m := New("api", "test")
	mux := http.NewServeMux()
	mux.HandleFunc("GET /v1/jobs/{id}", func(w http.ResponseWriter, r *http.Request) { w.WriteHeader(404) })
	h := m.InstrumentHTTP(mux)
	for _, path := range []string{"/v1/jobs/private-job-one", "/v1/jobs/private-job-two", "/private-unknown"} {
		h.ServeHTTP(httptest.NewRecorder(), httptest.NewRequest("GET", path, nil))
	}
	out := httptest.NewRecorder()
	m.Handler().ServeHTTP(out, httptest.NewRequest("GET", "/metrics", nil))
	body := out.Body.String()
	if strings.Contains(body, "private-") {
		t.Fatal("raw identifiers leaked into metrics")
	}
	if !strings.Contains(body, `route="GET /v1/jobs/{id}",status="404"} 2`) {
		t.Fatal(body)
	}
}

func TestWorkerOutcomes(t *testing.T) {
	m := New("worker", "test")
	m.ObserveIteration(false, 0, nil, time.Second)
	m.ObserveIteration(false, 0, errors.New("private error"), time.Second)
	m.ObserveIteration(true, 2, nil, time.Second)
	out := httptest.NewRecorder()
	m.Handler().ServeHTTP(out, httptest.NewRequest("GET", "/metrics", nil))
	for _, want := range []string{
		"workshop_jobs_completed_total 1",
		"workshop_retried_jobs_completed_total 1",
		`workshop_worker_iterations_total{outcome="idle"} 1`,
		`workshop_worker_iterations_total{outcome="error"} 1`,
	} {
		if !strings.Contains(out.Body.String(), want) {
			t.Fatalf("missing %s", want)
		}
	}
}

func TestWorkerReadinessRequiresFreshHealthyCycles(t *testing.T) {
	now := time.Now()
	worker := New("worker", "test")
	worker.RequireDispatchHealth(true)
	if worker.workerReadyAt(now) {
		t.Fatal("worker became ready before completing work or dispatch cycles")
	}
	worker.iterationOK.Store(now.UnixNano())
	if worker.workerReadyAt(now) {
		t.Fatal("cloud worker became ready before outbox dispatch succeeded")
	}
	worker.ObserveDispatch(errors.New("private dispatch failure"))
	if worker.workerReadyAt(now) {
		t.Fatal("failed dispatch marked worker ready")
	}
	worker.ObserveDispatch(nil)
	healthyAt := time.Now()
	if !worker.workerReadyAt(healthyAt) {
		t.Fatal("fresh successful work and dispatch cycles did not mark ready")
	}
	worker.ObserveIteration(false, 0, errors.New("private poll failure"), time.Second)
	if !worker.workerReadyAt(healthyAt.Add(workerReadinessWindow - time.Second)) {
		t.Fatal("one failed poll erased a still-fresh success")
	}
	if worker.workerReadyAt(healthyAt.Add(workerReadinessWindow + time.Second)) {
		t.Fatal("stale successful cycles remained ready")
	}
	api := New("api", "test")
	api.ObserveIteration(false, 0, nil, time.Second)
	if api.workerReadyAt(now) {
		t.Fatal("API process used the worker readiness contract")
	}
}

func TestLocalWorkerReadinessDoesNotRequireCloudDispatcher(t *testing.T) {
	worker := New("worker", "test")
	worker.ObservePoll(nil)
	if !worker.workerReadyAt(time.Now()) {
		t.Fatal("successful local idle poll should be ready")
	}
}

func TestCloudWorkerReadinessExpiresStalledDispatcher(t *testing.T) {
	now := time.Now()
	worker := New("worker", "test")
	worker.RequireDispatchHealth(true)
	worker.iterationOK.Store(now.UnixNano())
	worker.dispatchOK.Store(now.Add(-workerReadinessWindow - time.Second).UnixNano())
	if worker.workerReadyAt(now) {
		t.Fatal("fresh consumer polls hid a stalled cloud outbox dispatcher")
	}
}
