package analysis

import "testing"

func TestStemmedVersionKeepsOffsetsAndV1(t *testing.T) {
	input := "Studies studying study 42 café"
	baseline, err := Analyze(input)
	if err != nil {
		t.Fatal(err)
	}
	stemmed, err := AnalyzeVersion(input, StemmedVersion)
	if err != nil {
		t.Fatal(err)
	}
	if len(stemmed) != len(baseline) {
		t.Fatal("token count changed")
	}
	for i := range baseline {
		if stemmed[i].Start != baseline[i].Start || stemmed[i].End != baseline[i].End || stemmed[i].Position != baseline[i].Position {
			t.Fatalf("offset changed at %d", i)
		}
	}
	if stemmed[0].Term != "studi" || stemmed[1].Term != "studi" || stemmed[2].Term != "studi" {
		t.Fatalf("unexpected stems: %+v", stemmed)
	}
	if stemmed[3].Term != "42" || stemmed[4].Term != "café" {
		t.Fatalf("non-English term changed: %+v", stemmed)
	}
	if baseline[0].Term != "studies" {
		t.Fatal("v1 changed")
	}
}
