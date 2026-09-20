package search

import (
	"context"
	"fmt"
	"retrievec/engine/internal/analysis"
	"retrievec/engine/internal/index"
	"retrievec/engine/internal/query"
	"retrievec/engine/internal/scoring"
	"unicode/utf8"
)

type Request struct {
	Query   string `json:"query"`
	Mode    string `json:"mode"`
	TopK    int    `json:"top_k"`
	Explain bool   `json:"explain"`
}
type Hit struct {
	Rank           int                    `json:"rank"`
	ChunkID        string                 `json:"chunk_id"`
	PaperID        string                 `json:"paper_id"`
	PaperVersionID string                 `json:"paper_version_id"`
	Title          string                 `json:"title"`
	Score          float64                `json:"score"`
	Text           string                 `json:"text"`
	PageRange      []int                  `json:"page_range"`
	Contributions  []scoring.Contribution `json:"contributions,omitempty"`
}
type Result struct {
	TotalMatches int   `json:"total_matches"`
	Hits         []Hit `json:"hits"`
}

func Execute(ctx context.Context, idx index.Reader, request Request, config scoring.Config) (Result, error) {
	if !utf8.ValidString(request.Query) || utf8.RuneCountInString(request.Query) > 4096 || request.TopK < 1 || request.TopK > 1000 {
		return Result{}, fmt.Errorf("invalid query length or top_k")
	}
	terms := []string{}
	candidates := map[int]bool{}
	if request.Mode == "structured" {
		node, err := query.Parse(request.Query)
		if err != nil {
			return Result{}, err
		}
		terms = query.PositiveTerms(node)
		candidates, err = evaluate(ctx, idx, node)
		if err != nil {
			return Result{}, err
		}
	} else if request.Mode == "free_text" {
		tokens, err := analysis.Analyze(request.Query)
		if err != nil {
			return Result{}, err
		}
		if len(tokens) == 0 {
			return Result{}, fmt.Errorf("empty analyzed query")
		}
		for _, token := range tokens {
			if err := ctx.Err(); err != nil {
				return Result{}, err
			}
			terms = append(terms, token.Term)
			postings, err := idx.ReadPostings(token.Term)
			if err != nil {
				return Result{}, err
			}
			for _, p := range postings {
				candidates[p.InternalChunkID] = true
			}
		}
	} else {
		return Result{}, fmt.Errorf("unsupported mode")
	}
	ranked, err := scoring.RankContext(ctx, idx, terms, candidates, config)
	if err != nil {
		return Result{}, err
	}
	result := Result{TotalMatches: len(ranked), Hits: []Hit{}}
	for i, s := range ranked {
		if i >= request.TopK {
			break
		}
		doc, _ := idx.Document(s.ID)
		hit := Hit{Rank: i + 1, ChunkID: doc.ChunkID, PaperID: doc.PaperID, PaperVersionID: doc.PaperVersionID, Title: doc.Title, Score: s.Value, Text: doc.Text, PageRange: doc.PageRange}
		if request.Explain {
			hit.Contributions = s.Contributions
		}
		result.Hits = append(result.Hits, hit)
	}
	return result, ctx.Err()
}
