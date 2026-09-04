package queue

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
)

type Item struct {
	Method string          `json:"method"`
	Path   string          `json:"path"`
	Body   json.RawMessage `json:"body"`
}

type FileQueue struct {
	path string
	mu   sync.Mutex
}

func New(dir string) *FileQueue {
	_ = os.MkdirAll(dir, 0o700)
	return &FileQueue{path: filepath.Join(dir, "pending.jsonl")}
}

func (q *FileQueue) Push(item Item) error {
	q.mu.Lock()
	defer q.mu.Unlock()
	f, err := os.OpenFile(q.path, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o600)
	if err != nil {
		return err
	}
	defer f.Close()
	enc := json.NewEncoder(f)
	return enc.Encode(item)
}

func (q *FileQueue) Drain() ([]Item, error) {
	q.mu.Lock()
	defer q.mu.Unlock()
	data, err := os.ReadFile(q.path)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, err
	}
	var items []Item
	for _, line := range splitLines(data) {
		if len(line) == 0 {
			continue
		}
		var it Item
		if err := json.Unmarshal(line, &it); err == nil {
			items = append(items, it)
		}
	}
	_ = os.Remove(q.path)
	return items, nil
}

func splitLines(data []byte) [][]byte {
	var out [][]byte
	start := 0
	for i, b := range data {
		if b == '\n' {
			out = append(out, data[start:i])
			start = i + 1
		}
	}
	if start < len(data) {
		out = append(out, data[start:])
	}
	return out
}
