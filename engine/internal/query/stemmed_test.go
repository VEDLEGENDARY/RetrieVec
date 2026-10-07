package query

import (
	"retrievec/engine/internal/analysis"
	"testing"
)

func TestStructuredQueryUsesSelectedAnalyzer(t *testing.T) {
	v1, err := Parse(`"studies"`)
	if err != nil {
		t.Fatal(err)
	}
	v2, err := ParseVersion(`"studies"`, analysis.StemmedVersion)
	if err != nil {
		t.Fatal(err)
	}
	if v1.Terms[0] != "studies" || v2.Terms[0] != "studi" {
		t.Fatalf("unexpected terms: %v %v", v1.Terms, v2.Terms)
	}
}
