package segment

import (
	"bytes"
	"crypto/sha256"
	"encoding/binary"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"retrievec/engine/internal/index"
	"sort"
	"unicode/utf8"
)

type entry struct {
	df             int
	offset, length int64
}
type Reader struct {
	file        *os.File
	IDs         []string
	Lengths     []int
	dictionary  map[string]entry
	terms       []string
	TotalTokens int
}
type cursor struct {
	data []byte
	at   int
	err  error
}

func (c *cursor) take(n int) []byte {
	if c.err != nil {
		return nil
	}
	if n < 0 || n > len(c.data)-c.at {
		c.err = fmt.Errorf("truncated segment block")
		return nil
	}
	v := c.data[c.at : c.at+n]
	c.at += n
	return v
}
func (c *cursor) number() uint64 {
	if c.err != nil {
		return 0
	}
	v, n := binary.Uvarint(c.data[c.at:])
	if n <= 0 || !bytes.Equal(appendVar(nil, v), c.data[c.at:c.at+n]) {
		c.err = fmt.Errorf("invalid or noncanonical varint")
		return 0
	}
	c.at += n
	return v
}
func (c *cursor) str() string {
	n := c.number()
	if n == 0 || n > MaxStringBytes {
		c.err = fmt.Errorf("invalid string length")
		return ""
	}
	v := c.take(int(n))
	if !utf8.Valid(v) {
		c.err = fmt.Errorf("invalid UTF-8")
	}
	return string(v)
}
func (c *cursor) fixed() uint64 {
	v := c.take(8)
	if len(v) != 8 {
		return 0
	}
	return binary.LittleEndian.Uint64(v)
}
func (c *cursor) done() error {
	if c.err != nil {
		return c.err
	}
	if c.at != len(c.data) {
		return fmt.Errorf("trailing block bytes")
	}
	return nil
}
func (r *Reader) read(offset, length int64) ([]byte, error) {
	if length < 0 || length > MaxFileBytes {
		return nil, fmt.Errorf("invalid block length")
	}
	b := make([]byte, int(length))
	_, err := r.file.ReadAt(b, offset)
	return b, err
}

func Open(path string) (result *Reader, err error) {
	info, err := os.Lstat(path)
	if err != nil {
		return nil, err
	}
	if !info.Mode().IsRegular() || info.Size() < 128 || info.Size() > MaxFileBytes {
		return nil, fmt.Errorf("invalid segment file")
	}
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer func() {
		if err != nil {
			f.Close()
		}
	}()
	r := &Reader{file: f, dictionary: map[string]entry{}}
	header, err := r.read(0, 96)
	if err != nil {
		return nil, err
	}
	u := func(at int) uint64 { return binary.LittleEndian.Uint64(header[at:]) }
	if string(header[:8]) != "RLSEG001" || binary.LittleEndian.Uint16(header[8:]) != 1 || binary.LittleEndian.Uint16(header[10:]) != 0 || binary.LittleEndian.Uint32(header[12:]) != 96 || u(16) != uint64(info.Size()) || u(40) != 96 || !bytes.Equal(header[80:], make([]byte, 16)) {
		return nil, fmt.Errorf("invalid segment header")
	}
	n, nt, total := u(24), u(32), u(72)
	dict, post, footer := u(48), u(56), u(64)
	if n == 0 || nt == 0 || n > 1000000 || nt > 1000000 || total < n || total > 32000000 || dict < 96 || post < dict || footer < post || footer != uint64(info.Size()-32) {
		return nil, fmt.Errorf("invalid bounds or counts")
	}
	h := sha256.New()
	if _, err = io.Copy(h, io.NewSectionReader(f, 0, int64(footer))); err != nil {
		return nil, err
	}
	checksum, err := r.read(int64(footer), 32)
	if err != nil {
		return nil, err
	}
	if !bytes.Equal(h.Sum(nil), checksum) {
		return nil, fmt.Errorf("segment checksum mismatch")
	}
	chunkData, err := r.read(96, int64(dict)-96)
	if err != nil {
		return nil, err
	}
	c := cursor{data: chunkData}
	sum := uint64(0)
	last := ""
	for range n {
		id := c.str()
		length := c.number()
		if c.err != nil || id <= last || length == 0 || length > total-sum {
			return nil, fmt.Errorf("invalid chunk table")
		}
		r.IDs = append(r.IDs, id)
		r.Lengths = append(r.Lengths, int(length))
		sum += length
		last = id
	}
	if err = c.done(); err != nil {
		return nil, err
	}
	if sum != total {
		return nil, fmt.Errorf("token totals differ")
	}
	r.TotalTokens = int(total)
	data, err := r.read(int64(dict), int64(post-dict))
	if err != nil {
		return nil, err
	}
	c = cursor{data: data}
	offset := post
	last = ""
	for range nt {
		term := c.str()
		df := c.number()
		start, length := c.fixed(), c.fixed()
		if c.err != nil || term <= last || df == 0 || df > n || start != offset || length == 0 || length > footer-offset {
			return nil, fmt.Errorf("invalid dictionary")
		}
		r.dictionary[term] = entry{int(df), int64(start), int64(length)}
		r.terms = append(r.terms, term)
		offset += length
		last = term
	}
	if err = c.done(); err != nil {
		return nil, err
	}
	if offset != footer {
		return nil, fmt.Errorf("postings boundary mismatch")
	}
	bases := make([]int, len(r.IDs))
	for i := 1; i < len(bases); i++ {
		bases[i] = bases[i-1] + r.Lengths[i-1]
	}
	seen := make([]byte, (int(total)+7)/8)
	count := 0
	for _, term := range r.terms {
		list, e := r.Postings(term)
		if e != nil {
			return nil, e
		}
		for _, p := range list {
			for _, position := range p.Positions {
				bit := bases[p.InternalChunkID] + position
				mask := byte(1 << uint(bit%8))
				if seen[bit/8]&mask != 0 {
					return nil, fmt.Errorf("position assigned to multiple terms")
				}
				seen[bit/8] |= mask
				count++
			}
		}
	}
	if count != int(total) {
		return nil, fmt.Errorf("postings token total mismatch")
	}
	return r, nil
}

