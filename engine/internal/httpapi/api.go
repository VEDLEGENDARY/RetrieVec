package httpapi

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"retrievallab/engine/internal/analysis"
	"retrievallab/engine/internal/corpus"
	"retrievallab/engine/internal/index"
	"retrievallab/engine/internal/query"
	"retrievallab/engine/internal/scoring"
	"retrievallab/engine/internal/search"
	"sync/atomic"
	"time"
	"unicode/utf8"
)

const MaxBodyBytes = 32768

type API struct {
	idx                      *index.Index
	snapshotID, collectionID string
	sequence                 atomic.Uint64
	slots                    chan struct{}
}

func New(snapshot *corpus.Snapshot) (*API, error) {
	idx, err := index.Build(snapshot.Documents)
	if err != nil {
		return nil, err
	}
	if version, ok := snapshot.Manifest.Configuration["analyzer_version"]; ok && version != analysis.Version {
		return nil, fmt.Errorf("analyzer version mismatch")
	}
	return &API{idx: idx, snapshotID: snapshot.Manifest.SnapshotID, collectionID: snapshot.Manifest.CollectionID, slots: make(chan struct{}, 32)}, nil
}
func write(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}
func fail(w http.ResponseWriter, status int, code, message string) {
	write(w, status, map[string]any{"code": code, "message": message})
}
func (a *API) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	defer func() {
		if recover() != nil {
			fail(w, 500, "internal_error", "unexpected server failure")
		}
	}()
	expected := "GET"
	if r.URL.Path == "/v1/search" {
		expected = "POST"
	}
	if r.URL.Path != "/healthz" && r.URL.Path != "/readyz" && r.URL.Path != "/v1/stats" && r.URL.Path != "/v1/search" {
		fail(w, 404, "not_found", "unknown endpoint")
		return
	}
	if r.Method != expected {
		w.Header().Set("Allow", expected)
		fail(w, 405, "method_not_allowed", "unsupported method")
		return
	}
	if r.URL.Path == "/healthz" {
		write(w, 200, map[string]bool{"healthy": true})
		return
	}
	if a.idx == nil {
		fail(w, 503, "not_ready", "snapshot unavailable")
		return
	}
	if r.URL.Path == "/readyz" {
		write(w, 200, map[string]any{"ready": true, "snapshot_id": a.snapshotID})
		return
	}
	if r.URL.Path == "/v1/stats" {
		write(w, 200, map[string]any{"snapshot_id": a.snapshotID, "collection_id": a.collectionID, "analyzer_version": analysis.Version, "scoring_version": scoring.Version, "configuration": scoring.Default(), "statistics": a.idx.Stats()})
		return
	}
	select {
	case a.slots <- struct{}{}:
		defer func() { <-a.slots }()
	default:
		fail(w, 503, "busy", "request capacity reached")
		return
	}
	body, err := io.ReadAll(http.MaxBytesReader(w, r.Body, MaxBodyBytes))
	if err != nil {
		var large *http.MaxBytesError
		if errors.As(err, &large) {
			fail(w, 413, "body_too_large", "request body exceeds limit")
		} else {
			fail(w, 400, "invalid_input", "cannot read request")
		}
		return
	}
	if !utf8.Valid(body) {
		fail(w, 400, "invalid_input", "invalid UTF-8")
		return
	}
	var fields map[string]json.RawMessage
	decoder := json.NewDecoder(bytes.NewReader(body))
	opening, err := decoder.Token()
	if err != nil || opening != json.Delim('{') {
		fail(w, 400, "invalid_input", "expected JSON object")
		return
	}
	fields = map[string]json.RawMessage{}
	for decoder.More() {
		key, err := decoder.Token()
		if err != nil {
			fail(w, 400, "invalid_input", "invalid JSON")
			return
		}
		name, ok := key.(string)
		if !ok {
			fail(w, 400, "invalid_input", "invalid field")
			return
		}
		if _, exists := fields[name]; exists {
			fail(w, 400, "invalid_input", "duplicate field")
			return
		}
		var value json.RawMessage
		if decoder.Decode(&value) != nil {
			fail(w, 400, "invalid_input", "invalid JSON")
			return
		}
		fields[name] = value
	}
	if _, err := decoder.Token(); err != nil {
		fail(w, 400, "invalid_input", "invalid JSON")
		return
	}
	if decoder.Decode(new(any)) != io.EOF {
		fail(w, 400, "invalid_input", "trailing JSON")
		return
	}
	for key, value := range fields {
		if (key != "query" && key != "mode" && key != "top_k" && key != "explain") || bytes.Equal(value, []byte("null")) {
			fail(w, 400, "invalid_input", "unknown or null field")
			return
		}
	}
	for _, key := range []string{"query", "mode", "top_k"} {
		if _, ok := fields[key]; !ok {
			fail(w, 400, "invalid_input", "missing required field")
			return
		}
	}
	var request search.Request
	if json.Unmarshal(body, &request) != nil {
		fail(w, 400, "invalid_input", "invalid field type")
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	if request.TopK>100 {fail(w,400,"invalid_input","top_k exceeds HTTP limit");return}
	defer cancel()
	started := time.Now()
	result, err := search.Execute(ctx, a.idx, request, scoring.Default())
	if err != nil {
		var syntax *query.Error
		if errors.As(err, &syntax) {
			write(w, 400, map[string]any{"code": "invalid_query", "message": syntax.Message, "position": syntax.Position})
		} else if errors.Is(err, context.DeadlineExceeded) || errors.Is(err, context.Canceled) {
			fail(w, 503, "timeout", "search canceled")
		} else {
			fail(w, 400, "invalid_input", err.Error())
		}
		return
	}
	write(w, 200, map[string]any{"request_id": fmt.Sprintf("r-%d", a.sequence.Add(1)), "snapshot_id": a.snapshotID, "collection_id": a.collectionID, "analyzer_version": analysis.Version, "scoring_version": scoring.Version, "configuration": scoring.Default(), "total_matches": result.TotalMatches, "hits": result.Hits, "timings": map[string]float64{"search_ms": float64(time.Since(started).Nanoseconds()) / 1e6}})
}
