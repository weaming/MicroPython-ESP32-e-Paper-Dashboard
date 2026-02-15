# mem-kv-http

A simple in-memory Key-Value store with HTTP interface.

## Usage

```bash
go run main.go --port 8080 --max-size 10
```

## Features

- [x] GET /path - Retrieve value (transparent Content-Type)
- [x] POST /path - Upload value (limit 10MB)
- [x] GET /path/ - List children in HTML