func (r *Reader) Close() error                      { return r.file.Close() }
func (r *Reader) Terms() []string                   { return append([]string{}, r.terms...) }
func (r *Reader) DocumentFrequency(term string) int { return r.dictionary[term].df }
func (r *Reader) Postings(term string) ([]index.Posting, error) {
	e, ok := r.dictionary[term]
	if !ok {
		return []index.Posting{}, nil
	}
	data, err := r.read(e.offset, e.length)
	if err != nil {
		return nil, err
	}
	c := cursor{data: data}
	result := make([]index.Posting, 0, e.df)
	id := uint64(0)
	for i := 0; i < e.df; i++ {
		gap := c.number()
		if (i > 0 && gap == 0) || gap >= uint64(len(r.IDs)) || id+gap >= uint64(len(r.IDs)) {
			return nil, fmt.Errorf("invalid posting ID")
		}
		id += gap
		tf := c.number()
		if c.err != nil || tf == 0 || tf > uint64(r.Lengths[id]) || tf > uint64(len(data)-c.at) {
			return nil, fmt.Errorf("invalid term frequency")
		}
		positions := make([]int, 0, int(tf))
		position := uint64(0)
		for j := uint64(0); j < tf; j++ {
			gap = c.number()
			if c.err != nil || (j > 0 && gap == 0) || gap >= uint64(r.Lengths[id]) || position+gap >= uint64(r.Lengths[id]) {
				return nil, fmt.Errorf("invalid position")
			}
			position += gap
			positions = append(positions, int(position))
		}
		result = append(result, index.Posting{InternalChunkID: int(id), TermFrequency: int(tf), Positions: positions})
	}
	return result, c.done()
}

// Publish flushes, validates, and publishes a content-addressed immutable segment.
func Publish(directory string, idx *index.Index) (string, error) {
	data, err := Encode(idx)
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256(data)
	name := fmt.Sprintf("%x", sum)
	if err = os.MkdirAll(directory, 0700); err != nil {
		return "", err
	}
	target := filepath.Join(directory, name+".seg")
	if existing, err := os.ReadFile(target); err == nil {
		if !bytes.Equal(existing, data) {
			return "", fmt.Errorf("immutable segment conflict")
		}
		return name, nil
	}
	f, err := os.CreateTemp(directory, ".segment-")
	if err != nil {
		return "", err
	}
	stage := f.Name()
	defer os.Remove(stage)
	if _, err = f.Write(data); err == nil {
		err = f.Sync()
	}
	closeErr := f.Close()
	if err != nil {
		return "", err
	}
	if closeErr != nil {
		return "", closeErr
	}
	reader, err := Open(stage)
	if err != nil {
		return "", err
	}
	reader.Close()
	if err = os.Link(stage, target); err != nil {
		existing, e := os.ReadFile(target)
		if e != nil || !bytes.Equal(existing, data) {
			return "", err
		}
	}
	return name, nil
}

func (r *Reader) Lookup(id string) (int, bool) {
	at := sort.SearchStrings(r.IDs, id)
	return at, at < len(r.IDs) && r.IDs[at] == id
}
