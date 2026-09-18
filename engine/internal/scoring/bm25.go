package scoring

import (
	"fmt"
	"math"
	"retrievallab/engine/internal/index"
	"sort"
)

const Version = "bm25-v1"

type Config struct {
	K1 float64 `json:"k1"`
	B  float64 `json:"b"`
}

func Default() Config { return Config{1.2, 0.75} }
func (c Config) Validate() error {
	if math.IsNaN(c.K1) || math.IsInf(c.K1, 0) || c.K1 <= 0 || math.IsNaN(c.B) || math.IsInf(c.B, 0) || c.B < 0 || c.B > 1 {
		return fmt.Errorf("invalid BM25 parameters")
	}
	return nil
}

type Contribution struct {
	Term  string  `json:"term"`
	Score float64 `json:"score"`
	TF    int     `json:"tf"`
	DF    int     `json:"df"`
}
type Score struct {
	ID            int
	Value         float64
	Contributions []Contribution
}

// Rank scores the supplied candidates, including zero-score matches, in stable order.
func Rank(idx index.Reader, terms []string, candidates map[int]bool, config Config) ([]Score, error) {
	if err := config.Validate(); err != nil {
		return nil, err
	}
	unique := map[string]bool{}
	for _, term := range terms {
		unique[term] = true
	}
	ordered := make([]string, 0, len(unique))
	for term := range unique {
		ordered = append(ordered, term)
	}
	sort.Strings(ordered)
	scores := map[int]*Score{}
	for id := range candidates {
		if _, ok := idx.ChunkLength(id); !ok {
			return nil, fmt.Errorf("invalid candidate")
		}
		scores[id] = &Score{ID: id, Contributions: []Contribution{}}
	}
	stats := idx.Stats()
	for _, term := range ordered {
		postings, err := idx.ReadPostings(term); if err != nil {return nil,err}
		df := len(postings)
		idf := math.Log1p((float64(stats.ChunkCount-df) + 0.5) / (float64(df) + 0.5))
		for _, p := range postings {
			s, ok := scores[p.InternalChunkID]
			if !ok {
				continue
			}
			length, _ := idx.ChunkLength(p.InternalChunkID)
			// Divide through by k1 to avoid overflow for large finite parameters.
			tf := float64(p.TermFrequency)
			norm := 1 - config.B + config.B*float64(length)/stats.AverageChunkLength
			value := idf * tf * ((1 + 1/config.K1) / (tf/config.K1 + norm))
			if config.K1 < 1 {
				value = idf * tf * (config.K1 + 1) / (tf + config.K1*norm)
			}
			if math.IsNaN(value) || math.IsInf(value, 0) {
				return nil, fmt.Errorf("nonfinite BM25 score")
			}
			s.Value += value
			s.Contributions = append(s.Contributions, Contribution{term, value, p.TermFrequency, df})
		}
	}
	result := make([]Score, 0, len(scores))
	for _, s := range scores {
		result = append(result, *s)
	}
	sort.Slice(result, func(i, j int) bool {
		if result[i].Value != result[j].Value {
			return result[i].Value > result[j].Value
		}
		return result[i].ID < result[j].ID
	})
	return result, nil
}
