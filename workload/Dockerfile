FROM golang:1.27.1-bookworm@sha256:69a7b9788769bec032d238959b61854e9ae87f57be9029ec04e9885fabf99195 AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
ARG REVISION=development
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w -X main.revision=${REVISION}" -o /workshop ./cmd/workshop
FROM scratch
COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=build /workshop /usr/local/bin/workshop
USER 65532:65532
ENTRYPOINT ["/usr/local/bin/workshop"]
CMD ["api"]
