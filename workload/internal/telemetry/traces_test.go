package telemetry

import (
	"context"
	"net/http/httptest"
	"strings"
	"testing"

	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	"go.opentelemetry.io/otel/sdk/trace/tracetest"

	"github.com/talisman36935/gcp-platform-delivery-lab/workload/internal/domain"
	"github.com/talisman36935/gcp-platform-delivery-lab/workload/internal/httpapi"
)

type traceStore struct{ job domain.Job }

func (s *traceStore) Submit(_ context.Context, _ string, r domain.Request) (domain.Job, error) {
	s.job = domain.Job{ID: "synthetic", Fixture: r.Fixture, TraceParent: r.TraceParent}
	return s.job, nil
}
func (s *traceStore) Get(context.Context, string) (domain.Job, error) { return s.job, nil }

func TestDurableParentAndRetryCorrelation(t *testing.T) {
	exporter := tracetest.NewInMemoryExporter()
	provider := sdktrace.NewTracerProvider(sdktrace.WithSyncer(exporter))
	defer provider.Shutdown(context.Background())
	traces := &Traces{tracer: provider.Tracer("test")}
	store := &traceStore{}
	handler := httpapi.Handler(traces.Repository(store), func(context.Context) error { return nil }, traces.InstrumentHTTP)
	request := httptest.NewRequest("POST", "/v1/jobs", strings.NewReader(`{"fixture":"tiny-v1","algorithm":"tokens-v1"}`))
	request.Header.Set("Idempotency-Key", "trace-test")
	request.Header.Set("Authorization", "SECRET-not-exported")
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)
	if response.Code != 202 {
		t.Fatal(response.Body.String())
	}
	expectedTraceID := response.Header().Get("Trace-Id")
	if expectedTraceID == "" || JobTraceID(store.job.TraceParent) != expectedTraceID {
		t.Fatal("submission parent missing")
	}
	for attempt := 1; attempt <= 2; attempt++ {
		store.job.Attempt = attempt
		ctx, end := traces.StartAttempt(context.Background(), store.job)
		_, finish := traces.StartOperation(ctx, "analyze documents")
		finish(nil)
		end(nil)
	}
	spans := exporter.GetSpans()
	var persistedID string
	for _, span := range spans {
		if span.Name == "persist job and outbox" {
			persistedID = span.SpanContext.SpanID().String()
		}
		for _, attr := range span.Attributes {
			if strings.Contains(attr.Value.AsString(), "SECRET") {
				t.Fatal("private header exported")
			}
		}
	}
	attempts := 0
	for _, span := range spans {
		if span.Name == "process job" {
			attempts++
			if span.SpanContext.TraceID().String() != expectedTraceID || span.Parent.SpanID().String() != persistedID {
				t.Fatal("retry did not continue the original durable parent")
			}
		}
	}
	if attempts != 2 {
		t.Fatalf("got %d attempts", attempts)
	}
}
