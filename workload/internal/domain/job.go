package domain

import (
	"encoding/json"
	"errors"
	"time"
)

var (
	ErrConflict = errors.New("idempotency key reused with a different request")
	ErrStale    = errors.New("processing lease expired or was superseded")
	ErrNotFound = errors.New("job not found")
)

type Job struct {
	TraceParent string          `json:"-"`
	ID          string          `json:"id"`
	Fixture     string          `json:"fixture"`
	Algorithm   string          `json:"algorithm"`
	State       string          `json:"state"`
	Attempt     int             `json:"attempt"`
	CreatedAt   time.Time       `json:"created_at"`
	CompletedAt *time.Time      `json:"completed_at"`
	Report      json.RawMessage `json:"-"`
	Object      *ReportObject   `json:"-"`
}

// ReportObject is the selected immutable result, never a credential or signed URL.
type ReportObject struct {
	Provider string `json:"provider"`
	Bucket   string `json:"bucket"`
	Key      string `json:"key"`
	SHA256   string `json:"sha256"`
}
