package telemetry

import (
	"context"
	"net"
	"net/http"
	"net/http/pprof"
	"strconv"
	"time"
)

// Start binds synchronously so address failures prevent an unobservable startup.
// An empty address disables telemetry. Callers keep this listener private.
func (m *Metrics) Start(ctx context.Context, addr string, profiling ...bool) (func(), error) {
	if addr == "" {
		return func() {}, nil
	}
	listener, err := net.Listen("tcp", addr)
	if err != nil {
		return nil, err
	}
	enabled := len(profiling) > 0 && profiling[0]
	server := &http.Server{Handler: m.AdminHandler(enabled), ReadHeaderTimeout: 3 * time.Second, WriteTimeout: 10 * time.Second, IdleTimeout: 30 * time.Second}
	done := make(chan struct{})
	go func() { defer close(done); _ = server.Serve(listener) }()
	go func() {
		select {
		case <-ctx.Done():
			shutdown, cancel := context.WithTimeout(context.Background(), 3*time.Second)
			defer cancel()
			_ = server.Shutdown(shutdown)
		case <-done:
		}
	}()
	return func() { _ = server.Close() }, nil
}

func (m *Metrics) AdminHandler(profiling bool) http.Handler {
	mux := http.NewServeMux()
	mux.Handle("GET /metrics", m.Handler())
	if m.role == "worker" {
		mux.HandleFunc("GET /readyz", func(w http.ResponseWriter, _ *http.Request) {
			w.Header().Set("Cache-Control", "no-store")
			if !m.workerReadyAt(time.Now()) {
				http.Error(w, "worker_not_ready", http.StatusServiceUnavailable)
				return
			}
			w.WriteHeader(http.StatusOK)
			_, _ = w.Write([]byte("ready\n"))
		})
	}
	if profiling {
		mux.Handle("GET /debug/pprof/heap", pprof.Handler("heap"))
		mux.HandleFunc("GET /debug/pprof/profile", func(w http.ResponseWriter, r *http.Request) {
			seconds, err := strconv.Atoi(r.URL.Query().Get("seconds"))
			if err != nil || seconds < 1 || seconds > 5 {
				http.Error(w, "seconds must be between 1 and 5", 400)
				return
			}
			pprof.Profile(w, r)
		})
	}
	return mux
}
