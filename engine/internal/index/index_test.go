package index

import (
	"sync"
	"testing"

	"retrievallab/engine/internal/analysis"
	"retrievallab/engine/internal/corpus"
)

func document(id, text string) corpus.Document {
	return corpus.Document{Chunk: corpus.Chunk{
		ChunkID:        id,
		PaperID:        "paper-" + id,
		PaperVersionID: "version-" + id,
		CollectionID:   "research",
		Text:           text,
		PageRange:      []int{1, 1},
	}, Title: "Title " + id}
}

func TestBuildCreatesDeterministicPositionalPostings(t *testing.T) {
	index, err := Build([]corpus.Document{
		document("chunk-b", "Dense retrieval dense"),
		document("chunk-a", "Retrieval works"),
	})
	if err != nil {
		t.Fatal(err)
	}

	if got := index.Terms(); len(got) != 3 || got[0] != "dense" || got[1] != "retrieval" || got[2] != "works" {
		t.Fatalf("unexpected terms: %v", got)
	}
	postings := index.Postings("dense")
	if len(postings) != 1 || postings[0].InternalChunkID != 1 || postings[0].TermFrequency != 2 {
		t.Fatalf("unexpected dense posting: %+v", postings)
	}
	if want := []int{0, 2}; !equalInts(postings[0].Positions, want) {
		t.Fatalf("dense positions = %v, want %v", postings[0].Positions, want)
	}
	if got, ok := index.Lookup("chunk-a"); !ok || got != 0 {
		t.Fatalf("chunk-a lookup = %d, %t; want 0, true", got, ok)
	}
	if got := index.Stats(); got.ChunkCount != 2 || got.TotalTokens != 5 || got.TermCount != 3 || got.AverageChunkLength != 2.5 || got.AnalyzerVersion != analysis.Version {
		t.Fatalf("unexpected statistics: %+v", got)
	}
}

func TestBuildRejectsInvalidCollections(t *testing.T) {
	cases := []struct {
		name      string
		documents []corpus.Document
	}{
		{"empty corpus", nil},
		{"missing collection", []corpus.Document{{Chunk: corpus.Chunk{ChunkID: "chunk-a", PaperID: "paper", PaperVersionID: "version", Text: "text"}}}},
		{"zero-token chunk", []corpus.Document{{Chunk: corpus.Chunk{ChunkID: "chunk-a", PaperID: "paper", PaperVersionID: "version", CollectionID: "research", Text: "---"}}}},
		{"duplicate ID", []corpus.Document{document("chunk-a", "one"), document("chunk-a", "two")}},
		{"mixed collection", []corpus.Document{document("chunk-a", "one"), func() corpus.Document {
			value := document("chunk-b", "two")
			value.CollectionID = "other"
			return value
		}()}},
	}
	for _, test := range cases {
		t.Run(test.name, func(t *testing.T) {
			if _, err := Build(test.documents); err == nil {
				t.Fatal("Build succeeded for invalid documents")
			}
		})
	}
}

func TestAccessorsReturnDefensiveCopiesAndSupportConcurrentReads(t *testing.T) {
	index, err := Build([]corpus.Document{document("chunk-a", "one two")})
	if err != nil {
		t.Fatal(err)
	}

	postings := index.Postings("one")
	postings[0].Positions[0] = 99
	documentCopy, ok := index.Document(0)
	if !ok {
		t.Fatal("Document rejected valid internal ID")
	}
	documentCopy.PageRange[0] = 99
	if got := index.Postings("one")[0].Positions[0]; got != 0 {
		t.Fatalf("posting mutation leaked into index: %d", got)
	}
	if got, _ := index.Document(0); got.PageRange[0] != 1 {
		t.Fatalf("document mutation leaked into index: %v", got.PageRange)
	}

	var group sync.WaitGroup
	for range 32 {
		group.Add(1)
		go func() {
			defer group.Done()
			for range 100 {
				_ = index.Stats()
				_ = index.Terms()
				_ = index.Postings("one")
				_, _ = index.Document(0)
				_, _ = index.ChunkLength(0)
			}
		}()
	}
	group.Wait()
}

func equalInts(left, right []int) bool {
	if len(left) != len(right) {
		return false
	}
	for position := range left {
		if left[position] != right[position] {
			return false
		}
	}
	return true
}
