package scoring

import (
	"container/heap"
	"context"
	"fmt"
	"retrievec/engine/internal/index"
)

type scoreHeap []Score

func (values scoreHeap) Len() int { return len(values) }
func (values scoreHeap) Less(i, j int) bool {
	// Root is the worst retained score. A larger ID loses equal-score ties.
	if values[i].Value != values[j].Value {
		return values[i].Value < values[j].Value
	}
	return values[i].ID > values[j].ID
}
func (values scoreHeap) Swap(i, j int) { values[i], values[j] = values[j], values[i] }
func (values *scoreHeap) Push(value any) { *values = append(*values, value.(Score)) }
func (values *scoreHeap) Pop() any {
	old := *values
	value := old[len(old)-1]
	*values = old[:len(old)-1]
	return value
}

func better(left, right Score) bool {
	return left.Value > right.Value || (left.Value == right.Value && left.ID < right.ID)
}

// RankTopK is an opt-in parity prototype that preserves RankContext as reference.
// It deliberately remains outside search execution: the current implementation
// starts from the sorted reference and therefore demonstrates no optimization.
// Profiling and an unsorted scoring boundary are required before retention.
func RankTopK(ctx context.Context, idx index.Reader, terms []string, candidates map[int]bool, config Config, k int) ([]Score, error) {
	if k < 1 || k > 1000 {
		return nil, fmt.Errorf("invalid top-k bound")
	}
	reference, err := RankContext(ctx, idx, terms, candidates, config)
	if err != nil || len(reference) <= k {
		return reference, err
	}
	retained := &scoreHeap{}
	heap.Init(retained)
	for _, score := range reference {
		if retained.Len() < k {
			heap.Push(retained, score)
		} else if better(score, (*retained)[0]) {
			heap.Pop(retained)
			heap.Push(retained, score)
		}
	}
	result := make([]Score, retained.Len())
	for at := len(result) - 1; at >= 0; at-- {
		result[at] = heap.Pop(retained).(Score)
	}
	return result, nil
}
