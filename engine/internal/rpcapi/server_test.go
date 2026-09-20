package rpcapi

import (
	"context"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"
	pb "retrievec/engine/gen/retrieval/v1"
	"testing"
)

func TestCredentialsControlAndOverload(t *testing.T) {
	server := &Server{readToken: "read", workerToken: "worker", slots: make(chan struct{}, 1)}
	handler := func(ctx context.Context, request any) (any, error) { return "ok", nil }
	info := &grpc.UnaryServerInfo{FullMethod: pb.Retrieval_Search_FullMethodName}
	if _, err := server.Interceptor(context.Background(), nil, info, handler); status.Code(err) != codes.Unauthenticated {
		t.Fatal(err)
	}
	ctx := metadata.NewIncomingContext(context.Background(), metadata.Pairs("authorization", "Bearer read"))
	if _, err := server.Interceptor(ctx, nil, info, handler); err != nil {
		t.Fatal(err)
	}
	control := &grpc.UnaryServerInfo{FullMethod: pb.Retrieval_PrepareSnapshot_FullMethodName}
	if _, err := server.Interceptor(ctx, nil, control, handler); status.Code(err) != codes.PermissionDenied {
		t.Fatal(err)
	}
	server.slots <- struct{}{}
	if _, err := server.Interceptor(ctx, nil, info, handler); status.Code(err) != codes.ResourceExhausted {
		t.Fatal(err)
	}
}
