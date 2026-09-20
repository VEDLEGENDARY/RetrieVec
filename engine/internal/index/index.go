package index

import (
	"fmt"
	"slices"
	"sort"

	"retrievec/engine/internal/analysis"
	"retrievec/engine/internal/corpus"
)

// Posting records all positions of one term within an internal chunk ID.
type Posting struct {
	InternalChunkID int   `json:"internal_chunk_id"`
	TermFrequency   int   `json:"term_frequency"`
	Positions       []int `json:"positions"`
}

// Statistics describe one immutable loaded collection.
type Statistics struct {
	ChunkCount         int     `json:"chunk_count"`
	TermCount          int     `json:"term_count"`
	TotalTokens        int     `json:"total_tokens"`
	AverageChunkLength float64 `json:"average_chunk_length"`
	AnalyzerVersion    string  `json:"analyzer_version"`
}

// Index owns its storage; accessors return copies safe for concurrent readers.
type Index struct {
	postings    map[string][]Posting
	lengths     []int
	documents   []corpus.Document
	externalIDs map[string]int
	terms       []string
	stats       Statistics
}

func copyDocument(document corpus.Document) corpus.Document {
	document.PageRange = slices.Clone(document.PageRange)
	return document
}

// Build assigns internal IDs in external-ID order and rejects unindexable input.
func Build(documents []corpus.Document) (*Index, error) {
	if len(documents) == 0 {
		return nil, fmt.Errorf("index: empty corpus")
	}
	ordered := slices.Clone(documents)
	sort.Slice(ordered, func(i, j int) bool { return ordered[i].ChunkID < ordered[j].ChunkID })
	result := &Index{postings: make(map[string][]Posting), externalIDs: make(map[string]int),
		lengths: make([]int, 0, len(ordered)), documents: make([]corpus.Document, 0, len(ordered))}
	collection := ordered[0].CollectionID
	if collection == "" {
		return nil, fmt.Errorf("index: missing collection")
	}
	for id, document := range ordered {
		if document.ChunkID == "" || document.PaperID == "" || document.PaperVersionID == "" || document.CollectionID != collection {
			return nil, fmt.Errorf("index: missing metadata or mixed collection")
		}
		if _, exists := result.externalIDs[document.ChunkID]; exists {
			return nil, fmt.Errorf("index: duplicate chunk ID %s", document.ChunkID)
		}
		tokens, err := analysis.Analyze(document.Text)
		if err != nil {
			return nil, fmt.Errorf("index chunk %s: %w", document.ChunkID, err)
		}
		if len(tokens) == 0 {
			return nil, fmt.Errorf("index: zero-token chunk %s", document.ChunkID)
		}
		positions := map[string][]int{}
		for _, token := range tokens {
			positions[token.Term] = append(positions[token.Term], token.Position)
		}
		for term, offsets := range positions {
			result.postings[term] = append(result.postings[term], Posting{InternalChunkID: id, TermFrequency: len(offsets), Positions: offsets})
		}
		result.externalIDs[document.ChunkID] = id
		result.lengths = append(result.lengths, len(tokens))
		result.documents = append(result.documents, copyDocument(document))
		result.stats.TotalTokens += len(tokens)
	}
	result.terms = make([]string, 0, len(result.postings))
	for term := range result.postings {
		result.terms = append(result.terms, term)
	}
	sort.Strings(result.terms)
	result.stats.ChunkCount = len(ordered)
	result.stats.TermCount = len(result.terms)
	result.stats.AverageChunkLength = float64(result.stats.TotalTokens) / float64(len(ordered))
	result.stats.AnalyzerVersion = analysis.Version
	return result, nil
}

// Stats returns collection-wide statistics.
func (index *Index) Stats() Statistics { return index.stats }

// Terms returns a sorted copy of the vocabulary.
func (index *Index) Terms() []string { return slices.Clone(index.terms) }

// Postings returns copied postings and positions in internal-ID order.
func (index *Index) Postings(term string) []Posting {
	list := slices.Clone(index.postings[term])
	for i := range list {
		list[i].Positions = slices.Clone(list[i].Positions)
	}
	return list
}

// DocumentFrequency is the number of chunks containing the term.
func (index *Index) DocumentFrequency(term string) int { return len(index.postings[term]) }

// Lookup resolves a stable external chunk ID to its internal ID.
func (index *Index) Lookup(externalID string) (int, bool) {
	id, ok := index.externalIDs[externalID]
	return id, ok
}

// Document returns copied chunk metadata for a valid internal ID.
func (index *Index) Document(id int) (corpus.Document, bool) {
	if id < 0 || id >= len(index.documents) {
		return corpus.Document{}, false
	}
	return copyDocument(index.documents[id]), true
}

// ChunkLength returns the number of analyzed tokens for an internal ID.
func (index *Index) ChunkLength(id int) (int, bool) {
	if id < 0 || id >= len(index.lengths) {
		return 0, false
	}
	return index.lengths[id], true
}
