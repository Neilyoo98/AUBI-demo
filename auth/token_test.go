package auth

import (
	"fmt"
	"runtime"
	"strings"
	"sync"
	"testing"
)

func TestTokenCache_GetOrRefresh_Basic(t *testing.T) {
	cache := NewTokenCache()

	token, err := cache.GetOrRefresh("alice")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if token == "" {
		t.Fatal("expected non-empty token")
	}

	// Second call must return the same cached value.
	token2, err := cache.GetOrRefresh("alice")
	if err != nil {
		t.Fatalf("unexpected error on cache hit: %v", err)
	}
	if token != token2 {
		t.Errorf("cache miss on second call: %q != %q", token, token2)
	}
}

func TestTokenCache_Invalidate(t *testing.T) {
	cache := NewTokenCache()

	tok1, _ := cache.GetOrRefresh("bob")
	cache.Invalidate("bob")
	tok2, err := cache.GetOrRefresh("bob")
	if err != nil {
		t.Fatalf("unexpected error after invalidation: %v", err)
	}
	if tok1 == tok2 {
		t.Error("expected fresh token after invalidation, got same value")
	}
}

// TestTokenCache_ConcurrentAccess hammers the cache with concurrent reads and
// writes across multiple goroutines. Without mutex protection the Go runtime
// detects the concurrent map access and raises a fatal "concurrent map read
// and map write" error, failing the test. After adding sync.RWMutex the test
// completes cleanly.
func TestTokenCache_ConcurrentAccess(t *testing.T) {
	runtime.GOMAXPROCS(runtime.NumCPU())

	cache := NewTokenCache()
	users := []string{"alice", "bob", "carol", "dave", "eve"}

	var wg sync.WaitGroup
	const goroutines = 300

	for i := 0; i < goroutines; i++ {
		wg.Add(1)
		go func(n int) {
			defer wg.Done()
			userID := users[n%len(users)]
			// Mix of reads and invalidations forces concurrent map read+write.
			if n%7 == 0 {
				cache.Invalidate(userID)
			} else {
				tok, err := cache.GetOrRefresh(userID)
				if err != nil {
					t.Errorf("GetOrRefresh(%s): %v", userID, err)
					return
				}
				if !strings.HasPrefix(tok, "tok_") {
					t.Errorf("malformed token for %s: %q", userID, tok)
				}
			}
		}(i)
	}

	wg.Wait()
}

func TestTokenCache_MultipleUsers(t *testing.T) {
	cache := NewTokenCache()

	tokens := make(map[string]string)
	for i := 0; i < 10; i++ {
		userID := fmt.Sprintf("user%d", i)
		tok, err := cache.GetOrRefresh(userID)
		if err != nil {
			t.Fatalf("GetOrRefresh(%s): %v", userID, err)
		}
		tokens[userID] = tok
	}

	// Verify cache hits return same tokens.
	for userID, expected := range tokens {
		got, err := cache.GetOrRefresh(userID)
		if err != nil {
			t.Fatalf("cache hit for %s: %v", userID, err)
		}
		if got != expected {
			t.Errorf("%s: cached %q, got %q", userID, expected, got)
		}
	}
}
