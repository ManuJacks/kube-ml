# Roadmap

This repository is a hardened **reference implementation**, not a claim that every production
control is complete. Finish the items below before describing the service as a
production-certified, internet-facing platform.

## Identity & tenancy

- OIDC/JWT authentication with scoped authorization (today: a single shared bearer token).
- Tenant isolation, quotas, rate limiting, and audit trails.
- Tests for unauthenticated and unauthorized requests under the new model.

## Reliability & operations

- Distributed tracing, SLOs, burn-rate alerts, runbooks, and incident-response ownership.
- RPO/RTO targets, encrypted backups, restore drills, and regional recovery procedures.

## Verification

- Test the rendered workloads in an ephemeral Kubernetes cluster: policy, rollout, HPA, mesh,
  and failure-injection scenarios.

## Supply chain

- Admission enforcement (Kyverno or OPA Gatekeeper) that verifies Cosign signatures.
- Provenance attestations. (SBOM generation and keyless Cosign signing already run in CI.)

## ML platform

- Multi-tenant model and data isolation.
- Model provenance, evaluation gates, and controlled rollback.
