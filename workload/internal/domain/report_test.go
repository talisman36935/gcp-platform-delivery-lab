package domain

import "testing"

func TestGoldenReport(t *testing.T) {
	r, err := Analyze("tiny-v1")
	if err != nil {
		t.Fatal(err)
	}
	if r.Documents != 3 || r.Tokens != 11 || r.UniqueTokens != 6 || r.DuplicateDocuments != 1 {
		t.Fatalf("unexpected report: %+v", r)
	}
	again, _ := Analyze("tiny-v1")
	if again != r {
		t.Fatal("non-deterministic result")
	}
	if _, err := Analyze("../../etc/passwd"); err == nil {
		t.Fatal("unknown fixture accepted")
	}
}
