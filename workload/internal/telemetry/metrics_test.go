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
