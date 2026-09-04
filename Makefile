.PHONY: test api web agent

api:
	cd backend && python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

web:
	cd frontend && npm run dev

agent:
	cd agent && go run ./cmd/tic-agent run --config /tmp/tic-control/agent.json

test:
	cd backend && python3 -m pytest -q
	cd agent && go test ./...
