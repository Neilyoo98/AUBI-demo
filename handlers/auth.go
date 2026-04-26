package handlers

import (
	"encoding/json"
	"net/http"

	"github.com/Neilyoo98/AUBI-demo/auth"
)

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

		userID := r.URL.Query().Get("user_id")
		if userID == "" {
			http.Error(w, "missing user_id", http.StatusBadRequest)
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

		userID := r.URL.Query().Get("user_id")
		if userID == "" {
			http.Error(w, "missing user_id", http.StatusBadRequest)
			return
		}

		cache.Invalidate(userID)
		w.WriteHeader(http.StatusNoContent)
	}
}
