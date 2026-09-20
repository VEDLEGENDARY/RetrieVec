// Package snapshot owns immutable multi-segment readers and retrieval identities.
package snapshot

import (
	"bytes"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"retrievallab/engine/internal/analysis"
	"retrievallab/engine/internal/corpus"
	"retrievallab/engine/internal/index"
	"retrievallab/engine/internal/segment"
	"slices"
	"sort"
)

var identityPattern = regexp.MustCompile(`^(ss_|rs_|em_)?[0-9a-f]{64}$`)

func ValidID(value, prefix string) bool {
	return len(value) == len(prefix)+64 && len(prefix) <= len(value) && value[:len(prefix)] == prefix && identityPattern.MatchString(value)
}
func Hash(data []byte) string { return fmt.Sprintf("%x", sha256.Sum256(data)) }

type Manifest struct {
	SchemaVersion   int      `json:"schema_version"`
	CollectionID    string   `json:"collection_id"`
	CorpusID        string   `json:"corpus_snapshot_id"`
	CorpusHash      string   `json:"corpus_manifest_sha256"`
	Segments        []string `json:"segments"`
	StatisticsHash  string   `json:"statistics_sha256"`
	EmbeddingID     *string  `json:"embedding_id"`
	AnalyzerVersion string   `json:"analyzer_version"`
	Capabilities    []string `json:"capabilities"`
}
type Reader struct {
	ID          string
	Manifest    Manifest
	segments    []*segment.Reader
	global      [][]int
	documents   []corpus.Document
	lengths     []int
	stats       index.Statistics
	frequencies map[string]int
}

func (r *Reader) Close() error {
	var result error
	for _, s := range r.segments {
		if err := s.Close(); err != nil {
			result = err
		}
	}
	return result
}
func (r *Reader) Stats() index.Statistics { return r.stats }
func (r *Reader) Document(id int) (corpus.Document, bool) {
	if id < 0 || id >= len(r.documents) {
		return corpus.Document{}, false
	}
	doc := r.documents[id]
	doc.PageRange = slices.Clone(doc.PageRange)
	return doc, true
}
func (r *Reader) ChunkLength(id int) (int, bool) {
	if id < 0 || id >= len(r.lengths) {
		return 0, false
	}
	return r.lengths[id], true
}
func (r *Reader) ReadPostings(term string) ([]index.Posting, error) {
	result := []index.Posting{}
	for i, s := range r.segments {
		postings, err := s.Postings(term)
		if err != nil {
			return nil, err
		}
		for _, p := range postings {
			p.InternalChunkID = r.global[i][p.InternalChunkID]
			result = append(result, p)
		}
	}
	sort.Slice(result, func(i, j int) bool { return result[i].InternalChunkID < result[j].InternalChunkID })
	return result, nil
}
func (r *Reader) statisticsHash() (string, error) {
	data, err := corpus.Canonical(map[string]any{"chunk_count": r.stats.ChunkCount, "total_tokens": r.stats.TotalTokens, "document_frequencies": r.frequencies})
	return Hash(data), err
}

func load(root, id string, manifest Manifest) (result *Reader, err error) {
	if manifest.SchemaVersion != 1 || manifest.CollectionID == "" || manifest.AnalyzerVersion != analysis.Version || !ValidID(manifest.CorpusID, "ss_") || !ValidID(manifest.CorpusHash, "") {
		return nil, fmt.Errorf("invalid retrieval manifest")
	}
	if manifest.EmbeddingID == nil {
		if !slices.Equal(manifest.Capabilities, []string{"sparse"}) {
			return nil, fmt.Errorf("invalid sparse capabilities")
		}
	} else {
		if !ValidID(*manifest.EmbeddingID, "em_") || !slices.Equal(manifest.Capabilities, []string{"sparse", "dense", "hybrid"}) {
			return nil, fmt.Errorf("invalid hybrid capabilities")
		}
	}
	corpusPath := filepath.Join(root, "corpora", manifest.CorpusID)
	raw, err := os.ReadFile(filepath.Join(corpusPath, "manifest.json"))
	if err != nil || Hash(raw) != manifest.CorpusHash {
		return nil, fmt.Errorf("corpus manifest mismatch")
	}
	source, err := corpus.Load(corpusPath)
	if err != nil {
		return nil, err
	}
	if source.Manifest.CollectionID != manifest.CollectionID {
		return nil, fmt.Errorf("collection mismatch")
	}
	r := &Reader{ID: id, Manifest: manifest, frequencies: map[string]int{}, documents: source.Documents}
	defer func() {
		if err != nil {
			r.Close()
		}
	}()
	sort.Slice(r.documents, func(i, j int) bool { return r.documents[i].ChunkID < r.documents[j].ChunkID })
	byID := map[string]int{}
	for i, doc := range r.documents {
		byID[doc.ChunkID] = i
	}
	r.lengths = make([]int, len(r.documents))
	seen := map[string]bool{}
	segmentHashes := map[string]bool{}
	if len(manifest.Segments) > 1024 {
		return nil, fmt.Errorf("too many segments")
	}
	for _, hash := range manifest.Segments {
		if !ValidID(hash, "") || segmentHashes[hash] {
			return nil, fmt.Errorf("invalid or duplicate segment hash")
		}
		segmentHashes[hash] = true
		path := filepath.Join(root, "segments", hash+".seg")
		fileInfo, statErr := os.Lstat(path)
		if statErr != nil || !fileInfo.Mode().IsRegular() || fileInfo.Size() > segment.MaxFileBytes {
			return nil, fmt.Errorf("invalid segment file bounds")
		}
		raw, err := os.ReadFile(path)
		if err != nil || Hash(raw) != hash {
			return nil, fmt.Errorf("segment file hash mismatch")
		}
		s, err := segment.Open(path)
		if err != nil {
			return nil, err
		}
		r.segments = append(r.segments, s)
		mapping := make([]int, len(s.IDs))
		for local, key := range s.IDs {
			global, ok := byID[key]
			if !ok || seen[key] {
				return nil, fmt.Errorf("segments must be disjoint and match corpus")
			}
			seen[key] = true
			mapping[local] = global
			r.lengths[global] = s.Lengths[local]
		}
		r.global = append(r.global, mapping)
		r.stats.TotalTokens += s.TotalTokens
		for _, term := range s.Terms() {
			r.frequencies[term] += s.DocumentFrequency(term)
		}
	}
	if len(seen) != len(r.documents) {
		return nil, fmt.Errorf("incomplete segment coverage")
	}
	r.stats.ChunkCount = len(r.documents)
	r.stats.TermCount = len(r.frequencies)
	r.stats.AnalyzerVersion = analysis.Version
	if r.stats.ChunkCount > 0 {
		r.stats.AverageChunkLength = float64(r.stats.TotalTokens) / float64(r.stats.ChunkCount)
	}
	return r, nil
}

