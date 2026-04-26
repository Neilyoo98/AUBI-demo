package auth

import (
	"fmt"
	"sync"
	"time"
)

// TokenCache caches authentication tokens in memory.
//
// TokenCache is safe for concurrent use by multiple goroutines.
type TokenCache struct {
	cache map[string]string
	mu    sync.RWMutex
}

// NewTokenCache returns an empty token cache.
func NewTokenCache() *TokenCache {
	return &TokenCache{
		cache: make(map[string]string),
	}
}

// GetOrRefresh returns the cached token for userID, refreshing from the
// database if the cache misses.
func (c *TokenCache) GetOrRefresh(userID string) (string, error) {
	c.mu.RLock()
	cached := c.cache[userID]
	c.mu.RUnlock()
	if cached != "" {
		return cached, nil
	}

	token, err := refreshFromDB(userID)
	if err != nil {
		return "", err
	}

	c.mu.Lock()
	if cached := c.cache[userID]; cached != "" {
		c.mu.Unlock()
		return cached, nil
	}
	c.cache[userID] = token
	c.mu.Unlock()

	return token, nil
}

// Invalidate removes a cached token so the next call forces a DB refresh.
func (c *TokenCache) Invalidate(userID string) {
	c.mu.Lock()
	delete(c.cache, userID)
	c.mu.Unlock()
}

func refreshFromDB(userID string) (string, error) {
	return fmt.Sprintf("tok_%s_%d", userID, time.Now().UnixNano()), nil
}
