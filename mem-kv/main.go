package main

import (
	"flag"
	"fmt"
	"html/template"
	"io"
	"log"
	"net/http"
	"sort"
	"strings"
	"sync"
)

// Item 存储 KV 值及其 Content-Type
type Item struct {
	Content     []byte
	ContentType string
}

var (
	store = make(map[string]Item)
	mu    sync.RWMutex
)

var (
	addr       = flag.String("listen", ":8080", "Server listen address")
	maxSizeMiB = flag.Int("max-size", 10, "Max upload size in MiB")
)

func main() {
	flag.Parse()

	http.HandleFunc("/", handler)

	log.Printf("Starting mem-kv-http server on %s (Max upload size: %d MiB)", *addr, *maxSizeMiB)
	if err := http.ListenAndServe(*addr, nil); err != nil {
		log.Fatal(err)
	}
}

func handler(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/")
	log.Printf("%s /%s (%s)", r.Method, path, r.RemoteAddr)

	switch r.Method {
	case http.MethodGet:
		handleGet(w, r, path)
	case http.MethodPost:
		handlePost(w, r, path)
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

func handlePost(w http.ResponseWriter, r *http.Request, path string) {
	if path == "" || strings.HasSuffix(path, "/") || path == "help" {
		http.Error(w, "Invalid path for POST", http.StatusBadRequest)
		return
	}

	// 限制上传大小
	maxSize := int64(*maxSizeMiB) << 20
	r.Body = http.MaxBytesReader(w, r.Body, maxSize)

	content, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "Request body too large or error reading body", http.StatusRequestEntityTooLarge)
		return
	}

	contentType := r.Header.Get("Content-Type")
	userAgent := r.Header.Get("User-Agent")
	// If Content-Type is empty, or if it's curl's default and it's a curl request, default to text/plain
	if contentType == "" || (strings.HasPrefix(userAgent, "curl/") && contentType == "application/x-www-form-urlencoded") {
		contentType = "text/plain"
	}

	mu.Lock()
	store[path] = Item{
		Content:     content,
		ContentType: contentType,
	}
	mu.Unlock()

	w.WriteHeader(http.StatusCreated)
	fmt.Fprintf(w, "Stored %d bytes at %s\n", len(content), path)
}

func handleGet(w http.ResponseWriter, r *http.Request, path string) {
	if path == "help" {
		handleHelp(w)
		return
	}
	if strings.HasSuffix(path, "/") || path == "" {
		handleList(w, r, path)
		return
	}

	mu.RLock()
	item, ok := store[path]
	mu.RUnlock()

	if !ok {
		// 尝试检查是否是目录（即是否存在以该路径为前缀的 key）
		mu.RLock()
		isDir := false
		prefix := path + "/"
		for k := range store {
			if strings.HasPrefix(k, prefix) {
				isDir = true
				break
			}
		}
		mu.RUnlock()

		if isDir {
			// 如果是目录但没有以 / 结尾，则重定向
			http.Redirect(w, r, "/"+path+"/", http.StatusMovedPermanently)
			return
		}

		http.NotFound(w, r)
		return
	}

	w.Header().Set("Content-Type", item.ContentType)
	w.Write(item.Content)
}

type listEntry struct {
	Name  string
	IsDir bool
}

func handleList(w http.ResponseWriter, r *http.Request, path string) {
	mu.RLock()
	defer mu.RUnlock()

	type entryState struct {
		IsFile bool
		IsDir  bool
	}
	entriesState := make(map[string]entryState)
	prefix := path

	for k := range store {
		if strings.HasPrefix(k, prefix) {
			rel := strings.TrimPrefix(k, prefix)
			if rel == "" {
				continue
			}

			parts := strings.Split(rel, "/")
			name := parts[0]
			state := entriesState[name]
			if len(parts) > 1 {
				state.IsDir = true
			} else {
				state.IsFile = true
			}
			entriesState[name] = state
		}
	}

	var entries []listEntry
	for name, state := range entriesState {
		if state.IsFile {
			entries = append(entries, listEntry{Name: name, IsDir: false})
		}
		if state.IsDir {
			entries = append(entries, listEntry{Name: name, IsDir: true})
		}
	}

	sort.Slice(entries, func(i, j int) bool {
		if entries[i].IsDir != entries[j].IsDir {
			return entries[i].IsDir
		}
		return entries[i].Name < entries[j].Name
	})

	renderList(w, path, entries)
}

var listTemplate = template.Must(template.New("list").Parse(`
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Listing for /{{.Path}}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif; padding: 40px; color: #111; max-width: 800px; margin: 0 auto; line-height: 1.6; }
        h1 { font-size: 1.2rem; font-weight: 600; margin-bottom: 2rem; }
        ul { list-style: none; padding: 0; }
        li { border-bottom: 1px solid #eee; padding: 8px 0; }
        li:last-child { border-bottom: none; }
        a { text-decoration: none; color: #0066cc; }
        a:hover { text-decoration: underline; }
        .dir { font-weight: 600; }
        .dir::after { content: "/"; color: #999; }
    </style>
</head>
<body>
    <h1>Listing for /{{.Path}}</h1>
    <hr>
    <ul>
        {{if .Path}}
        <li><a href="../">.. (Parent Directory)</a></li>
        {{end}}
        {{range .Entries}}
        <li><a href="{{.Name}}{{if .IsDir}}/{{end}}" {{if .IsDir}}class="dir"{{end}}>{{.Name}}</a></li>
        {{end}}
    </ul>
</body>
</html>
`))

func renderList(w http.ResponseWriter, path string, entries []listEntry) {
	data := struct {
		Path    string
		Entries []listEntry
	}{
		Path:    path,
		Entries: entries,
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := listTemplate.Execute(w, data); err != nil {
		log.Printf("Template execution error: %v", err)
	}
}

func handleHelp(w http.ResponseWriter) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprintf(w, `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Help - mem-kv-http</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif; padding: 40px; color: #111; max-width: 800px; margin: 0 auto; line-height: 1.6; }
        h1 { font-size: 1.2rem; font-weight: 600; margin-bottom: 2rem; }
        pre { background: #f8f8f8; padding: 15px; border-radius: 4px; overflow-x: auto; font-size: 0.9rem; border: 1px solid #eee; }
        code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
        .section { margin-bottom: 2rem; }
    </style>
</head>
<body>
    <h1>Usage Guide</h1>
    <div class="section">
        <p>This is a simple in-memory Key-Value store with an HTTP interface.</p>
    </div>
    <div class="section">
        <strong>Upload Content (POST)</strong>
        <pre><code># Upload text (detected as text/plain)
curl -d "hello world" http://localhost:8080/my/path

# Upload with specific Content-Type
curl -X POST -H "Content-Type: application/json" -d '{"key":"value"}' http://localhost:8080/api/data</code></pre>
    </div>
    <div class="section">
        <strong>Retrieve Content (GET)</strong>
        <pre><code># Get raw content
curl http://localhost:8080/my/path

# List directory (path ends with /)
curl http://localhost:8080/my/</code></pre>
    </div>
    <div class="section">
        <strong>Notes</strong>
        <ul>
            <li>Max upload size: %d MiB (configurable).</li>
            <li>Paths ending in / or "help" cannot be used for POST.</li>
            <li>Directory listing provides a minimalist navigation UI.</li>
        </ul>
    </div>
</body>
</html>
`, *maxSizeMiB)
}
