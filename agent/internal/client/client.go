package client

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"

	"github.com/gbocaz/tic-control-agent/internal/queue"
)

type Client struct {
	BaseURL   string
	Token     string
	HTTP      *http.Client
	Queue     *queue.FileQueue
}

func New(baseURL, token string, q *queue.FileQueue) *Client {
	return &Client{
		BaseURL: baseURL,
		Token:   token,
		HTTP:    &http.Client{Timeout: 30 * time.Second},
		Queue:   q,
	}
}

func (c *Client) do(method, path string, body any, enqueueOnFail bool) ([]byte, int, error) {
	var buf io.Reader
	var raw []byte
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			return nil, 0, err
		}
		raw = b
		buf = bytes.NewReader(b)
	}
	req, err := http.NewRequest(method, c.BaseURL+path, buf)
	if err != nil {
		return nil, 0, err
	}
	req.Header.Set("Content-Type", "application/json")
	if c.Token != "" {
		req.Header.Set("Authorization", "Bearer "+c.Token)
	}
	resp, err := c.HTTP.Do(req)
	if err != nil {
		if enqueueOnFail && c.Queue != nil && raw != nil {
			_ = c.Queue.Push(queue.Item{Method: method, Path: path, Body: raw})
		}
		return nil, 0, err
	}
	defer resp.Body.Close()
	data, _ := io.ReadAll(resp.Body)
	if resp.StatusCode >= 400 {
		return data, resp.StatusCode, fmt.Errorf("http %d: %s", resp.StatusCode, data)
	}
	return data, resp.StatusCode, nil
}

func (c *Client) Post(path string, body any, enqueue bool) ([]byte, error) {
	data, _, err := c.do(http.MethodPost, path, body, enqueue)
	return data, err
}

func (c *Client) Get(path string) ([]byte, error) {
	data, _, err := c.do(http.MethodGet, path, nil, false)
	return data, err
}

func (c *Client) Download(path, dest string) error {
	req, err := http.NewRequest(http.MethodGet, c.BaseURL+path, nil)
	if err != nil {
		return err
	}
	if c.Token != "" {
		req.Header.Set("Authorization", "Bearer "+c.Token)
	}
	resp, err := c.HTTP.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		return fmt.Errorf("descarga http %d", resp.StatusCode)
	}
	f, err := os.Create(dest)
	if err != nil {
		return err
	}
	defer f.Close()
	_, err = io.Copy(f, resp.Body)
	return err
}

func (c *Client) FlushQueue() {
	if c.Queue == nil {
		return
	}
	items, err := c.Queue.Drain()
	if err != nil {
		return
	}
	for _, it := range items {
		var body any
		if len(it.Body) > 0 {
			body = json.RawMessage(it.Body)
		}
		_, _, err := c.do(it.Method, it.Path, body, true)
		if err != nil {
			return
		}
	}
}
