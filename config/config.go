package config

import "os"

type Config struct {
	Port      string
	RateLimit int
	DBUrl     string
}

func Load() *Config {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	return &Config{
		Port:      port,
		RateLimit: 100,
		DBUrl:     os.Getenv("DATABASE_URL"),
	}
}
