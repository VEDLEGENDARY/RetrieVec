package rpcapi

import (
	"bytes"
	"context"
	"encoding/json"
	"log"
	"strings"
	"testing"
	"time"

	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"
	pb "retrievec/engine/gen/retrieval/v1"
)

func TestTraceOmitsCredentialsAndErrorPayload(t *testing.T) {
	var buffer bytes.Buffer
	previous := traceLog
	traceLog = log.New(&buffer, "", 0)
	t.Cleanup(func() { traceLog = previous })
	ctx := metadata.NewIncomingContext(context.Background(), metadata.Pairs(
		"x-request-id", strings.Repeat("a", 32),
		"authorization", "private-token",
		"x-retrievec-job-id", "bad\nidentifier",
	))
	traceRPC(ctx, &pb.SearchRequest{}, "/retrieval.Search", time.Now(),
		status.Error(codes.Unavailable, "private-passage"))
	var record map[string]any
	if err := json.Unmarshal(buffer.Bytes(), &record); err != nil {
		t.Fatal(err)
	}
	if record["request_id"] != strings.Repeat("a", 32) || record["error_code"] != "Unavailable" {
		t.Fatalf("unexpected safe fields: %v", record)
	}
	for _, secret := range []string{"private-token", "private-passage", "bad", "authorization"} {
		if strings.Contains(buffer.String(), secret) {
			t.Fatalf("sensitive field in trace: %q", secret)
		}
	}
}
