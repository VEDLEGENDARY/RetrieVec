package httpapi

import (
	"io"
	"net/http"
	"net/http/httptest"
	"retrievallab/engine/internal/corpus"
	"strings"
	"sync"
	"testing"
)

func TestLiveHTTPContracts(t *testing.T) {
	snapshot, err := corpus.Load("../../../datasets/fixtures/snapshots/ss_4415a7c573a87a239ee65b0581664ea667b3988e4be43cb7f3bd069380ee0811")
	if err != nil {
		t.Fatal(err)
	}
	api, err := New(snapshot)
	if err != nil {
		t.Fatal(err)
	}
	server := httptest.NewServer(api)
	defer server.Close()
	cases := []struct {
		method, path, body string
		status             int
	}{
		{"GET", "/healthz", "", 200}, {"GET", "/readyz", "", 200}, {"GET", "/v1/stats", "", 200}, {"GET", "/v1/search", "", 405},
		{"POST", "/v1/search", `{"query":"retrieval","mode":"free_text","top_k":10,"explain":true}`, 200},
		{"POST", "/v1/search", `{"query":"red AND","mode":"structured","top_k":10}`, 400},
		{"POST", "/v1/search", `{"query":"red","query":"blue","mode":"free_text","top_k":10}`, 400},
		{"POST", "/v1/search", `{"query":"red","mode":"free_text","top_k":0}`, 400},
		{"POST", "/v1/search", `{"query":null,"mode":"free_text","top_k":10}`, 400},
		{"POST", "/v1/search", strings.Repeat(" ", MaxBodyBytes+1), 413},
	}
	for _, c := range cases {
		request, _ := http.NewRequest(c.method, server.URL+c.path, strings.NewReader(c.body))
		response, err := server.Client().Do(request)
		if err != nil {
			t.Fatal(err)
		}
		_, _ = io.Copy(io.Discard, response.Body)
		response.Body.Close()
		if response.StatusCode != c.status {
			t.Errorf("%s %s got %d want %d", c.method, c.path, response.StatusCode, c.status)
		}
	}
	var wg sync.WaitGroup
	for range 8 {
		wg.Add(1)
		go func() {
			defer wg.Done()
			r, err := server.Client().Post(server.URL+"/v1/search", "application/json", strings.NewReader(`{"query":"retrieval","mode":"free_text","top_k":3}`))
			if err != nil {
				t.Error(err)
				return
			}
			defer r.Body.Close()
			if r.StatusCode != 200 {
				t.Error(r.StatusCode)
			}
		}()
	}
	wg.Wait()
	unavailable := httptest.NewRecorder()
	(&API{}).ServeHTTP(unavailable, httptest.NewRequest("GET", "/readyz", nil))
	if unavailable.Code != 503 {
		t.Fatal("readiness")
	}
}
