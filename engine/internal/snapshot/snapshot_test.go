package snapshot

import (
	"context"
	"reflect"
	"retrievec/engine/internal/corpus"
	"retrievec/engine/internal/index"
	"retrievec/engine/internal/scoring"
	"retrievec/engine/internal/search"
	"testing"
)

func TestMultiSegmentSearchParity(t *testing.T) {
	path := "../../../datasets/fixtures/snapshots/ss_4415a7c573a87a239ee65b0581664ea667b3988e4be43cb7f3bd069380ee0811"
	root := t.TempDir()
	id, err := Build(root, path, 3, nil)
	if err != nil {
		t.Fatal(err)
	}
	disk, err := Open(root, id)
	if err != nil {
		t.Fatal(err)
	}
	defer disk.Close()
	source, _ := corpus.Load(path)
	memory, _ := index.Build(source.Documents)
	for _, request := range []search.Request{{Query: "retrieval", Mode: "free_text", TopK: 100, Explain: true}, {Query: `"red red" OR NOT retrieval`, Mode: "structured", TopK: 100, Explain: true}} {
		a, err := search.Execute(context.Background(), memory, request, scoring.Default())
		if err != nil {
			t.Fatal(err)
		}
		b, err := search.Execute(context.Background(), disk, request, scoring.Default())
		if err != nil || !reflect.DeepEqual(a, b) {
			t.Fatalf("parity mismatch: %v", err)
		}
	}
}
