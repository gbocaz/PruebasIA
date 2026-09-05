package backoff

import (
	"math/rand"
	"time"
)

type Policy struct {
	Attempt int
}

func (p *Policy) Next() time.Duration {
	p.Attempt++
	exp := p.Attempt
	if exp > 6 {
		exp = 6
	}
	base := time.Second * time.Duration(1<<uint(exp-1))
	if base > 60*time.Second {
		base = 60 * time.Second
	}
	jitter := time.Duration(rand.Int63n(int64(base / 3)))
	return base + jitter
}

func (p *Policy) Reset() {
	p.Attempt = 0
}
