package rpcapi

import (
	"context"
	"crypto/subtle"
	"fmt"
	"github.com/jackc/pgx/v5/pgxpool"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"
	pb "retrievec/engine/gen/retrieval/v1"
	"retrievec/engine/internal/scoring"
	"retrievec/engine/internal/search"
	"retrievec/engine/internal/snapshot"
	"sync"
	"time"
)

type Server struct {
	pb.UnimplementedRetrievalServer
	pool                                    *pgxpool.Pool
	root, principal, readToken, workerToken string
	mu                                      sync.Mutex
	readers                                 map[string]*snapshot.Reader
	slots                                   chan struct{}
}

func New(ctx context.Context, dsn, root, principal, readToken, workerToken string) (*Server, error) {
	if principal == "" || len(readToken) < 24 || len(workerToken) < 24 || readToken == workerToken {
		return nil, fmt.Errorf("distinct credentials of at least 24 characters and principal required")
	}
	pool, err := pgxpool.New(ctx, dsn)
	if err != nil {
		return nil, err
	}
	s := &Server{pool: pool, root: root, principal: principal, readToken: readToken, workerToken: workerToken, readers: map[string]*snapshot.Reader{}, slots: make(chan struct{}, 32)}
	if err = pool.Ping(ctx); err != nil {
		pool.Close()
		return nil, err
	}
	rows, err := pool.Query(ctx, "SELECT collection_id,active_snapshot FROM collections WHERE owner_id=$1 AND active_snapshot IS NOT NULL", principal)
	if err != nil {
		s.Close()
		return nil, err
	}
	defer rows.Close()
	for rows.Next() {
		var collection, id string
		if err = rows.Scan(&collection, &id); err != nil {
			rows.Close()
			s.Close()
			return nil, err
		}
		reader, e := snapshot.Open(root, id)
		if e != nil {
			rows.Close()
			s.Close()
			return nil, e
		}
		if reader.Manifest.CollectionID != collection {
			reader.Close()
			rows.Close()
			s.Close()
			return nil, fmt.Errorf("active collection mismatch")
		}
		s.readers[id] = reader
	}
	if err = rows.Err(); err != nil {
		s.Close()
		return nil, err
	}
	return s, nil
}
func (s *Server) Close() {
	s.mu.Lock()
	defer s.mu.Unlock()
	for _, r := range s.readers {
		r.Close()
	}
	s.pool.Close()
}
func equal(a, b string) bool { return subtle.ConstantTimeCompare([]byte(a), []byte(b)) == 1 }
func (s *Server) Interceptor(ctx context.Context, request any, info *grpc.UnaryServerInfo, handler grpc.UnaryHandler) (response any, err error) {
	defer func() {
		if recover() != nil {
			response = nil
			err = status.Error(codes.Internal, "unexpected service failure")
		}
	}()
	md, _ := metadata.FromIncomingContext(ctx)
	auth := md.Get("authorization")
	if len(auth) != 1 {
		return nil, status.Error(codes.Unauthenticated, "service credential required")
	}
	worker := equal(auth[0], "Bearer "+s.workerToken)
	if !worker && !equal(auth[0], "Bearer "+s.readToken) {
		return nil, status.Error(codes.Unauthenticated, "invalid service credential")
	}
	if info.FullMethod == pb.Retrieval_PrepareSnapshot_FullMethodName && !worker {
		return nil, status.Error(codes.PermissionDenied, "worker credential required")
	}
	select {
	case s.slots <- struct{}{}:
		defer func() { <-s.slots }()
	default:
		return nil, status.Error(codes.ResourceExhausted, "request capacity reached")
	}
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	response, err = handler(ctx, request)
	if ctx.Err() != nil {
		return nil, status.FromContextError(ctx.Err()).Err()
	}
	return response, err
}
func (s *Server) reader(ctx context.Context, collection, id string, prepare bool) (*snapshot.Reader, error) {
	if collection == "" || !snapshot.ValidID(id, "rs_") {
		return nil, status.Error(codes.InvalidArgument, "explicit collection and snapshot required")
	}
	var owner, state string
	err := s.pool.QueryRow(ctx, "SELECT c.owner_id,s.state FROM retrieval_snapshots s JOIN collections c USING(collection_id) WHERE s.snapshot_id=$1 AND s.collection_id=$2", id, collection).Scan(&owner, &state)
	if err != nil {
		return nil, status.Error(codes.NotFound, "registered snapshot unavailable")
	}
	if owner != s.principal {
		return nil, status.Error(codes.PermissionDenied, "collection scope denied")
	}
	if !prepare && state != "ready" {
		return nil, status.Error(codes.FailedPrecondition, "snapshot not ready")
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	if r := s.readers[id]; r != nil {
		return r, nil
	}
	r, err := snapshot.Open(s.root, id)
	if err != nil {
		return nil, status.Error(codes.FailedPrecondition, "snapshot artifact validation failed")
	}
	if r.Manifest.CollectionID != collection {
		r.Close()
		return nil, status.Error(codes.PermissionDenied, "manifest collection mismatch")
	}
	s.readers[id] = r
	return r, nil
}
func info(r *snapshot.Reader) *pb.SnapshotInfo {
	stats := r.Stats()
	return &pb.SnapshotInfo{SnapshotId: r.ID, CorpusSnapshotId: r.Manifest.CorpusID, CollectionId: r.Manifest.CollectionID, AnalyzerVersion: stats.AnalyzerVersion, ChunkCount: uint64(stats.ChunkCount), TermCount: uint64(stats.TermCount), TotalTokens: uint64(stats.TotalTokens), AverageLength: stats.AverageChunkLength, Capabilities: r.Manifest.Capabilities}
}
func (s *Server) GetSnapshotInfo(ctx context.Context, request *pb.SnapshotRequest) (*pb.SnapshotInfo, error) {
	r, err := s.reader(ctx, request.CollectionId, request.SnapshotId, false)
	if err != nil {
		return nil, err
	}
	return info(r), nil
}
func (s *Server) PrepareSnapshot(ctx context.Context, request *pb.SnapshotRequest) (*pb.SnapshotInfo, error) {
	r, err := s.reader(ctx, request.CollectionId, request.SnapshotId, true)
	if err != nil {
		return nil, err
	}
	return info(r), nil
}
func (s *Server) Search(ctx context.Context, request *pb.SearchRequest) (*pb.SearchResponse, error) {
	if request.CandidateLimit < 1 || request.CandidateLimit > 1000 || (request.Mode != pb.QueryMode_FREE_TEXT && request.Mode != pb.QueryMode_STRUCTURED) {
		return nil, status.Error(codes.InvalidArgument, "invalid mode or candidate limit")
	}
	r, err := s.reader(ctx, request.CollectionId, request.SnapshotId, false)
	if err != nil {
		return nil, err
	}
	mode := "free_text"
	if request.Mode == pb.QueryMode_STRUCTURED {
		mode = "structured"
	}
	start := time.Now()
	result, err := search.Execute(ctx, r, search.Request{Query: request.Query, Mode: mode, TopK: int(request.CandidateLimit), Explain: request.Explain}, scoring.Default())
	if err != nil {
		return nil, status.Error(codes.InvalidArgument, err.Error())
	}
	response := &pb.SearchResponse{SnapshotId: r.ID, CorpusSnapshotId: r.Manifest.CorpusID, AnalyzerVersion: r.Stats().AnalyzerVersion, Configuration: &pb.Configuration{ScoringVersion: scoring.Version, K1: 1.2, B: 0.75}, TotalMatches: uint64(result.TotalMatches), SearchMs: float64(time.Since(start).Nanoseconds()) / 1e6}
	for _, hit := range result.Hits {
		value := &pb.Hit{Rank: uint32(hit.Rank), ChunkId: hit.ChunkID, PaperId: hit.PaperID, PaperVersionId: hit.PaperVersionID, Score: hit.Score}
		for _, c := range hit.Contributions {
			value.Contributions = append(value.Contributions, &pb.Contribution{Term: c.Term, Score: c.Score, Tf: uint32(c.TF), Df: uint32(c.DF)})
		}
		response.Hits = append(response.Hits, value)
	}
	return response, nil
}
