package analysis

import (
	"encoding/json"
	"os"
	"reflect"
	"strings"
	"testing"
	"unicode"
)

func TestSharedFixtures(t *testing.T) {
	data, err := os.ReadFile("../../../datasets/fixtures/analyzer-v1.json")
	if err != nil {
		t.Fatal(err)
	}
	var fixtures []struct {
		Text  string
		Terms []string
	}
	if err := json.Unmarshal(data, &fixtures); err != nil {
		t.Fatal(err)
	}
	for _, fixture := range fixtures {
		t.Run(fixture.Text, func(t *testing.T) {
			got, err := Analyze(fixture.Text)
			if err != nil {
				t.Fatal(err)
			}
			terms := make([]string, 0, len(got))
			lastEnd := 0
			for pos, token := range got {
				if token.Position != pos || token.Start < lastEnd || token.End <= token.Start || token.End > len(fixture.Text) {
					t.Fatalf("invalid offsets/position: %+v", token)
				}
				if strings.Map(unicode.ToLower, fixture.Text[token.Start:token.End]) != token.Term {
					t.Fatalf("token does not match original slice: %+v", token)
				}
				terms = append(terms, token.Term)
				lastEnd = token.End
			}
			if !reflect.DeepEqual(terms, fixture.Terms) {
				t.Fatalf("terms = %v, want %v", terms, fixture.Terms)
			}
		})
	}
}

func TestByteOffsets(t *testing.T) {
	got, err := Analyze("É x")
	want := []Token{{Term: "é", Position: 0, Start: 0, End: 2}, {Term: "x", Position: 1, Start: 3, End: 4}}
	if err != nil || !reflect.DeepEqual(got, want) {
		t.Fatalf("got %v, %v; want %v", got, err, want)
	}
}

func TestInvalidUTF8(t *testing.T) {
	if _, err := Analyze(string([]byte{0xff})); err == nil {
		t.Fatal("accepted invalid UTF-8")
	}
}
