package segment

import (
	"os"
	"path/filepath"
	"retrievec/engine/internal/corpus"
	"retrievec/engine/internal/index"
	"testing"
)

func compactFixture(t *testing.T, directory, id, text string) string {
	t.Helper()
	idx, err := index.Build([]corpus.Document{{Chunk: corpus.Chunk{ChunkID: id, PaperID: "paper-" + id, PaperVersionID: "v1", CollectionID: "collection", Text: text}}})
	if err != nil {
		t.Fatal(err)
	}
	hash, err := Publish(directory, idx)
	if err != nil {
		t.Fatal(err)
	}
	return filepath.Join(directory, hash+".seg")
}

func TestCompactionPreservesPinnedReadersAndExternalIDs(t *testing.T) {
	directory := t.TempDir()
	first := compactFixture(t, directory, "chunk-a", "dense retrieval")
	second := compactFixture(t, directory, "chunk-b", "sparse retrieval")
	pinned, err := Open(first)
	if err != nil {
		t.Fatal(err)
	}
	defer pinned.Close()
	hash, err := Compact(directory, []string{first, second})
	if err != nil {
		t.Fatal(err)
	}
	merged, err := Open(filepath.Join(directory, hash+".seg"))
	if err != nil {
		t.Fatal(err)
	}
	defer merged.Close()
	if len(merged.IDs) != 2 || merged.IDs[0] != "chunk-a" || merged.IDs[1] != "chunk-b" || merged.TotalTokens != 4 {
		t.Fatalf("unexpected compacted table: ids=%v tokens=%d", merged.IDs, merged.TotalTokens)
	}
	if postings, err := pinned.Postings("dense"); err != nil || len(postings) != 1 {
		t.Fatalf("pinned source reader changed after publication: %v %v", postings, err)
	}
	if _, err := os.Stat(first); err != nil {
		t.Fatalf("referenced source removed: %v", err)
	}
}

func TestCompactionFailurePublishesNothing(t *testing.T) {
	directory := t.TempDir()
	first := compactFixture(t, directory, "same", "dense retrieval")
	otherDirectory := t.TempDir()
	second := compactFixture(t, otherDirectory, "same", "sparse retrieval")
	before, _ := filepath.Glob(filepath.Join(directory, "*.seg"))
	if _, err := Compact(directory, []string{first, second}); err == nil {
		t.Fatal("expected duplicate external ID rejection")
	}
	after, _ := filepath.Glob(filepath.Join(directory, "*.seg"))
	if len(before) != len(after) {
		t.Fatalf("failed compaction published output: before=%v after=%v", before, after)
	}
}
