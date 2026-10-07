package main

import (
	"bufio"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"strings"
	"unicode/utf8"

	"github.com/kljensen/snowball/english"
	"retrievec/engine/internal/analysis"
	"retrievec/engine/internal/corpus"
)

// Offline ablations only. The product analyzer and immutable indexes are unchanged.
const englishControlStopwords = "a an and are as at be but by for if in into is it no not of on or such that the their then there these they this to was will with"

func normalizeBenchmarkText(text, mode string) (string, error) {
	if mode == "unicode" {
		return text, nil
	}
	if mode != "english_stopwords" && mode != "snowball_english" && mode != "english_stopwords_snowball" {
		return "", fmt.Errorf("unknown benchmark analyzer")
	}
	tokens, err := analysis.Analyze(text)
	if err != nil {
		return "", err
	}
	stop := strings.Contains(mode, "stopwords")
	stem := strings.Contains(mode, "snowball")
	terms := make([]string, 0, len(tokens))
	for _, token := range tokens {
		term := token.Term
		if stop && strings.Contains(" "+englishControlStopwords+" ", " "+term+" ") {
			continue
		}
		if stem {
			term = english.Stem(term, false)
		}
		terms = append(terms, term)
	}
	return strings.Join(terms, " "), nil
}

func benchmarkDocuments(path, mode string) ([]corpus.Document, string, error) {
	source, err := os.Open(path)
	if err != nil {
		return nil, "", err
	}
	defer source.Close()
	stat, err := source.Stat()
	if err != nil || stat.Size() > 512<<20 {
		return nil, "", fmt.Errorf("invalid document control size")
	}
	hash := sha256.New()
	scanner := bufio.NewScanner(io.TeeReader(source, hash))
	scanner.Buffer(make([]byte, 4096), 16<<20)
	documents := []corpus.Document{}
	for scanner.Scan() {
		var row struct {
			ID    string `json:"_id"`
			Title string `json:"title"`
			Text  string `json:"text"`
		}
		if !utf8.Valid(scanner.Bytes()) {
			return nil, "", fmt.Errorf("invalid document UTF-8")
		}
		if err := json.Unmarshal(scanner.Bytes(), &row); err != nil {
			return nil, "", err
		}
		if row.ID == "" {
			return nil, "", fmt.Errorf("missing document identity")
		}
		text, err := normalizeBenchmarkText(row.Title+"\n\n"+row.Text, mode)
		if err != nil {
			return nil, "", err
		}
		documents = append(documents, corpus.Document{Chunk: corpus.Chunk{ChunkID: row.ID, PaperID: row.ID, PaperVersionID: "beir-" + row.ID, CollectionID: "beir-document-control", Text: text}, Title: row.Title})
	}
	if err := scanner.Err(); err != nil {
		return nil, "", err
	}
	return documents, "beir-records-sha256-" + hex.EncodeToString(hash.Sum(nil)), nil
}
