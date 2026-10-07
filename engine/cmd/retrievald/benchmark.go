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
	"strings"
	"time"
)

// Offline diagnostic transport over the shipped index and scoring implementation.
// No listener, registry access, or application authorization bypass is introduced.
func benchmarkCommand(args []string, input io.Reader, output, stderr io.Writer) int {
	flags := flag.NewFlagSet("benchmark", flag.ContinueOnError)
	flags.SetOutput(stderr)
	directory := flags.String("corpus", "", "validated corpus snapshot")
	documentsPath := flags.String("documents", "", "offline BEIR JSONL document control; title plus text")
	analyzer := flags.String("analyzer", "unicode", "offline document control or versioned corpus analyzer")
	if flags.Parse(args) != nil || (*directory == "") == (*documentsPath == "") || flags.NArg() != 0 {
		return 2
	}
	started := time.Now()
	var documents []corpus.Document
	var identity string
	var err error
	if *documentsPath != "" {
		documents, identity, err = benchmarkDocuments(*documentsPath, *analyzer)
	} else {
		var snapshot *corpus.Snapshot
		snapshot, err = corpus.Load(*directory)
		if err == nil {
			documents, identity = snapshot.Documents, snapshot.Manifest.SnapshotID
		}
	}
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 1
	}
	analyzerVersion := analysis.Version
	if *directory != "" && *analyzer != "unicode" {
		analyzerVersion = *analyzer
	}
	idx, err := index.BuildVersion(documents, analyzerVersion)
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 1
	}
	encoder := json.NewEncoder(output)
	if encoder.Encode(map[string]any{"snapshot_id": identity, "analyzer_control": *analyzer, "analyzer_version": idx.Stats().AnalyzerVersion, "document_count": len(documents), "build_ms": float64(time.Since(started).Microseconds()) / 1000}) != nil {
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
		query, err := normalizeBenchmarkText(request.Query, *analyzer)
		if err != nil {
			cancel()
			fmt.Fprintln(stderr, err)
			return 2
		}
		result := search.Result{}
		if strings.TrimSpace(query) != "" {
			result, err = search.Execute(ctx, idx, search.Request{Query: query, Mode: "free_text", TopK: request.TopK}, config)
		}
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
