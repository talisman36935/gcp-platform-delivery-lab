package telemetry

import (
	"net/http/httptest"
	"testing"
	"time"
)

func TestProfilingRequiresExplicitEnableAndBoundedDuration(t *testing.T) {
	m := New("worker", "test")
	for _, tc := range []struct {
		enabled bool
		path    string
		want    int
	}{
		{false, "/debug/pprof/profile?seconds=1", 404},
		{false, "/debug/pprof/heap", 404},
		{true, "/debug/pprof/profile?seconds=600", 400},
		{true, "/debug/pprof/profile", 400},
	} {
		response := httptest.NewRecorder()
		m.AdminHandler(tc.enabled).ServeHTTP(response, httptest.NewRequest("GET", tc.path, nil))
		if response.Code != tc.want {
			t.Fatalf("got %d want %d", response.Code, tc.want)
		}
	}
}

func TestWorkerReadinessEndpointIsPrivateToWorkerAndFailClosed(t *testing.T) {
	worker := New("worker", "test")
	handler := worker.AdminHandler(false)
	request := httptest.NewRequest("GET", "/readyz", nil)
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)
	if response.Code != 503 || response.Header().Get("Cache-Control") != "no-store" {
		t.Fatalf("uninitialized worker readiness = %d, headers=%v", response.Code, response.Header())
	}
	worker.ObserveIteration(false, 0, nil, time.Millisecond)
	response = httptest.NewRecorder()
	handler.ServeHTTP(response, request)
	if response.Code != 200 || response.Body.String() != "ready\n" {
		t.Fatalf("healthy worker readiness = %d %q", response.Code, response.Body.String())
	}
	api := New("api", "test")
	response = httptest.NewRecorder()
	api.AdminHandler(false).ServeHTTP(response, request)
	if response.Code != 404 {
		t.Fatalf("API exposed worker readiness route: %d", response.Code)
	}
}
