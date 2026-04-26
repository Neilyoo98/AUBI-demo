# AUBI Demo — Auth Service

A minimal Go authentication service used as the target repository for AUBI (Autonomous Understanding & Behaviour Inference) demos.

## Structure

```
auth/           Token cache — owns authentication token lifecycle
handlers/       HTTP handlers for /auth/token and /auth/invalidate
middleware/     Rate limiting
config/         Environment-based configuration
main.go         Server entrypoint
```

## Running

```bash
go run .
```

## Testing

```bash
go test ./...
```

## Known Issues

See [open issues](https://github.com/Neilyoo98/AUBI-demo/issues) for active bugs being tracked.
