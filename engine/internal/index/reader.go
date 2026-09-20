package index

import "retrievallab/engine/internal/corpus"

// Reader is the shared immutable search boundary for memory and disk snapshots.
type Reader interface {
	Stats() Statistics
	ReadPostings(string) ([]Posting, error)
	Document(int) (corpus.Document, bool)
	ChunkLength(int) (int, bool)
}

func (i *Index) ReadPostings(term string) ([]Posting, error) { return i.Postings(term), nil }
