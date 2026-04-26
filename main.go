package main

import (
	"fmt"
	"log"
	"net/http"
	"os"

	"github.com/Neilyoo98/AUBI-demo/auth"
	"github.com/Neilyoo98/AUBI-demo/config"
	"github.com/Neilyoo98/AUBI-demo/handlers"
	"github.com/Neilyoo98/AUBI-demo/middleware"
)

func main() {
	cfg := config.Load()
	cache := auth.NewTokenCache()

	mux := http.NewServeMux()
	mux.HandleFunc("/health", handlers.Health)
	mux.HandleFunc("/auth/token", handlers.TokenHandler(cache))
	mux.HandleFunc("/auth/invalidate", handlers.InvalidateHandler(cache))

	handler := middleware.RateLimit(mux, cfg.RateLimit)

	addr := fmt.Sprintf(":%s", cfg.Port)
	log.Printf("AUBI-demo server starting on %s", addr)
	if err := http.ListenAndServe(addr, handler); err != nil {
		log.Fatal(err)
	}
}

func init() {
	if os.Getenv("PORT") == "" {
		os.Setenv("PORT", "8080")
	}
}
