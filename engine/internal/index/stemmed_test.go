package index

import (
	"retrievec/engine/internal/analysis"
	"retrievec/engine/internal/corpus"
	"testing"
)

func TestBuildVersionKeepsV1Reference(t *testing.T) {
	docs := []corpus.Document{{Chunk: corpus.Chunk{ChunkID: "a", PaperID: "p", PaperVersionID: "v", CollectionID: "c", Text: "studies"}}}
	v1, err := Build(docs)
	if err != nil {
		t.Fatal(err)
	}
	v2, err := BuildVersion(docs, analysis.StemmedVersion)
	if err != nil {
		t.Fatal(err)
	}
	if v1.DocumentFrequency("studies") != 1 || v1.DocumentFrequency("studi") != 0 {
		t.Fatal("v1 terms changed")
	}
	if v2.DocumentFrequency("studi") != 1 || v2.DocumentFrequency("studies") != 0 {
		t.Fatal("v2 stem missing")
	}
	if v2.Stats().AnalyzerVersion != analysis.StemmedVersion {
		t.Fatal("v2 version missing")
	}
}
