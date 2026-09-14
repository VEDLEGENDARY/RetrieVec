package analysis

import (
	"fmt"
	"strings"
	"unicode"
	"unicode/utf8"
)

// Version pins both tokenization behavior and the Unicode tables used by Go.
const Version = "analyzer-v1-unicode-" + unicode.Version

// Token carries a normalized term and its location in the original UTF-8 text.
type Token struct {
	Term     string `json:"term"`
	Position int    `json:"position"`
	Start    int    `json:"start"`
	End      int    `json:"end"`
}

// Analyze retains letter/digit runs, using simple Unicode lowercase without normalization.
func Analyze(text string) ([]Token, error) {
	if !utf8.ValidString(text) {
		return nil, fmt.Errorf("analyze: invalid UTF-8")
	}
	tokens := make([]Token, 0)
	start := -1
	var term strings.Builder
	emit := func(end int) {
		if start >= 0 {
			tokens = append(tokens, Token{Term: term.String(), Position: len(tokens), Start: start, End: end})
			term.Reset()
			start = -1
		}
	}
	for offset, r := range text {
		if unicode.IsLetter(r) || unicode.IsDigit(r) {
			if start < 0 {
				start = offset
			}
			term.WriteRune(unicode.ToLower(r))
		} else {
			emit(offset)
		}
	}
	emit(len(text))
	return tokens, nil
}
