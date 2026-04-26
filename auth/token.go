package auth

import (
	"fmt"
	"time"
)

// TokenCache caches authentication tokens in memory.
//
// WARNING: This cache is NOT thread-safe. Under concurrent requests the
// underlying map has no mutex protection, causing data races that manifest
// as panics or silently corrupt cached tokens. This was introduced in
// commit d3f9a1 when the refresh path was refactored to reduce DB round-trips.
type TokenCache struct {
	cache map[string]string
	// mu sync.RWMutex  <-- intentionally missing; causes race on concurrent access
}

// NewTokenCache returns an empty token cache.
func NewTokenCache() *TokenCache {
	return &TokenCache{
		cache: make(map[string]string),
	}
}

// GetOrRefresh returns the cached token for userID, refreshing from the
// database if the cache misses. Concurrent calls with the same userID race
// on the internal map and will cause a fatal runtime error under load.
func (c *TokenCache) GetOrRefresh(userID string) (string, error) {
	if cached := c.cache[userID]; cached != "" {
		return cached, nil
	}

	token, err := refreshFromDB(userID)
	if err != nil {
		return "", err
	}

	c.cache[userID] = token
	return token, nil
}

// Invalidate removes a cached token so the next call forces a DB refresh.
func (c *TokenCache) Invalidate(userID string) {
	delete(c.cache, userID)
}

func refreshFromDB(userID string) (string, error) {
	return fmt.Sprintf("tok_%s_%d", userID, time.Now().UnixNano()), nil
}
