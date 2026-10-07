package analysis

import (
	"fmt"
	"strings"
	"unicode"
	"unicode/utf8"

	"github.com/kljensen/snowball"
)

// Version pins both tokenization behavior and the Unicode tables used by Go.
const Version = "analyzer-v1-unicode-" + unicode.Version

// StemmedVersion is an experimental English Snowball analyzer. V1 stays the default.
const StemmedVersion = "analyzer-v2-snowball-en-0.10.0-unicode-" + unicode.Version

func Supported(version string) bool { return version == Version || version == StemmedVersion }

func AnalyzeVersion(text, version string) ([]Token, error) {
	if !Supported(version) {
		return nil, fmt.Errorf("unsupported analyzer version %q", version)
	}
	tokens, err := Analyze(text)
	if err != nil || version == Version {
		return tokens, err
	}
	for i := range tokens {
		// Snowball English is applied only to ASCII letter terms; Unicode and
		// numeric tokens retain v1 normalization and offsets.
		asciiLetters := tokens[i].Term != ""
		for _, r := range tokens[i].Term {
			if r < 'a' || r > 'z' {
				asciiLetters = false
				break
			}
		}
		if asciiLetters {
			tokens[i].Term, err = snowball.Stem(tokens[i].Term, "english", true)
			if err != nil {
				return nil, err
			}
		}
	}
	return tokens, nil
}

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
