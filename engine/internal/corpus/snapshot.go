package corpus

import (
    "bytes"
    "crypto/sha256"
    "encoding/hex"
    "encoding/json"
    "fmt"
    "io"
    "os"
    "path/filepath"
    "reflect"
    "sort"
    "strconv"
    "strings"
    "unicode/utf8"
)

const maxFileBytes = 64 * 1024 * 1024

// Paper records the identity and provenance of an extracted source version.
type Paper struct {
    SchemaVersion int `json:"schema_version"`
    PaperID string `json:"paper_id"`
    PaperVersionID string `json:"paper_version_id"`
    Title string `json:"title"`
    Authors []string `json:"authors"`
    SourceURL *string `json:"source_url"`
    SourceSHA256 string `json:"source_sha256"`
    ExtractionVersion string `json:"extraction_version"`
    LicenseNote string `json:"license_note"`
}

// Chunk is the retrieval unit, retaining exact text and nullable page provenance.
type Chunk struct {
    SchemaVersion int `json:"schema_version"`
    ChunkID string `json:"chunk_id"`
    PaperID string `json:"paper_id"`
    PaperVersionID string `json:"paper_version_id"`
    CollectionID string `json:"collection_id"`
    Ordinal int `json:"ordinal"`
    Text string `json:"text"`
    TextSHA256 string `json:"text_sha256"`
    ChunkerVersion string `json:"chunker_version"`
    PageRange []int `json:"page_range"`
}

// Source is the manifest's concise provenance record.
type Source struct {
    PaperID string `json:"paper_id"`
    PaperVersionID string `json:"paper_version_id"`
    SourceURL *string `json:"source_url"`
    SourceSHA256 string `json:"source_sha256"`
    LicenseNote string `json:"license_note"`
}

// Manifest binds canonical records to their content and preparation configuration.
type Manifest struct {
    SchemaVersion int `json:"schema_version"`
    SnapshotID string `json:"snapshot_id"`
    CollectionID string `json:"collection_id"`
    Files map[string]string `json:"files"`
    Sources []Source `json:"sources"`
    ExtractionVersions []string `json:"extraction_versions"`
    ChunkerVersions []string `json:"chunker_versions"`
    Counts map[string]int `json:"counts"`
    Configuration map[string]any `json:"configuration"`
}

// Document adds the paper title needed by retrieval results.
type Document struct { Chunk; Title string `json:"title"` }

// Snapshot contains fully validated records, ready for index construction.
type Snapshot struct { Manifest Manifest; Papers []Paper; Documents []Document }

func hash(data []byte) string { sum := sha256.Sum256(data); return hex.EncodeToString(sum[:]) }

func identity(prefix string, value any) string {
    data, err := canonical(value)
    if err != nil { panic(err) } // Callers supply only contract-defined JSON values.
    return prefix + hash(data)
}

func text(s string) bool { return strings.TrimSpace(s) != "" && utf8.ValidString(s) }

func validHash(s string) bool {
    if len(s) != 64 { return false }
    _, err := hex.DecodeString(s)
    return err == nil && s == strings.ToLower(s)
}

func readFile(directory, name string) ([]byte, error) {
    path := filepath.Join(directory, name)
    info, err := os.Lstat(path)
    if err != nil { return nil, err }
    if !info.Mode().IsRegular() || info.Size() > maxFileBytes { return nil, fmt.Errorf("%s: linked, nonregular, or oversized file", name) }
    file, err := os.Open(path)
    if err != nil { return nil, err }
    defer file.Close()
    data, err := io.ReadAll(io.LimitReader(file, maxFileBytes+1))
    if err != nil { return nil, err }
    if len(data) > maxFileBytes || !utf8.Valid(data) { return nil, fmt.Errorf("%s: oversized or invalid UTF-8", name) }
    return data, nil
}

func decode(data []byte, value any) error {
    decoder := json.NewDecoder(bytes.NewReader(data))
    decoder.DisallowUnknownFields()
    decoder.UseNumber()
    if err := decoder.Decode(value); err != nil { return err }
    expected, err := canonical(value)
    if err != nil { return err }
    if !bytes.Equal(data, expected) { return fmt.Errorf("noncanonical, duplicate, missing, or trailing JSON fields") }
    return nil
}

func records[T any](data []byte) ([]T, error) {
    if len(data) == 0 || data[len(data)-1] != '\n' { return nil, fmt.Errorf("JSONL requires final newline and nonempty records") }
    var result []T
    for i, line := range bytes.Split(data[:len(data)-1], []byte{'\n'}) {
        var value T
        if err := decode(line, &value); err != nil { return nil, fmt.Errorf("record %d: %w", i+1, err) }
        result = append(result, value)
    }
    return result, nil
}

func sortedKeys(set map[string]bool) []string {
    values := make([]string, 0, len(set))
    for key := range set { values = append(values, key) }
    sort.Strings(values)
    return values
}