func Open(root, id string) (*Reader, error) {
	if !ValidID(id, "rs_") {
		return nil, fmt.Errorf("invalid retrieval ID")
	}
	path := filepath.Join(root, "snapshots", id, "manifest.json")
	info, err := os.Lstat(path)
	if err != nil || !info.Mode().IsRegular() || info.Size() > 4<<20 {
		return nil, fmt.Errorf("invalid snapshot manifest file")
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var manifest Manifest
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	if err = decoder.Decode(&manifest); err != nil {
		return nil, err
	}
	canonical, err := corpus.Canonical(manifest)
	if err != nil || !bytes.Equal(raw, append(canonical, '\n')) || "rs_"+Hash(canonical) != id {
		return nil, fmt.Errorf("retrieval identity mismatch")
	}
	r, err := load(root, id, manifest)
	if err != nil {
		return nil, err
	}
	hash, err := r.statisticsHash()
	if err != nil || hash != manifest.StatisticsHash {
		r.Close()
		return nil, fmt.Errorf("aggregate statistics mismatch")
	}
	return r, nil
}

// Build publishes a corpus and disjoint segments, then a content-addressed manifest.
func Build(root, sourcePath string, batch int, embeddingID *string) (string, error) {
	if batch < 1 || batch > 100000 {
		return "", fmt.Errorf("invalid segment batch size")
	}
	source, err := corpus.Load(sourcePath)
	if err != nil {
		return "", err
	}
	target := filepath.Join(root, "corpora", source.Manifest.SnapshotID)
	if err = os.MkdirAll(target, 0700); err != nil {
		return "", err
	}
	for _, name := range []string{"manifest.json", "papers.jsonl", "chunks.jsonl"} {
		raw, err := os.ReadFile(filepath.Join(sourcePath, name))
		if err != nil {
			return "", err
		}
		if err = publishFile(filepath.Join(target, name), raw); err != nil {
			return "", err
		}
	}
	manifestRaw, err := os.ReadFile(filepath.Join(target, "manifest.json"))
	if err != nil {
		return "", err
	}
	manifest := Manifest{SchemaVersion: 1, CollectionID: source.Manifest.CollectionID, CorpusID: source.Manifest.SnapshotID, CorpusHash: Hash(manifestRaw), Segments: []string{}, AnalyzerVersion: analysis.Version, EmbeddingID: embeddingID, Capabilities: []string{"sparse"}}
	if embeddingID != nil {
		manifest.Capabilities = []string{"sparse", "dense", "hybrid"}
	}
	for start := 0; start < len(source.Documents); start += batch {
		end := min(start+batch, len(source.Documents))
		idx, err := index.Build(source.Documents[start:end])
		if err != nil {
			return "", err
		}
		hash, err := segment.Publish(filepath.Join(root, "segments"), idx)
		if err != nil {
			return "", err
		}
		manifest.Segments = append(manifest.Segments, hash)
	}
	reader, err := load(root, "", manifest)
	if err != nil {
		return "", err
	}
	manifest.StatisticsHash, err = reader.statisticsHash()
	reader.Close()
	if err != nil {
		return "", err
	}
	raw, err := corpus.Canonical(manifest)
	if err != nil {
		return "", err
	}
	id := "rs_" + Hash(raw)
	path := filepath.Join(root, "snapshots", id, "manifest.json")
	if err = os.MkdirAll(filepath.Dir(path), 0700); err != nil {
		return "", err
	}
	if err = publishFile(path, append(raw, '\n')); err != nil {
		return "", err
	}
	verified, err := Open(root, id)
	if err != nil {
		return "", err
	}
	verified.Close()
	return id, nil
}
func publishFile(path string, data []byte) error {
	if old, err := os.ReadFile(path); err == nil {
		if !bytes.Equal(old, data) {
			return fmt.Errorf("immutable artifact conflict")
		}
		return nil
	}
	f, err := os.CreateTemp(filepath.Dir(path), ".artifact-")
	if err != nil {
		return err
	}
	defer os.Remove(f.Name())
	if _, err = f.Write(data); err == nil {
		err = f.Sync()
	}
	closeErr := f.Close()
	if err != nil {
		return err
	}
	if closeErr != nil {
		return closeErr
	}
	if err = os.Link(f.Name(), path); err != nil {
		old, e := os.ReadFile(path)
		if e != nil || !bytes.Equal(old, data) {
			return err
		}
	}
	return nil
}
