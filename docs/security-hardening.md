# Security hardening

These controls close the gap between local defaults and multi-tenant cluster expectations
(EKS, GKE, AKS). They are defined in
[`clusters/minikube/apps/hardened-manifest.yaml`](../clusters/minikube/apps/hardened-manifest.yaml).

## Zero-trust networking (Calico / Cilium)

- **Default-deny ingress and egress** across the `ml-workloads` namespace.
- **Gateway-only ingress.** The application pod accepts traffic only from the Istio ztunnel and
  ingress gateway proxies in `istio-system`, on port 8000. Direct pod-to-pod attempts that
  bypass the mesh are rejected.
- **Egress allow-list.** Outbound traffic is limited to CoreDNS (`kube-dns:53`) and configured
  storage or database endpoints, blocking exfiltration channels.

## Least-privilege identity

- **Dedicated service account** `kube-ml-sa` with `automountServiceAccountToken: false`.
- **Cloud IAM mapping.** Annotations support AWS IRSA and GCP Workload Identity, so no static
  credentials are needed.
- **Namespace-scoped RBAC** via `Role` and `RoleBinding`; no cluster-wide permissions.

## Pod Security Standards (Restricted) & container hardening

- Namespace enforces `pod-security.kubernetes.io/enforce: restricted`.
- `readOnlyRootFilesystem: true`, with scratch space on an in-memory `emptyDir` at `/tmp`.
- All Linux capabilities dropped (`drop: ["ALL"]`); `allowPrivilegeEscalation: false`.
- Runs as UID/GID `10001` (`runAsNonRoot: true`) with `seccompProfile.type: RuntimeDefault`.

## Secrets & supply chain

- **External Secrets Operator** keeps credentials out of GitOps manifests, syncing on demand
  from HashiCorp Vault, AWS Secrets Manager, or GCP Secret Manager.
- **CI checks:** `pip-audit` and Trivy HIGH/CRITICAL scanning.
- **Provenance:** the push pipeline publishes an SPDX SBOM and signs images with keyless Cosign
  (see [GitOps & delivery](gitops-and-delivery.md)). Admission enforcement with Kyverno or
  OPA Gatekeeper is still a deployment-specific follow-up.
- **Source analysis:** GitHub CodeQL runs extended Python security queries on pushes, pull
  requests, and a weekly schedule.
- **Application credentials:** bearer-token authentication protects the API and MCP interfaces;
  replace the shared token with OIDC/JWT and external secret management before production use.

## Application-level guards

- **Zero-copy bridge.** `torch.from_numpy()` over C-contiguous `float32` arrays shares memory
  between NumPy and PyTorch. Note that the upstream JSON-to-array parse is not zero-copy.
- **CPU throttling.** `torch.set_num_threads(2)` prevents CPU thrashing under pod limits.
- **Request-size ceiling.** `MAX_ELEMENTS = 1,000,000` and a 25 MB body limit cap what a single
  request can allocate. They bound per-request memory, not total memory under high
  concurrency; pair them with pod memory limits and the HPA.
- **Input validation.** Non-finite numbers, empty payloads, and malformed JSON are rejected.

See [Authentication](authentication.md) for access control and the [Roadmap](roadmap.md) for
what remains before this could be called production-certified.
