package main

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/talisman36935/gcp-platform-delivery-lab/workload/internal/application"
	"github.com/talisman36935/gcp-platform-delivery-lab/workload/internal/httpapi"
	"github.com/talisman36935/gcp-platform-delivery-lab/workload/internal/postgres"
	"github.com/talisman36935/gcp-platform-delivery-lab/workload/internal/telemetry"
)

var revision = "development"

func main() {
	slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stdout, nil)))
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()
	if err := run(ctx); err != nil {
		slog.Error("process failed", "category", "runtime")
		os.Exit(1)
	}
}

func run(ctx context.Context) error {
	if len(os.Args) != 2 {
		return errors.New("expected migrate, api or worker")
	}
	mode := os.Args[1]
	if mode != "migrate" && mode != "api" && mode != "worker" {
		return errors.New("invalid mode")
	}
	url := os.Getenv("DATABASE_URL")
	if url == "" {
		return errors.New("DATABASE_URL is required")
	}
	connect, cancel := context.WithTimeout(ctx, 10*time.Second)
	s, err := postgres.Open(connect, url)
	cancel()
	if err != nil {
		return err
	}
	defer s.Pool.Close()
	if mode == "migrate" {
		return s.Migrate(ctx)
	}
	metrics := telemetry.New(mode, revision)
	stopMetrics, err := metrics.Start(ctx, os.Getenv("METRICS_ADDR"))
	if err != nil {
		return err
	}
	defer stopMetrics()
	if mode == "worker" {
		ticker := time.NewTicker(200 * time.Millisecond)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				return nil
			case <-ticker.C:
				iteration, cancel := context.WithTimeout(ctx, 10*time.Second)
				err := process(iteration, s, metrics)
				cancel()
				if err != nil {
					slog.Warn("processing iteration failed", "category", "processing")
				}
			}
		}
	}
	addr := os.Getenv("LISTEN_ADDR")
	if addr == "" {
		addr = "127.0.0.1:8080"
	}
	srv := &http.Server{Addr: addr, Handler: httpapi.Handler(s, s.Pool.Ping, metrics.InstrumentHTTP), ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 10 * time.Second, WriteTimeout: 10 * time.Second, IdleTimeout: 30 * time.Second}
	finished := make(chan struct{})
	defer close(finished)
	go func() {
		select {
		case <-ctx.Done():
			shutdown, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()
			_ = srv.Shutdown(shutdown)
		case <-finished:
		}
	}()
	slog.Info("API listening", "address", addr, "revision", revision)
	err = srv.ListenAndServe()
	if errors.Is(err, http.ErrServerClosed) {
		return nil
	}
	return err
}

func process(ctx context.Context, s *postgres.Store, metrics *telemetry.Metrics) error {
	started := time.Now()
	j, err := application.ProcessOne(ctx, s, revision)
	attempt := 0
	if j != nil {
		attempt = j.Attempt
	}
	metrics.ObserveIteration(j != nil, attempt, err, time.Since(started))
	if err != nil {
		return err
	}
	if j != nil {
		slog.Info("job completed", "job_id", j.ID, "attempt", j.Attempt, "revision", revision, "processing_ms", time.Since(started).Milliseconds())
	}
	return nil
}
