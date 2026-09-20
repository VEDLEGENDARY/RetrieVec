package main

import (
	"context"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"os/signal"
	"retrievec/engine/internal/corpus"
	"retrievec/engine/internal/httpapi"
	"syscall"
	"time"
)

func serve(directory, address string, stdout, stderr io.Writer) int {
	host, _, err := net.SplitHostPort(address)
	if err != nil || net.ParseIP(host) == nil || !net.ParseIP(host).IsLoopback() {
		fmt.Fprintln(stderr, "listen address must be a numeric loopback IP and port")
		return 2
	}
	snapshot, err := corpus.Load(directory)
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 1
	}
	handler, err := httpapi.New(snapshot)
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 1
	}
	listener, err := net.Listen("tcp", address)
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 1
	}
	server := &http.Server{Handler: handler, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 10 * time.Second, WriteTimeout: 10 * time.Second, IdleTimeout: 30 * time.Second, MaxHeaderBytes: 16 * 1024}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	done := make(chan struct{})
	go func() {
		defer close(done)
		<-ctx.Done()
		shutdown, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		if server.Shutdown(shutdown) != nil {
			_ = server.Close()
		}
	}()
	fmt.Fprintf(stdout, "listening http://%s\n", listener.Addr())
	err = server.Serve(listener)
	stop()
	<-done
	if err != nil && err != http.ErrServerClosed {
		fmt.Fprintln(stderr, err)
		return 1
	}
	return 0
}
