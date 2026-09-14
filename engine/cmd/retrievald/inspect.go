package main

import (
    "encoding/json"
    "errors"
    "flag"
    "fmt"
    "io"

    "retrievallab/engine/internal/corpus"
    "retrievallab/engine/internal/index"
)

func inspectCommand(args []string, stdout, stderr io.Writer) int {
    flags := flag.NewFlagSet("inspect", flag.ContinueOnError)
    flags.SetOutput(stderr)
    path := flags.String("corpus", "", "validated snapshot directory")
    if err := flags.Parse(args); err != nil { if errors.Is(err, flag.ErrHelp) { return 0 }; return 2 }
    if *path == "" || flags.NArg() != 0 { fmt.Fprintln(stderr, "inspect: --corpus is required; no positional arguments"); return 2 }
    snapshot, err := corpus.Load(*path)
    if err != nil { fmt.Fprintln(stderr, "inspect:", err); return 2 }
    built, err := index.Build(snapshot.Documents)
    if err != nil { fmt.Fprintln(stderr, "inspect:", err); return 2 }
    if prepared, ok := snapshot.Manifest.Configuration["analyzer_version"]; ok && prepared != built.Stats().AnalyzerVersion {
        fmt.Fprintln(stderr, "inspect: preparation analyzer does not match index analyzer")
        return 2
    }
    response := map[string]any{"snapshot_id":snapshot.Manifest.SnapshotID,
        "collection_id":snapshot.Manifest.CollectionID, "statistics":built.Stats()}
    if err := json.NewEncoder(stdout).Encode(response); err != nil { fmt.Fprintln(stderr, "inspect:", err); return 1 }
    return 0
}
