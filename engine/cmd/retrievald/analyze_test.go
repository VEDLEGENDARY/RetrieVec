package main

import (
	"bytes"
	"strings"
	"testing"
)

func TestAnalyzeCommand(t *testing.T) {
	for _, test := range []struct {
		input string
		code  int
	}{
		{`{"texts":["RAG-based", ""]}`, 0}, {`{"texts":[]}`, 0},
		{`{}`, 2}, {`{"texts":null}`, 2}, {`{"texts":[1]}`, 2},
		{`{"texts":[],"unknown":1}`, 2}, {`{"texts":[]} {}`, 2},
		{string([]byte{0xff}), 2}, {strings.Repeat("x", maxAnalysisBytes+1), 2},
	} {
		var out, stderr bytes.Buffer
		if code := analyzeCommand(strings.NewReader(test.input), &out, &stderr); code != test.code {
			t.Fatalf("code %d, want %d: %s", code, test.code, &stderr)
		}
		if test.code != 0 && out.Len() != 0 {
			t.Fatal("error produced partial output")
		}
	}
}
