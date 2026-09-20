package search

import (
	"context"
	"reflect"
	"retrievec/engine/internal/corpus"
	"retrievec/engine/internal/index"
	"retrievec/engine/internal/scoring"
	"sort"
	"strings"
	"testing"
)

func TestStructuredAgainstReferencePredicates(t *testing.T) {
	texts := []string{"red red blue", "red blue red", "green blue", "green", "blue red red"}
	docs := []corpus.Document{}
	for i, text := range texts {
		docs = append(docs, corpus.Document{Chunk: corpus.Chunk{ChunkID: string(rune('a' + i)), PaperID: "p", PaperVersionID: "v", CollectionID: "c", Text: text}})
	}
	idx, err := index.Build(docs)
	if err != nil {
		t.Fatal(err)
	}
	cases := []struct {
		q     string
		match func(string) bool
	}{
		{`"red red"`, func(s string) bool { return strings.Contains(s, "red red") }},
		{`red AND NOT green`, func(s string) bool { return strings.Contains(s, "red") && !strings.Contains(s, "green") }},
		{`red OR NOT blue`, func(s string) bool { return strings.Contains(s, "red") || !strings.Contains(s, "blue") }},
		{`NOT (NOT red OR green)`, func(s string) bool { return !(!strings.Contains(s, "red") || strings.Contains(s, "green")) }},
		{`NOT NOT blue`, func(s string) bool { return strings.Contains(s, "blue") }},
	}
	for _, c := range cases {
		t.Run(c.q, func(t *testing.T) {
			r, err := Execute(context.Background(), idx, Request{c.q, "structured", 100, true}, scoring.Default())
			if err != nil {
				t.Fatal(err)
			}
			want, got := []string{}, []string{}
			for i, s := range texts {
				if c.match(s) {
					want = append(want, docs[i].ChunkID)
				}
			}
			for _, hit := range r.Hits {
				got = append(got, hit.ChunkID)
				sum := 0.0
				for _, v := range hit.Contributions {
					sum += v.Score
				}
				if sum != hit.Score {
					t.Fatal("explanation mismatch")
				}
			}
			sort.Strings(got)
			if !reflect.DeepEqual(got, want) {
				t.Fatalf("got %v want %v", got, want)
			}
		})
	}
	r, _ := Execute(context.Background(), idx, Request{"red OR NOT blue", "structured", 100, false}, scoring.Default())
	if r.Hits[len(r.Hits)-1].ChunkID != "d" || r.Hits[len(r.Hits)-1].Score != 0 {
		t.Fatal("zero score match missing")
	}
	a, _ := Execute(context.Background(), idx, Request{"red blue", "free_text", 100, false}, scoring.Default())
	b, _ := Execute(context.Background(), idx, Request{"red red blue", "free_text", 100, false}, scoring.Default())
	if !reflect.DeepEqual(a, b) {
		t.Fatal("repeated terms change ranking")
	}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if _, err := Execute(ctx, idx, Request{"red", "structured", 10, false}, scoring.Default()); err == nil {
		t.Fatal("cancellation ignored")
	}
}
