package main

import (
	"crypto/tls"
	"crypto/x509"
	"fmt"
	"net"
	"os"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"
)

// Remote listeners require mutual TLS in addition to the per-role bearer token.
func transportOptions(address, certPath, keyPath, caPath string) ([]grpc.ServerOption, error) {
	host, _, err := net.SplitHostPort(address)
	if err != nil {
		return nil, fmt.Errorf("invalid RPC listen address")
	}
	configured := certPath != "" || keyPath != "" || caPath != ""
	if !configured {
		ip := net.ParseIP(host)
		if ip == nil || !ip.IsLoopback() {
			return nil, fmt.Errorf("remote RPC requires mutual TLS")
		}
		return nil, nil
	}
	if certPath == "" || keyPath == "" || caPath == "" {
		return nil, fmt.Errorf("RPC certificate, key and client CA must all be configured")
	}
	cert, err := tls.LoadX509KeyPair(certPath, keyPath)
	if err != nil {
		return nil, fmt.Errorf("invalid RPC server certificate or key")
	}
	pem, err := os.ReadFile(caPath)
	if err != nil {
		return nil, fmt.Errorf("cannot read RPC client CA")
	}
	roots := x509.NewCertPool()
	if !roots.AppendCertsFromPEM(pem) {
		return nil, fmt.Errorf("invalid RPC client CA")
	}
	return []grpc.ServerOption{grpc.Creds(credentials.NewTLS(&tls.Config{
		MinVersion:   tls.VersionTLS13,
		Certificates: []tls.Certificate{cert},
		ClientCAs:    roots,
		ClientAuth:   tls.RequireAndVerifyClientCert,
	}))}, nil
}
