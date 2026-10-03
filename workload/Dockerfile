FROM golang:1.27.1-bookworm AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
ARG REVISION=development
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w -X main.revision=${REVISION}" -o /workshop ./cmd/workshop
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=build /workshop /usr/local/bin/workshop
USER 65532:65532
ENTRYPOINT ["workshop"]
CMD ["api"]
