package rpcapi

import (
	"context"
	"fmt"
	"net/url"
	"os"
	"strconv"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	otelcodes "go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	"go.opentelemetry.io/otel/trace"
	"google.golang.org/grpc"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"
)

func ConfigureTracing(ctx context.Context) (func(context.Context) error, error) {
	if os.Getenv("RETRIEVEC_OTEL") != "1" {
		return func(context.Context) error { return nil }, nil
	}
	endpoint := os.Getenv("RETRIEVEC_OTEL_ENDPOINT")
	if endpoint == "" {
		endpoint = "http://127.0.0.1:4318/v1/traces"
	}
	parsed, err := url.Parse(endpoint)
	if err != nil || parsed.Hostname() == "" || (parsed.Scheme != "http" && parsed.Scheme != "https") || parsed.User != nil || parsed.RawQuery != "" || parsed.Fragment != "" {
		return nil, fmt.Errorf("invalid trace collector endpoint")
	}
	ratio := 0.1
	if value := os.Getenv("RETRIEVEC_OTEL_SAMPLE_RATIO"); value != "" {
		ratio, err = strconv.ParseFloat(value, 64)
		if err != nil || !(ratio >= 0 && ratio <= 1) {
			return nil, fmt.Errorf("invalid trace sampling ratio")
		}
	}
	exporter, err := otlptracehttp.New(ctx, otlptracehttp.WithEndpointURL(endpoint), otlptracehttp.WithTimeout(2*time.Second))
	if err != nil {
		return nil, fmt.Errorf("trace exporter initialization failed")
	}
	provider := sdktrace.NewTracerProvider(
		sdktrace.WithResource(resource.NewSchemaless(attribute.String("service.name", "retrievec.retrieval"))),
		sdktrace.WithSampler(sdktrace.ParentBased(sdktrace.TraceIDRatioBased(ratio))),
		sdktrace.WithBatcher(exporter, sdktrace.WithMaxQueueSize(2048), sdktrace.WithMaxExportBatchSize(256)),
	)
	otel.SetTracerProvider(provider)
	return provider.Shutdown, nil
}

// Only W3C traceparent crosses the boundary; baggage, credentials and payloads do not.
func TraceInterceptor(ctx context.Context, request any, info *grpc.UnaryServerInfo, handler grpc.UnaryHandler) (any, error) {
	md, _ := metadata.FromIncomingContext(ctx)
	carrier := propagation.MapCarrier{}
	if values := md.Get("traceparent"); len(values) == 1 {
		carrier["traceparent"] = values[0]
	}
	ctx = propagation.TraceContext{}.Extract(ctx, carrier)
	ctx, span := otel.Tracer("retrievec/retrieval").Start(ctx, info.FullMethod, trace.WithSpanKind(trace.SpanKindServer))
	defer span.End()
	response, err := handler(ctx, request)
	if err != nil {
		span.SetStatus(otelcodes.Error, status.Code(err).String())
	}
	return response, err
}
