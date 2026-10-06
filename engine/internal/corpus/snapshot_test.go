package corpus

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestConfigurationRejectsNoncanonicalNegativeZero(t *testing.T) {
	root := "../../../datasets/fixtures/snapshots/ss_4415a7c573a87a239ee65b0581664ea667b3988e4be43cb7f3bd069380ee0811"
	for _, spelling := range []string{"0", "-1", "-0"} {
		t.Run(spelling, func(t *testing.T) {
			target := t.TempDir()
			for _, name := range []string{"manifest.json", "papers.jsonl", "chunks.jsonl"} {
				data, err := os.ReadFile(filepath.Join(root, name))
				if err != nil {
					t.Fatal(err)
				}
				if name == "manifest.json" {
					var fields map[string]any
					decoder := json.NewDecoder(bytes.NewReader(data))
					decoder.UseNumber()
					if err := decoder.Decode(&fields); err != nil {
						t.Fatal(err)
					}
					delete(fields, "snapshot_id")
					fields["configuration"].(map[string]any)["review_control"] = json.Number(spelling)
					fields["snapshot_id"] = identity("ss_", fields)
					data, err = canonical(fields)
					if err != nil {
						t.Fatal(err)
					}
					data = append(data, '\n')
				}
				if err := os.WriteFile(filepath.Join(target, name), data, 0600); err != nil {
					t.Fatal(err)
				}
			}
			_, err := Load(target)
			if spelling == "-0" && err == nil {
				t.Fatal("noncanonical negative zero was accepted")
			}
			if spelling != "-0" && err != nil {
				t.Fatal(err)
			}
		})
	}
}

func TestAggregateChunkBoundIsStillEnforced(t *testing.T) {
	for _, item := range []struct {
		name string
		size int64
	}{
		{"chunks.jsonl", maxChunkFileBytes + 1},
		{"papers.jsonl", maxFileBytes + 1},
		{"manifest.json", maxFileBytes + 1},
	} {
		t.Run(item.name, func(t *testing.T) {
			directory := t.TempDir()
			path := filepath.Join(directory, item.name)
			file, err := os.Create(path)
			if err != nil {
				t.Fatal(err)
			}
			if err := file.Truncate(item.size); err != nil {
				t.Fatal(err)
			}
			if err := file.Close(); err != nil {
				t.Fatal(err)
			}
			if _, err := readFile(directory, item.name); err == nil {
				t.Fatal("oversized artifact was accepted")
			}
		})
	}
}

func TestLoadCanonicalSnapshotAndRejectCorruption(t *testing.T) {
	root := "../../../datasets/fixtures/snapshots/ss_4415a7c573a87a239ee65b0581664ea667b3988e4be43cb7f3bd069380ee0811"
	snapshot, err := Load(root)
	if err != nil {
		t.Fatal(err)
	}
	if len(snapshot.Documents) != 12 || len(snapshot.Papers) != 12 {
		t.Fatal("incorrect counts")
	}
	target := t.TempDir()
	for _, name := range []string{"manifest.json", "papers.jsonl", "chunks.jsonl"} {
		data, err := os.ReadFile(filepath.Join(root, name))
		if err != nil {
			t.Fatal(err)
		}
		if name == "chunks.jsonl" {
			data[10] ^= 1
		}
		if err := os.WriteFile(filepath.Join(target, name), data, 0600); err != nil {
			t.Fatal(err)
		}
	}
	if _, err := Load(target); err == nil {
		t.Fatal("corruption accepted")
	}
}
