package telemetry

import (
	"net/http/httptest"
	"testing"
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
