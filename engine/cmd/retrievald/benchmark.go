package main

import (
	"bufio"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"retrievec/engine/internal/analysis"
	"retrievec/engine/internal/corpus"
	"retrievec/engine/internal/index"
	"retrievec/engine/internal/scoring"
	"retrievec/engine/internal/search"
	"time"
)

// Offline diagnostic transport over the shipped index and scoring implementation.
// No listener, registry access, or application authorization bypass is introduced.
func benchmarkCommand(args []string, input io.Reader, output, stderr io.Writer) int {
	flags := flag.NewFlagSet("benchmark", flag.ContinueOnError)
	flags.SetOutput(stderr)
	directory := flags.String("corpus", "", "validated corpus snapshot")
	analyzerVersion := flags.String("analyzer", analysis.Version, "versioned analyzer (default v1)")
	if flags.Parse(args) != nil || *directory == "" || flags.NArg() != 0 {
		return 2
	}
	started := time.Now()
	snapshot, err := corpus.Load(*directory)
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 1
	}
	idx, err := index.BuildVersion(snapshot.Documents, *analyzerVersion)
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 1
	}
	encoder := json.NewEncoder(output)
	if encoder.Encode(map[string]any{"snapshot_id": snapshot.Manifest.SnapshotID, "analyzer_version": idx.Stats().AnalyzerVersion, "build_ms": float64(time.Since(started).Microseconds()) / 1000}) != nil {
		return 1
	}
	scanner := bufio.NewScanner(input)
	scanner.Buffer(make([]byte, 4096), 32768)
	for scanner.Scan() {
		var request struct {
			Query string  `json:"query"`
			TopK  int     `json:"top_k"`
			K1    float64 `json:"k1"`
			B     float64 `json:"b"`
		}
		if err := json.Unmarshal(scanner.Bytes(), &request); err != nil {
			fmt.Fprintln(stderr, err)
			return 2
		}
		config := scoring.Config{K1: request.K1, B: request.B}
		if err := config.Validate(); err != nil {
			fmt.Fprintln(stderr, err)
			return 2
		}
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		started := time.Now()
		result, err := search.Execute(ctx, idx, search.Request{Query: request.Query, Mode: "free_text", TopK: request.TopK}, config)
		cancel()
		if err != nil {
			fmt.Fprintln(stderr, err)
			return 1
		}
		hits := make([]map[string]any, len(result.Hits))
		for i, hit := range result.Hits {
			hits[i] = map[string]any{"chunk_id": hit.ChunkID, "paper_id": hit.PaperID, "score": hit.Score}
		}
		if encoder.Encode(map[string]any{"hits": hits, "elapsed_ms": float64(time.Since(started).Microseconds()) / 1000}) != nil {
			return 1
		}
	}
	if err := scanner.Err(); err != nil {
		fmt.Fprintln(stderr, err)
		return 1
	}
	return 0
}
