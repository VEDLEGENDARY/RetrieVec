package rpcapi

import (
	"context"
	"encoding/json"
	"log"
	"os"
	"regexp"
	"time"

	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"
)

var traceLog = log.New(os.Stderr, "", 0)
var safeTraceID = regexp.MustCompile(`^[a-zA-Z0-9_.:-]{1,128}$`)

// traceRPC records identifiers and timings, never request bodies or error messages.
func traceRPC(ctx context.Context, request any, method string, started time.Time, err error) {
	record := map[string]any{
		"schema_version": 1, "time": time.Now().UTC().Format(time.RFC3339Nano),
		"event": "rpc.finished", "service": "retrieval", "operation": method,
		"error_code": status.Code(err).String(),
		"elapsed_ms": float64(time.Since(started).Microseconds()) / 1000,
	}
	md, _ := metadata.FromIncomingContext(ctx)
	for header, field := range map[string]string{
		"x-request-id": "request_id", "x-retrievec-job-id": "job_id", "x-retrievec-run-id": "run_id",
	} {
		values := md.Get(header)
		if len(values) == 1 && safeTraceID.MatchString(values[0]) {
			record[field] = values[0]
		}
	}
	if scope, ok := request.(interface {
		GetCollectionId() string
		GetSnapshotId() string
	}); ok {
		for field, value := range map[string]string{
			"collection_id": scope.GetCollectionId(), "snapshot_id": scope.GetSnapshotId(),
		} {
			if safeTraceID.MatchString(value) {
				record[field] = value
			}
		}
	}
	if raw, marshalErr := json.Marshal(record); marshalErr == nil {
		traceLog.Print(string(raw))
	}
}
