// Package domain implements deterministic report computation without infrastructure dependencies.
package domain

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"strings"
	"unicode"
)

var ErrFixture = errors.New("unknown fixture")

type Request struct {
	TraceParent string `json:"-"`
	Fixture     string `json:"fixture"`
	Algorithm   string `json:"algorithm"`
}

type Report struct {
	Documents          int    `json:"documents"`
	Tokens             int    `json:"tokens"`
	UniqueTokens       int    `json:"unique_tokens"`
	DuplicateDocuments int    `json:"duplicate_documents"`
	InputSHA256        string `json:"input_sha256"`
}

func Documents(name string) ([]string, error) {
	switch name {
	case "tiny-v1":
		return []string{"Platforms teams can own", "Observable platforms recover", "Platforms teams can own"}, nil
	case "batch-v1":
		return []string{strings.Repeat("observable reliable platforms ", 10000), strings.Repeat("retries preserve work ", 10000)}, nil
	default:
		return nil, ErrFixture
	}
}

func Validate(r Request) error {
	if r.Algorithm != "tokens-v1" {
		return errors.New("unsupported algorithm")
	}
	_, err := Documents(r.Fixture)
	return err
}

func Hash(data []byte) string {
	h := sha256.Sum256(data)
	return hex.EncodeToString(h[:])
}

func Analyze(name string) (Report, error) {
	docs, err := Documents(name)
	if err != nil {
		return Report{}, err
	}
	encoded, err := json.Marshal(docs)
	if err != nil {
		return Report{}, err
	}
	r := Report{Documents: len(docs), InputSHA256: Hash(encoded)}
	words, seen := map[string]bool{}, map[string]bool{}
	for _, doc := range docs {
		if seen[doc] {
			r.DuplicateDocuments++
		}
		seen[doc] = true
		for _, word := range strings.FieldsFunc(strings.ToLower(doc), func(r rune) bool { return !unicode.IsLetter(r) && !unicode.IsNumber(r) }) {
			r.Tokens++
			words[word] = true
		}
	}
	r.UniqueTokens = len(words)
	return r, nil
}
