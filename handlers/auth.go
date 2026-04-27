package handlers

import (
	"encoding/json"
	"fmt"
	"net/http"
	"regexp"
	"strings"

	"github.com/Neilyoo98/AUBI-demo/auth"
)

var validUserID = regexp.MustCompile(`^[a-zA-Z0-9_\-]+$`)

const maxUserIDLen = 128

func validateUserID(raw string) (string, error) {
	id := strings.TrimSpace(raw)
	if id == "" {
		return "", fmt.Errorf("missing user_id")
	}
	if len(id) > maxUserIDLen {
		return "", fmt.Errorf("user_id too long")
	}
	if !validUserID.MatchString(id) {
		return "", fmt.Errorf("invalid user_id")
	}
	return id, nil
}

type tokenResponse struct {
	UserID string `json:"user_id"`
	Token  string `json:"token"`
}

func TokenHandler(cache *auth.TokenCache) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}

		userID, verr := validateUserID(r.URL.Query().Get("user_id"))
		if verr != nil {
			http.Error(w, verr.Error(), http.StatusBadRequest)
			return
		}

		token, err := cache.GetOrRefresh(userID)
		if err != nil {
			http.Error(w, "internal error", http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(tokenResponse{UserID: userID, Token: token})
	}
}

func InvalidateHandler(cache *auth.TokenCache) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}

		userID, verr := validateUserID(r.URL.Query().Get("user_id"))
		if verr != nil {
			http.Error(w, verr.Error(), http.StatusBadRequest)
			return
		}

		cache.Invalidate(userID)
		w.WriteHeader(http.StatusNoContent)
	}
}
