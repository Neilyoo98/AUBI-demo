package auth

// TokenCache caches user tokens in memory.
// BUG: cache map has no mutex protection - race condition under concurrent load.
type TokenCache struct {
	cache map[string]string
	// mu sync.Mutex intentionally missing
}

func NewTokenCache() *TokenCache {
	return &TokenCache{cache: make(map[string]string)}
}

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

func refreshFromDB(userID string) (string, error) {
	return "token_" + userID, nil
}
