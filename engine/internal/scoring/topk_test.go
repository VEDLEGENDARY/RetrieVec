package scoring

import (
	"context"
	"retrievec/engine/internal/corpus"
	"retrievec/engine/internal/index"
	"testing"
)

func TestRankTopKMatchesReferencePrefix(t *testing.T) {
	documents := []corpus.Document{
		{Chunk: corpus.Chunk{ChunkID: "a", PaperID: "p", PaperVersionID: "v", CollectionID: "c", Text: "dense retrieval dense"}},
		{Chunk: corpus.Chunk{ChunkID: "b", PaperID: "p", PaperVersionID: "v", CollectionID: "c", Text: "dense retrieval"}},
		{Chunk: corpus.Chunk{ChunkID: "c", PaperID: "p", PaperVersionID: "v", CollectionID: "c", Text: "sparse retrieval"}},
	}
	idx, err := index.Build(documents)
	if err != nil {
		t.Fatal(err)
	}
	candidates := map[int]bool{0: true, 1: true, 2: true}
	reference, err := RankContext(context.Background(), idx, []string{"dense", "retrieval"}, candidates, Default())
	if err != nil {
		t.Fatal(err)
	}
	optimized, err := RankTopK(context.Background(), idx, []string{"dense", "retrieval"}, candidates, Default(), 2)
	if err != nil {
		t.Fatal(err)
	}
	for at := range optimized {
		if optimized[at].ID != reference[at].ID || optimized[at].Value != reference[at].Value {
			t.Fatalf("top-k differs at %d: %+v != %+v", at, optimized[at], reference[at])
		}
	}
}
