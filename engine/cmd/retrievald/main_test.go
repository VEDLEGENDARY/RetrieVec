package main

import (
	"bytes"
	"strings"
	"testing"
)

func TestRun(t *testing.T) {
	tests := []struct {
		name       string
		args       []string
		wantCode   int
		wantOutput string
	}{
		{"version", []string{"--version"}, 0, "retrievald 0.1.0"},
		{"help", []string{"--help"}, 0, "Usage: retrievald"},
		{"missing corpus", nil, 2, "--corpus is required"},
		{"unknown flag", []string{"--unknown"}, 2, "flag provided but not defined"},
		{"positional argument", []string{"unexpected"}, 2, "unexpected positional arguments"},
		{"version with argument", []string{"--version", "unexpected"}, 2, "unexpected positional arguments"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var stdout, stderr bytes.Buffer
			if got := run(tt.args, &stdout, &stderr); got != tt.wantCode {
				t.Fatalf("exit code = %d, want %d; stderr: %s", got, tt.wantCode, &stderr)
			}
			if output := stdout.String() + stderr.String(); !strings.Contains(output, tt.wantOutput) {
				t.Fatalf("output = %q, want substring %q", output, tt.wantOutput)
			}
			if tt.wantCode != 0 && stdout.Len() != 0 {
				t.Fatalf("error wrote to stdout: %s", &stdout)
			}
		})
	}
}
