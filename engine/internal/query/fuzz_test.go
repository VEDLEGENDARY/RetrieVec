package query

import "testing"

func FuzzParse(f *testing.F) {
	for _, seed := range []string{"red", `"red red" AND NOT blue`, "NOT NOT red", "(red OR blue)", "\xff"} {
		f.Add(seed)
	}
	f.Fuzz(func(t *testing.T, input string) {
		if len(input) > 20000 {
			t.Skip()
		}
		node, err := Parse(input)
		if err == nil && (node == nil || len(PositiveTerms(node)) == 0) {
			t.Fatal("invalid successful parse")
		}
	})
}
