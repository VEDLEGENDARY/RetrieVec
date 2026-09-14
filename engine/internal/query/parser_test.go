package query

import (
	"reflect"
	"strings"
	"testing"
)

func TestPrecedenceAndPositiveTerms(t *testing.T) {
	n, err := Parse(`alpha OR beta AND NOT gamma`)
	if err != nil {
		t.Fatal(err)
	}
	if n.Kind != "OR" || n.Right.Kind != "AND" || n.Right.Right.Kind != "NOT" {
		t.Fatalf("bad AST: %+v", n)
	}
	n, err = Parse(`NOT NOT alpha AND "a \\"b\\""`)
	_ = n
	_ = err
	n, err = Parse(`NOT NOT alpha AND "red red"`)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(PositiveTerms(n), []string{"alpha", "red"}) {
		t.Fatal(PositiveTerms(n))
	}
	if _, err := Parse(`"quote \"word\" and \\ slash"`); err != nil {
		t.Fatal(err)
	}
}
func TestMalformedAndBounds(t *testing.T) {
	for _, input := range []string{"", "a b", "a AND", "(a", "a)", "NOT a", `""`, `"a\q"`, `"a`, "rag-based", strings.Repeat("(", 33) + "a" + strings.Repeat(")", 33), strings.Repeat("a", 4097), `"` + strings.Repeat("a ", 257) + `"`, strings.Repeat("a OR ", 128) + "a"} {
		if _, err := Parse(input); err == nil {
			t.Errorf("accepted %q", input)
		}
	}
}
