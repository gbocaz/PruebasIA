package service

import (
	"github.com/kardianos/service"
)

func New(display, description string, runner func()) (service.Service, error) {
	cfg := &service.Config{
		Name:        "TICControlAgent",
		DisplayName: display,
		Description: description,
	}
	return service.New(&program{run: runner}, cfg)
}

type program struct {
	run    func()
	stopCh chan struct{}
}

func (p *program) Start(s service.Service) error {
	p.stopCh = make(chan struct{})
	go p.run()
	return nil
}

func (p *program) Stop(s service.Service) error {
	if p.stopCh != nil {
		close(p.stopCh)
	}
	return nil
}
