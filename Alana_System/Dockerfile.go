#   verStage 1: Build the Go binaries
FROM golang:1.24-alpine AS builder

WORKDIR /app

# Install system dependencies
RUN apk add --no-cache git

# Copy go mod and sum files
COPY go.mod go.sum ./
RUN go mod download

# Copy the source code
COPY . .

# Build the Orchestrator (Ingestor)
RUN go build -o alana_ingestor ./orchestrator/ingestor.go

# Build the Search Engine
RUN go build -o alana_search ./search_engine.go

# Stage 2: Create a minimal image
FROM alpine:latest

WORKDIR /app

# Install necessary libraries (like ca-certificates for HTTPS)
RUN apk add --no-cache ca-certificates libc6-compat

# Copy the binaries from the builder
COPY --from=builder /app/alana_ingestor .
COPY --from=builder /app/alana_search .

# Copy data directory for ingestion simulation is handled via volumes in docker-compose

# Default command (can be overridden in docker-compose)
CMD ["./alana_ingestor"]
