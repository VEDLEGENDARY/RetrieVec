package rpcapi

import (
	"context"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	health "google.golang.org/grpc/health/grpc_health_v1"
	"google.golang.org/grpc/status"
)

type healthService struct {
	health.UnimplementedHealthServer
	retrieval *Server
}

// Checks share the role-token interceptor; no anonymous metadata endpoint is exposed.
func RegisterHealth(server *grpc.Server, retrieval *Server) {
	health.RegisterHealthServer(server, &healthService{retrieval: retrieval})
}

func (h *healthService) Check(ctx context.Context, request *health.HealthCheckRequest) (*health.HealthCheckResponse, error) {
	switch request.Service {
	case "live":
		return &health.HealthCheckResponse{Status: health.HealthCheckResponse_SERVING}, nil
	case "ready":
		state := health.HealthCheckResponse_SERVING
		if err := h.retrieval.pool.Ping(ctx); err != nil {
			state = health.HealthCheckResponse_NOT_SERVING
		}
		return &health.HealthCheckResponse{Status: state}, nil
	default:
		return nil, status.Error(codes.NotFound, "unknown health service")
	}
}
