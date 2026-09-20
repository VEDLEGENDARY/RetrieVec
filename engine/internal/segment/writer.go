// Package segment implements the immutable RLSEG001 disk format.
package segment

import (
	"bytes"
	"crypto/sha256"
	"encoding/binary"
	"fmt"
	"retrievec/engine/internal/index"
)

const MaxFileBytes = 256 << 20
const MaxStringBytes = 1 << 20

func appendVar(b []byte, v uint64) []byte    { return binary.AppendUvarint(b, v) }
func appendString(b []byte, s string) []byte { return append(appendVar(b, uint64(len(s))), s...) }

// Encode writes deterministic compressed postings; publication validates with Open.
func Encode(idx *index.Index) ([]byte, error) {
	stats := idx.Stats()
	if stats.ChunkCount == 0 {
		return nil, fmt.Errorf("empty segment")
	}
	chunks := []byte{}
	for id := 0; id < stats.ChunkCount; id++ {
		doc, _ := idx.Document(id)
		length, _ := idx.ChunkLength(id)
		if len(doc.ChunkID) > MaxStringBytes {
			return nil, fmt.Errorf("chunk ID too large")
		}
		chunks = appendString(chunks, doc.ChunkID)
		chunks = appendVar(chunks, uint64(length))
	}
	terms := idx.Terms()
	lists := make([][]byte, len(terms))
	dictionarySize := 0
	for i, term := range terms {
		if len(term) > MaxStringBytes {
			return nil, fmt.Errorf("term too large")
		}
		lastID := 0
		for _, p := range idx.Postings(term) {
			lists[i] = appendVar(lists[i], uint64(p.InternalChunkID-lastID))
			lists[i] = appendVar(lists[i], uint64(p.TermFrequency))
			last := 0
			for _, position := range p.Positions {
				lists[i] = appendVar(lists[i], uint64(position-last))
				last = position
			}
			lastID = p.InternalChunkID
		}
		dictionarySize += len(appendVar(appendString(nil, term), uint64(idx.DocumentFrequency(term)))) + 16
	}
	dictionary := []byte{}
	offset := 96 + len(chunks) + dictionarySize
	for i, term := range terms {
		dictionary = appendString(dictionary, term)
		dictionary = appendVar(dictionary, uint64(idx.DocumentFrequency(term)))
		dictionary = binary.LittleEndian.AppendUint64(dictionary, uint64(offset))
		dictionary = binary.LittleEndian.AppendUint64(dictionary, uint64(len(lists[i])))
		offset += len(lists[i])
	}
	if offset+32 > MaxFileBytes {
		return nil, fmt.Errorf("segment exceeds size limit")
	}
	header := make([]byte, 96)
	copy(header, "RLSEG001")
	binary.LittleEndian.PutUint16(header[8:], 1)
	binary.LittleEndian.PutUint32(header[12:], 96)
	for at, value := range map[int]uint64{16: uint64(offset + 32), 24: uint64(stats.ChunkCount), 32: uint64(len(terms)), 40: 96, 48: uint64(96 + len(chunks)), 56: uint64(96 + len(chunks) + len(dictionary)), 64: uint64(offset), 72: uint64(stats.TotalTokens)} {
		binary.LittleEndian.PutUint64(header[at:], value)
	}
	data := bytes.Join(append([][]byte{header, chunks, dictionary}, lists...), nil)
	sum := sha256.Sum256(data)
	return append(data, sum[:]...), nil
}
