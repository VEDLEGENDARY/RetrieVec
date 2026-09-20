package main

import (
	"context"
	"flag"
	"fmt"
	"google.golang.org/grpc"
	"io"
	"net"
	"os"
	"os/signal"
	pb "retrievallab/engine/gen/retrieval/v1"
	"retrievallab/engine/internal/rpcapi"
	"syscall"
	"time"
)

func rpcCommand(args []string, stdout, stderr io.Writer) int {
	flags := flag.NewFlagSet("rpc", flag.ContinueOnError)
	flags.SetOutput(stderr)
	root := flags.String("store", "", "artifact store")
	address := flags.String("listen", "127.0.0.1:8092", "local RPC address")
	if flags.Parse(args) != nil || flags.NArg() != 0 || *root == "" {
		return 2
	}
	host, _, err := net.SplitHostPort(*address)
	if err != nil || net.ParseIP(host) == nil || !net.ParseIP(host).IsLoopback() {
		fmt.Fprintln(stderr, "RPC requires numeric loopback address")
		return 2
	}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	service, err := rpcapi.New(ctx, os.Getenv("RETRIEVALLAB_DSN"), *root, os.Getenv("RETRIEVALLAB_PRINCIPAL"), os.Getenv("RETRIEVALLAB_READ_TOKEN"), os.Getenv("RETRIEVALLAB_WORKER_TOKEN"))
	if err != nil {
		fmt.Fprintln(stderr, "RPC registry or artifact startup failed")
		return 1
	}
	defer service.Close()
	server := grpc.NewServer(grpc.UnaryInterceptor(service.Interceptor), grpc.MaxRecvMsgSize(4<<20), grpc.MaxSendMsgSize(4<<20), grpc.MaxConcurrentStreams(32))
	pb.RegisterRetrievalServer(server, service)
	listener, err := net.Listen("tcp", *address)
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 1
	}
	done := make(chan struct{})
	go func() {
		defer close(done)
		<-ctx.Done()
		timer := time.AfterFunc(10*time.Second, server.Stop)
		server.GracefulStop()
		timer.Stop()
	}()
	fmt.Fprintf(stdout, "listening grpc://%s\n", listener.Addr())
	err = server.Serve(listener)
	stop()
	<-done
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 1
	}
	return 0
}
