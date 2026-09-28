package main

import "testing"

func TestRemoteTransportRequiresCompleteTLS(t *testing.T) {
	for _, address := range []string{"0.0.0.0:8092", "retrieval:8092", "192.168.1.2:8092", "[::]:8092", "invalid"} {
		if _, err := transportOptions(address, "", "", ""); err == nil {
			t.Fatalf("accepted plaintext %s", address)
		}
	}
	for _, address := range []string{"127.0.0.1:8092", "[::1]:8092"} {
		if _, err := transportOptions(address, "", "", ""); err != nil {
			t.Fatal(err)
		}
		if _, err := transportOptions(address, "missing-cert", "", ""); err == nil {
			t.Fatal("partial TLS fell back to plaintext")
		}
	}
}
