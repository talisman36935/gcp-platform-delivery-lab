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
