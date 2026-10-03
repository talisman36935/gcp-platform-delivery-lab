package application

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/talisman36935/gcp-platform-delivery-lab/workload/internal/domain"
)

type queueStub struct {
	dispatchErr, claimErr, completeErr error
	completed                          bool
}

func (q *queueStub) Dispatch(context.Context) error { return q.dispatchErr }
func (q *queueStub) Claim(context.Context, string, time.Duration) (domain.Job, error) {
	return domain.Job{ID: "test", Fixture: "tiny-v1"}, q.claimErr
}
func (q *queueStub) Complete(_ context.Context, _ domain.Job, report domain.Report) error {
	q.completed = true
	if report.Tokens != 11 {
		return errors.New("incorrect report")
	}
	return q.completeErr
}

func TestProcessOne(t *testing.T) {
	for _, tc := range []struct {
		name                             string
		q                                queueStub
		wantJob, wantError, wantComplete bool
	}{
		{"success", queueStub{}, true, false, true},
		{"idle", queueStub{claimErr: domain.ErrNotFound}, false, false, false},
		{"dispatch fails", queueStub{dispatchErr: errors.New("dispatch")}, false, true, false},
		{"claim fails", queueStub{claimErr: errors.New("claim")}, false, true, false},
		{"stale", queueStub{completeErr: domain.ErrStale}, false, true, true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			job, err := ProcessOne(context.Background(), &tc.q, "test")
			if (job != nil) != tc.wantJob || (err != nil) != tc.wantError || tc.q.completed != tc.wantComplete {
				t.Fatalf("job=%v err=%v completed=%v", job, err, tc.q.completed)
			}
		})
	}
}
