package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"unicode/utf8"

	"retrievec/engine/internal/analysis"
)

const maxAnalysisBytes = 8 * 1024 * 1024

func analyzeCommand(stdin io.Reader, stdout, stderr io.Writer) int {
	data, err := io.ReadAll(io.LimitReader(stdin, maxAnalysisBytes+1))
	if err != nil || len(data) > maxAnalysisBytes || !utf8.Valid(data) {
		fmt.Fprintln(stderr, "analyze: unreadable, oversized, or invalid UTF-8 input")
		return 2
	}
	var request struct {
		Texts []string `json:"texts"`
	}
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&request); err != nil {
		fmt.Fprintln(stderr, "analyze: expected a JSON object with texts")
		return 2
	}
	var extra any
	if decoder.Decode(&extra) != io.EOF || request.Texts == nil || len(request.Texts) > 256 {
		fmt.Fprintln(stderr, "analyze: expected one object and at most 256 texts")
		return 2
	}
	tokens := make([][]analysis.Token, 0, len(request.Texts))
	for _, text := range request.Texts {
		if len(text) > 1024*1024 {
			fmt.Fprintln(stderr, "analyze: text exceeds 1 MiB")
			return 2
		}
		result, err := analysis.Analyze(text)
		if err != nil {
			fmt.Fprintln(stderr, err)
			return 2
		}
		tokens = append(tokens, result)
	}
	response := struct {
		AnalyzerVersion string             `json:"analyzer_version"`
		Tokens          [][]analysis.Token `json:"tokens"`
	}{analysis.Version, tokens}
	if err := json.NewEncoder(stdout).Encode(response); err != nil {
		fmt.Fprintln(stderr, "analyze: write response:", err)
		return 1
	}
	return 0
}
