# Third-party components

CloudNativePG is an independently distributed Apache-2.0 PostgreSQL operator.
The dormant database profile uses its public Cluster API; no operator source is
vendored. Its release licenses and notices remain authoritative when installing
the pinned operator distribution. The application and infrastructure retain their
own implementation and ownership boundaries.

Kubernetes API schemas and CloudNativePG served CRDs are downloaded from their
official, versioned repositories/releases for checksum-verified validation only.
They are not copied into the application source. Dependency and container image
licenses must accompany any future image/operator redistribution.

The shared workload uses the official Google Cloud Go Pub/Sub v2 and Storage
clients and AWS SDK for Go v2 configuration/SQS/S3 clients under their respective
Apache-2.0 distributions. It also links PostgreSQL, Prometheus and OpenTelemetry
Go dependencies. Image builds collect upstream LICENSE/NOTICE/COPYING files for
every actual linked third-party module plus the Go standard-library license into
`/usr/share/licenses/report-workshop/`, with a module/version/file index. A missing
module license fails the build. This preserves dependency notices; it does not
assign a new license to the user's own source or imply cloud qualification.
