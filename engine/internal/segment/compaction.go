package segment

import (
	"bytes"
	"crypto/sha256"
	"encoding/binary"
	"fmt"
	"os"
	"path/filepath"
	"retrievec/engine/internal/index"
	"sort"
)

type compactDocument struct {
	id     string
	length int
	source int
	local  int
}

// Compact merges immutable segments without changing RLSEG001 or external IDs.
// Publication remains content addressed, validated and atomic. Source files are
// never removed; retention belongs to the snapshot registry.
func Compact(directory string, sourcePaths []string) (string, error) {
	if len(sourcePaths) < 2 || len(sourcePaths) > 1024 {
		return "", fmt.Errorf("compaction requires 2-1024 source segments")
	}
	readers := make([]*Reader, 0, len(sourcePaths))
	defer func() {
		for _, reader := range readers {
			reader.Close()
		}
	}()
	documents := []compactDocument{}
	for source, path := range sourcePaths {
		reader, err := Open(path)
		if err != nil {
			return "", fmt.Errorf("open compaction source %d: %w", source, err)
		}
		readers = append(readers, reader)
		for local, id := range reader.IDs {
			documents = append(documents, compactDocument{id, reader.Lengths[local], source, local})
		}
	}
	sort.Slice(documents, func(i, j int) bool { return documents[i].id < documents[j].id })
	for at := range documents {
		if at > 0 && documents[at-1].id == documents[at].id {
			return "", fmt.Errorf("duplicate external ID during compaction")
		}
	}
	remap := make([][]int, len(readers))
	for source, reader := range readers {
		remap[source] = make([]int, len(reader.IDs))
	}
	ids, lengths := make([]string, len(documents)), make([]int, len(documents))
	for global, document := range documents {
		ids[global], lengths[global] = document.id, document.length
		remap[document.source][document.local] = global
	}
	terms := map[string][]index.Posting{}
	for source, reader := range readers {
		for _, term := range reader.Terms() {
			postings, err := reader.Postings(term)
			if err != nil {
				return "", fmt.Errorf("decode compaction term: %w", err)
			}
			for _, posting := range postings {
				posting.InternalChunkID = remap[source][posting.InternalChunkID]
				terms[term] = append(terms[term], posting)
			}
		}
	}
	for term := range terms {
		sort.Slice(terms[term], func(i, j int) bool {
			return terms[term][i].InternalChunkID < terms[term][j].InternalChunkID
		})
	}
	data, err := encodeCompacted(ids, lengths, terms)
	if err != nil {
		return "", err
	}
	return publishCompacted(directory, data)
}

func encodeCompacted(ids []string, lengths []int, postings map[string][]index.Posting) ([]byte, error) {
	chunks := []byte{}
	total := 0
	for at, id := range ids {
		if id == "" || len(id) > MaxStringBytes || lengths[at] <= 0 {
			return nil, fmt.Errorf("invalid compacted chunk table")
		}
		chunks = appendString(chunks, id)
		chunks = appendVar(chunks, uint64(lengths[at]))
		total += lengths[at]
	}
	terms := make([]string, 0, len(postings))
	for term := range postings {
		terms = append(terms, term)
	}
	sort.Strings(terms)
	lists := make([][]byte, len(terms))
	dictionarySize := 0
	for at, term := range terms {
		lastID := 0
		for position, posting := range postings[term] {
			if (position > 0 && posting.InternalChunkID <= lastID) || posting.TermFrequency != len(posting.Positions) {
				return nil, fmt.Errorf("invalid compacted postings")
			}
			lists[at] = appendVar(lists[at], uint64(posting.InternalChunkID-lastID))
			lists[at] = appendVar(lists[at], uint64(posting.TermFrequency))
			lastPosition := 0
			for _, value := range posting.Positions {
				lists[at] = appendVar(lists[at], uint64(value-lastPosition))
				lastPosition = value
			}
			lastID = posting.InternalChunkID
		}
		dictionarySize += len(appendVar(appendString(nil, term), uint64(len(postings[term])))) + 16
	}
	dictionary := []byte{}
	offset := 96 + len(chunks) + dictionarySize
	for at, term := range terms {
		dictionary = appendString(dictionary, term)
		dictionary = appendVar(dictionary, uint64(len(postings[term])))
		dictionary = binary.LittleEndian.AppendUint64(dictionary, uint64(offset))
		dictionary = binary.LittleEndian.AppendUint64(dictionary, uint64(len(lists[at])))
		offset += len(lists[at])
	}
	if offset+32 > MaxFileBytes {
		return nil, fmt.Errorf("compacted segment exceeds size limit")
	}
	header := make([]byte, 96)
	copy(header, "RLSEG001")
	binary.LittleEndian.PutUint16(header[8:], 1)
	binary.LittleEndian.PutUint32(header[12:], 96)
	for at, value := range map[int]uint64{16: uint64(offset + 32), 24: uint64(len(ids)), 32: uint64(len(terms)), 40: 96, 48: uint64(96 + len(chunks)), 56: uint64(96 + len(chunks) + len(dictionary)), 64: uint64(offset), 72: uint64(total)} {
		binary.LittleEndian.PutUint64(header[at:], value)
	}
	data := bytes.Join(append([][]byte{header, chunks, dictionary}, lists...), nil)
	sum := sha256.Sum256(data)
	return append(data, sum[:]...), nil
}

func publishCompacted(directory string, data []byte) (string, error) {
	sum := sha256.Sum256(data)
	name := fmt.Sprintf("%x", sum)
	if err := os.MkdirAll(directory, 0700); err != nil {
		return "", err
	}
	target := filepath.Join(directory, name+".seg")
	if existing, err := os.ReadFile(target); err == nil {
		if !bytes.Equal(existing, data) {
			return "", fmt.Errorf("immutable compacted segment conflict")
		}
		return name, nil
	}
	file, err := os.CreateTemp(directory, ".compact-")
	if err != nil {
		return "", err
	}
	stage := file.Name()
	defer os.Remove(stage)
	if _, err = file.Write(data); err == nil {
		err = file.Sync()
	}
	if closeErr := file.Close(); err == nil {
		err = closeErr
	}
	if err != nil {
		return "", err
	}
	reader, err := Open(stage)
	if err != nil {
		return "", err
	}
	reader.Close()
	if err = os.Link(stage, target); err != nil {
		existing, readErr := os.ReadFile(target)
		if readErr != nil || !bytes.Equal(existing, data) {
			return "", err
		}
	}
	return name, nil
}
