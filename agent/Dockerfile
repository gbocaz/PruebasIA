FROM golang:1.24-bookworm AS build
WORKDIR /src
COPY go.mod go.sum* ./
RUN go mod download || true
COPY . .
RUN CGO_ENABLED=0 go build -o /tic-agent ./cmd/tic-agent

FROM gcr.io/distroless/static-debian12
COPY --from=build /tic-agent /tic-agent
ENTRYPOINT ["/tic-agent"]
