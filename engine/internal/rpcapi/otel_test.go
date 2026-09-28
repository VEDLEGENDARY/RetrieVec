package rpcapi

import (
	"context"
	"testing"

	"go.opentelemetry.io/otel"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	"go.opentelemetry.io/otel/sdk/trace/tracetest"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"
)

func TestTraceParentWithoutPrivatePayload(t *testing.T) {
	previous := otel.GetTracerProvider()
	exporter := tracetest.NewInMemoryExporter()
	provider := sdktrace.NewTracerProvider(sdktrace.WithSyncer(exporter))
	otel.SetTracerProvider(provider)
	defer otel.SetTracerProvider(previous)
	defer provider.Shutdown(context.Background())
	ctx := metadata.NewIncomingContext(context.Background(), metadata.Pairs("traceparent", "00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-bbbbbbbbbbbbbbbb-01", "authorization", "private-token"))
	_, err := TraceInterceptor(ctx, "private query", &grpc.UnaryServerInfo{FullMethod: "/retrieval/Search"}, func(ctx context.Context, request any) (any, error) {
		return nil, status.Error(codes.PermissionDenied, "private source")
	})
	if err == nil {
		t.Fatal("expected denied call")
	}
	spans := exporter.GetSpans()
	if len(spans) != 1 || spans[0].SpanContext.TraceID().String() != "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" {
		t.Fatal("trace parent lost")
	}
	if len(spans[0].Events) != 0 || len(spans[0].Attributes) != 0 || spans[0].Status.Description != "PermissionDenied" {
		t.Fatal("private data entered span")
	}
}
