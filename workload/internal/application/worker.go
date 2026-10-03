// Package application defines use cases and their infrastructure-independent ports.
package application

import (
	"context"
	"errors"
	"time"

	"github.com/talisman36935/gcp-platform-delivery-lab/workload/internal/domain"
)

type JobReaderWriter interface {
	Submit(context.Context, string, domain.Request) (domain.Job, error)
	Get(context.Context, string) (domain.Job, error)
}

type WorkQueue interface {
	Dispatch(context.Context) error
	Claim(context.Context, string, time.Duration) (domain.Job, error)
	Complete(context.Context, domain.Job, domain.Report) error
}

// ProcessOne returns nil when no eligible work exists. Cloud adapters must retain
// the same fencing contract while qualifying their own delivery semantics.
func ProcessOne(ctx context.Context, queue WorkQueue, revision string) (*domain.Job, error) {
	if err := queue.Dispatch(ctx); err != nil {
		return nil, err
	}
	job, err := queue.Claim(ctx, revision, 30*time.Second)
	if errors.Is(err, domain.ErrNotFound) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	report, err := domain.Analyze(job.Fixture)
	if err != nil {
		return nil, err
	}
	if err = queue.Complete(ctx, job, report); err != nil {
		return nil, err
	}
	return &job, nil
}
