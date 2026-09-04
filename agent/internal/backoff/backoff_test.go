package backoff_test

import (
	"testing"
	"time"

	"github.com/gbocaz/tic-control-agent/internal/backoff"
)

func TestBackoffGrowsAndCaps(t *testing.T) {
	p := backoff.Policy{}
	d1 := p.Next()
	d2 := p.Next()
	if d2 < d1 {
		t.Fatalf("expected growth, got %s then %s", d1, d2)
	}
	for i := 0; i < 10; i++ {
		p.Next()
	}
	if p.Next() > 90*time.Second {
		t.Fatal("backoff exceeded cap with jitter")
	}
}
