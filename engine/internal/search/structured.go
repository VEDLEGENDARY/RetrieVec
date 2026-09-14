package search

import (
	"context"
	"retrievallab/engine/internal/index"
	"retrievallab/engine/internal/query"
	"sort"
)

func evaluate(ctx context.Context, idx *index.Index, node *query.Node) (map[int]bool, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	result := map[int]bool{}
	if node.Kind == "term" || node.Kind == "phrase" {
		lists := make([]map[int][]int, len(node.Terms))
		for i, term := range node.Terms {
			lists[i] = map[int][]int{}
			for _, p := range idx.Postings(term) {
				lists[i][p.InternalChunkID] = p.Positions
			}
		}
		for id, starts := range lists[0] {
			if err := ctx.Err(); err != nil {
				return nil, err
			}
			for _, start := range starts {
				matches := true
				for offset := 1; offset < len(lists); offset++ {
					positions := lists[offset][id]
					at := sort.SearchInts(positions, start+offset)
					if at == len(positions) || positions[at] != start+offset {
						matches = false
						break
					}
				}
				if matches {
					result[id] = true
					break
				}
			}
		}
		return result, nil
	}
	left, err := evaluate(ctx, idx, node.Left)
	if err != nil {
		return nil, err
	}
	if node.Kind == "NOT" {
		for id := 0; id < idx.Stats().ChunkCount; id++ {
			if id%256 == 0 {
				if err := ctx.Err(); err != nil {
					return nil, err
				}
			}
			if !left[id] {
				result[id] = true
			}
		}
		return result, nil
	}
	right, err := evaluate(ctx, idx, node.Right)
	if err != nil {
		return nil, err
	}
	for id := range left {
		if node.Kind == "OR" || right[id] {
			result[id] = true
		}
	}
	if node.Kind == "OR" {
		for id := range right {
			result[id] = true
		}
	}
	return result, nil
}
