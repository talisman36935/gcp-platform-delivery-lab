package httpapi

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"regexp"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/talisman36935/gcp-platform-delivery-lab/workload/internal/domain"
	"github.com/talisman36935/gcp-platform-delivery-lab/workload/internal/postgres"
)

type Repository interface {
	Submit(context.Context, string, domain.Request) (postgres.Job, error)
	Get(context.Context, string) (postgres.Job, error)
}

var keyPattern = regexp.MustCompile(`^[A-Za-z0-9_-]{1,128}$`)

func Handler(s Repository, ready func(context.Context) error) http.Handler {
	m := http.NewServeMux()
	m.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) { reply(w, 200, map[string]string{"status": "ok"}) })
	m.HandleFunc("GET /readyz", func(w http.ResponseWriter, r *http.Request) {
		ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
		defer cancel()
		if ready(ctx) != nil {
			reply(w, 503, map[string]string{"error": "database_unavailable"})
			return
		}
		reply(w, 200, map[string]string{"status": "ready"})
	})
	m.HandleFunc("POST /v1/jobs", func(w http.ResponseWriter, r *http.Request) {
		key := r.Header.Get("Idempotency-Key")
		if !keyPattern.MatchString(key) {
			reply(w, 400, map[string]string{"error": "invalid_idempotency_key"})
			return
		}
		r.Body = http.MaxBytesReader(w, r.Body, 4096)
		dec := json.NewDecoder(r.Body)
		dec.DisallowUnknownFields()
		var req domain.Request
		if err := dec.Decode(&req); err != nil {
			reply(w, 400, map[string]string{"error": "invalid_request"})
			return
		}
		var extra any
		if dec.Decode(&extra) != io.EOF || domain.Validate(req) != nil {
			reply(w, 400, map[string]string{"error": "invalid_request"})
			return
		}
		j, err := s.Submit(r.Context(), key, req)
		if errors.Is(err, postgres.ErrConflict) {
			reply(w, 409, map[string]string{"error": "idempotency_conflict"})
			return
		}
		if err != nil {
			reply(w, 503, map[string]string{"error": "storage_unavailable"})
			return
		}
		w.Header().Set("Location", "/v1/jobs/"+j.ID)
		reply(w, 202, j)
	})
	m.HandleFunc("GET /v1/jobs/{id}", func(w http.ResponseWriter, r *http.Request) {
		j, err := s.Get(r.Context(), r.PathValue("id"))
		if fail(w, err) {
			return
		}
		reply(w, 200, j)
	})
	m.HandleFunc("GET /v1/jobs/{id}/report", func(w http.ResponseWriter, r *http.Request) {
		j, err := s.Get(r.Context(), r.PathValue("id"))
		if fail(w, err) {
			return
		}
		if j.State != "succeeded" {
			reply(w, 409, map[string]string{"error": "report_not_ready"})
			return
		}
		reply(w, 200, j.Report)
	})
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Cache-Control", "no-store")
		w.Header().Set("X-Content-Type-Options", "nosniff")
		ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
		defer cancel()
		m.ServeHTTP(w, r.WithContext(ctx))
	})
}

func fail(w http.ResponseWriter, err error) bool {
	if err == nil {
		return false
	}
	status, code := 503, "storage_unavailable"
	if errors.Is(err, pgx.ErrNoRows) {
		status, code = 404, "job_not_found"
	}
	reply(w, status, map[string]string{"error": code})
	return true
}
func reply(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}
