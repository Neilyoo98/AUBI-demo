package main

import (
    "context"
    "errors"
    "fmt"
    "log"
    "net/http"
    "os"
    "os/signal"
    "syscall"
    "time"

    "github.com/Neilyoo98/AUBI-demo/auth"
    "github.com/Neilyoo98/AUBI-demo/config"
    "github.com/Neilyoo98/AUBI-demo/handlers"
    "github.com/Neilyoo98/AUBI-demo/middleware"
)

const (
    readHeaderTimeout = 5 * time.Second
    readTimeout       = 15 * time.Second
    writeTimeout      = 15 * time.Second
    idleTimeout       = 60 * time.Second
    shutdownTimeout   = 10 * time.Second
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
    server := &http.Server{
        Addr:              addr,
        Handler:           handler,
        ReadHeaderTimeout: readHeaderTimeout,
        ReadTimeout:       readTimeout,
        WriteTimeout:      writeTimeout,
        IdleTimeout:       idleTimeout,
    }

    signalCtx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
    defer stop()

    serverErr := make(chan error, 1)
    go func() {
        log.Printf("AUBI-demo server starting on %s", addr)
        if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
            serverErr <- err
            return
        }
        serverErr <- nil
    }()

    select {
    case err := <-serverErr:
        if err != nil {
            log.Fatal(err)
        }
    case <-signalCtx.Done():
        log.Printf("shutdown signal received")
        stop()

        shutdownCtx, cancel := context.WithTimeout(context.Background(), shutdownTimeout)
        defer cancel()

        if err := server.Shutdown(shutdownCtx); err != nil {
            log.Printf("graceful shutdown failed: %v", err)
            if closeErr := server.Close(); closeErr != nil {
                log.Printf("server close failed: %v", closeErr)
            }
        }

        if err := <-serverErr; err != nil {
            log.Fatal(err)
        }
        log.Printf("server stopped")
    }
}

func init() {
    if os.Getenv("PORT") == "" {
        os.Setenv("PORT", "8080")
    }
}
