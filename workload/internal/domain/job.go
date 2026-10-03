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
	ID          string          `json:"id"`
	Fixture     string          `json:"fixture"`
	Algorithm   string          `json:"algorithm"`
	State       string          `json:"state"`
	Attempt     int             `json:"attempt"`
	CreatedAt   time.Time       `json:"created_at"`
	CompletedAt *time.Time      `json:"completed_at"`
	Report      json.RawMessage `json:"-"`
}
