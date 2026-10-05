package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"retrievec/engine/internal/analysis"
	"strings"
	"testing"
)

func TestDocumentBenchmarkControls(t *testing.T) {
	path := filepath.Join(t.TempDir(), "corpus.jsonl")
	data := "{\"_id\":\"a\",\"title\":\"Running\",\"text\":\"the runners run\"}\n{\"_id\":\"b\",\"title\":\"Walking\",\"text\":\"the walkers walk\"}\n"
	if err := os.WriteFile(path, []byte(data), 0600); err != nil {
		t.Fatal(err)
	}
	for _, test := range []struct {
		mode, query string
		hits        int
	}{
		{"unicode", "running", 1}, {"unicode", "runs", 0}, {"snowball_english", "runs", 1},
		{"unicode", "the", 2}, {"english_stopwords", "the", 0}, {"english_stopwords_snowball", "the running", 1},
	} {
		t.Run(test.mode+test.query, func(t *testing.T) {
			var out, stderr bytes.Buffer
			input, _ := json.Marshal(map[string]any{"query": test.query, "top_k": 100, "k1": 1.2, "b": .75})
			if code := benchmarkCommand([]string{"--documents", path, "--analyzer", test.mode}, bytes.NewReader(input), &out, &stderr); code != 0 {
				t.Fatalf("code=%d %s", code, &stderr)
			}
			decoder := json.NewDecoder(&out)
			var startup struct {
				Count    int    `json:"document_count"`
				Identity string `json:"snapshot_id"`
			}
			if err := decoder.Decode(&startup); err != nil {
				t.Fatal(err)
			}
			if startup.Count != 2 || !strings.HasPrefix(startup.Identity, "beir-records-sha256-") {
				t.Fatalf("wrong document unit: %+v", startup)
			}
			var response struct {
				Hits []map[string]any `json:"hits"`
			}
			if err := decoder.Decode(&response); err != nil {
				t.Fatal(err)
			}
			if len(response.Hits) != test.hits {
				t.Fatalf("hits=%v want %d", response.Hits, test.hits)
			}
			for _, hit := range response.Hits {
				if hit["chunk_id"] != hit["paper_id"] {
					t.Fatal("document identity collapsed")
				}
			}
		})
	}
	tokens, _ := analysis.Analyze("running the")
	if tokens[0].Term != "running" || tokens[1].Term != "the" {
		t.Fatal("product analyzer changed")
	}
}

func TestDocumentControlRejectsAmbiguousModeAndDuplicates(t *testing.T) {
	path := filepath.Join(t.TempDir(), "duplicate.jsonl")
	if err := os.WriteFile(path, []byte("{\"_id\":\"a\",\"text\":\"one\"}\n{\"_id\":\"a\",\"text\":\"two\"}\n"), 0600); err != nil {
		t.Fatal(err)
	}
	for _, args := range [][]string{{"--documents", path, "--corpus", path}, {"--documents", path}, {"--documents", path, "--analyzer", "unknown"}} {
		var out, stderr bytes.Buffer
		if benchmarkCommand(args, strings.NewReader(""), &out, &stderr) == 0 || out.Len() != 0 {
			t.Fatal("invalid control accepted")
		}
	}
}