// Load validates file hashes, identities, provenance, record order, and references.
func Load(directory string) (*Snapshot, error) {
    raw, err := readFile(directory, "manifest.json")
    if err != nil { return nil, fmt.Errorf("load manifest: %w", err) }
    if len(raw) == 0 || raw[len(raw)-1] != '\n' { return nil, fmt.Errorf("manifest requires final newline") }
    var manifest Manifest
    if err := decode(raw[:len(raw)-1], &manifest); err != nil { return nil, fmt.Errorf("manifest: %w", err) }
    if manifest.SchemaVersion != 1 || !text(manifest.CollectionID) || manifest.Configuration == nil { return nil, fmt.Errorf("invalid manifest schema, collection, or configuration") }
    for key, value := range manifest.Configuration {
        if !text(key) { return nil, fmt.Errorf("empty configuration key") }
        switch value := value.(type) {
        case string: if !text(value) { return nil, fmt.Errorf("empty configuration value") }
        case bool:
        case json.Number: if _, err := strconv.ParseInt(string(value), 10, 32); err != nil { return nil, fmt.Errorf("configuration requires 32-bit integer: %w", err) }
        default: return nil, fmt.Errorf("invalid configuration value")
        }
    }
    var identityFields map[string]any
    decoder := json.NewDecoder(bytes.NewReader(raw)); decoder.UseNumber()
    if err := decoder.Decode(&identityFields); err != nil { return nil, err }
    delete(identityFields, "snapshot_id")
    if manifest.SnapshotID != identity("ss_", identityFields) { return nil, fmt.Errorf("snapshot identity mismatch") }
    paperData, err := readFile(directory, "papers.jsonl")
    if err != nil { return nil, err }
    chunkData, err := readFile(directory, "chunks.jsonl")
    if err != nil { return nil, err }
    if !reflect.DeepEqual(manifest.Files, map[string]string{"papers.jsonl":hash(paperData), "chunks.jsonl":hash(chunkData)}) { return nil, fmt.Errorf("file hash mismatch") }
    papers, err := records[Paper](paperData)
    if err != nil { return nil, fmt.Errorf("papers: %w", err) }
    chunks, err := records[Chunk](chunkData)
    if err != nil { return nil, fmt.Errorf("chunks: %w", err) }
    if !reflect.DeepEqual(manifest.Counts, map[string]int{"papers":len(papers), "chunks":len(chunks)}) { return nil, fmt.Errorf("record counts mismatch") }
    versions := make(map[string]Paper, len(papers))
    extractionVersions, chunkerVersions := map[string]bool{}, map[string]bool{}
    sources := make([]Source, 0, len(papers))
    lastID := ""
    for _, paper := range papers {
        if paper.SchemaVersion != 1 || !text(paper.PaperID) || !text(paper.Title) || !text(paper.ExtractionVersion) || !text(paper.LicenseNote) || paper.Authors == nil || !validHash(paper.SourceSHA256) { return nil, fmt.Errorf("invalid paper record") }
        for _, author := range paper.Authors { if !text(author) { return nil, fmt.Errorf("invalid author") } }
        if paper.SourceURL != nil && (!strings.HasPrefix(*paper.SourceURL, "https://") && !strings.HasPrefix(*paper.SourceURL,"http://")) { return nil, fmt.Errorf("invalid source URL") }
        if paper.PaperVersionID != identity("pv_", map[string]any{"paper_id":paper.PaperID, "source_sha256":paper.SourceSHA256}) { return nil, fmt.Errorf("paper identity mismatch") }
        if paper.PaperVersionID <= lastID { return nil, fmt.Errorf("duplicate or unsorted paper IDs") }
        lastID = paper.PaperVersionID
        versions[lastID] = paper
        extractionVersions[paper.ExtractionVersion] = true
        sources = append(sources, Source{paper.PaperID, paper.PaperVersionID, paper.SourceURL, paper.SourceSHA256, paper.LicenseNote})
    }
    ordinals := make(map[string][]int)
    documents := make([]Document, 0, len(chunks))
    lastID = ""
    for _, chunk := range chunks {
        paper, ok := versions[chunk.PaperVersionID]
        if !ok || paper.PaperID != chunk.PaperID { return nil, fmt.Errorf("missing or inconsistent paper reference") }
        if chunk.SchemaVersion != 1 || chunk.CollectionID != manifest.CollectionID || !text(chunk.Text) || !text(chunk.ChunkerVersion) || chunk.Ordinal < 0 || chunk.Ordinal > 2147483647 { return nil, fmt.Errorf("invalid chunk record") }
        if chunk.TextSHA256 != hash([]byte(chunk.Text)) { return nil, fmt.Errorf("text hash mismatch") }
        if chunk.ChunkID != identity("ch_", map[string]any{"paper_version_id":chunk.PaperVersionID, "extraction_version":paper.ExtractionVersion, "chunker_version":chunk.ChunkerVersion, "ordinal":chunk.Ordinal, "text_sha256":chunk.TextSHA256}) { return nil, fmt.Errorf("chunk identity mismatch") }
        if chunk.ChunkID <= lastID { return nil, fmt.Errorf("duplicate or unsorted chunk IDs") }
        lastID = chunk.ChunkID
        if chunk.PageRange != nil && (len(chunk.PageRange) != 2 || chunk.PageRange[0] < 1 || chunk.PageRange[1] < chunk.PageRange[0] || chunk.PageRange[1] > 2147483647) { return nil, fmt.Errorf("invalid page range") }
        ordinals[chunk.PaperVersionID] = append(ordinals[chunk.PaperVersionID], chunk.Ordinal)
        chunkerVersions[chunk.ChunkerVersion] = true
        documents = append(documents, Document{Chunk:chunk, Title:paper.Title})
    }
    for id := range versions {
        values := ordinals[id]
        if len(values) == 0 { return nil, fmt.Errorf("paper without chunks") }
        sort.Ints(values)
        for i, ordinal := range values { if ordinal != i { return nil, fmt.Errorf("chunk ordinals must be contiguous from zero") } }
    }
    if !reflect.DeepEqual(manifest.Sources, sources) || !reflect.DeepEqual(manifest.ExtractionVersions, sortedKeys(extractionVersions)) || !reflect.DeepEqual(manifest.ChunkerVersions, sortedKeys(chunkerVersions)) { return nil, fmt.Errorf("manifest provenance or versions mismatch") }
    return &Snapshot{Manifest:manifest, Papers:papers, Documents:documents}, nil
}
