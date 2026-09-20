package scoring

import (
	"math"
	"retrievec/engine/internal/corpus"
	"retrievec/engine/internal/index"
	"testing"
)

func TestIndependentScoresAndParameters(t *testing.T) {
	idx, err := index.Build([]corpus.Document{{Chunk: corpus.Chunk{ChunkID: "b", PaperID: "p", PaperVersionID: "v", CollectionID: "c", Text: "red red"}}, {Chunk: corpus.Chunk{ChunkID: "a", PaperID: "p", PaperVersionID: "v", CollectionID: "c", Text: "red blue"}}})
	if err != nil {
		t.Fatal(err)
	}
	scores, err := Rank(idx, []string{"red", "red"}, map[int]bool{0: true, 1: true}, Default())
	if err != nil {
		t.Fatal(err)
	}
	if scores[0].ID != 1 || math.Abs(scores[0].Value-0.2506921405916876) > 1e-12 || math.Abs(scores[1].Value-0.1823215567939546) > 1e-12 {
		t.Fatalf("scores: %+v", scores)
	}
	ties, _ := Rank(idx, nil, map[int]bool{0: true, 1: true}, Default())
	if ties[0].ID != 0 {
		t.Fatal("unstable ties")
	}
	for _, c := range []Config{{0, .5}, {1, -1}, {1, 2}, {math.Inf(1), 0}, {1, math.NaN()}} {
		if _, err := Rank(idx, nil, nil, c); err == nil {
			t.Fatal("accepted invalid parameters")
		}
	}
}
