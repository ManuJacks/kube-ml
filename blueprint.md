# Project Blueprint: Cloud-Native NumPy & PyTorch Platform with MCP & SRE Hardening

## 1. Project Overview & Objectives
A production-grade, enterprise-tier AI platform engineering reference architecture designed for senior/staff engineering evaluation. Integrates Django, a zero-copy PyTorch-NumPy tensor bridge, Model Context Protocol (MCP) server integration, Istio Ambient mesh security, Flux GitOps delivery, Prometheus monitoring, Debian system packaging, and native systemd daemon hardening.

---

## 2. Repository Directory Structure
```text
cloud-native-numpy-platform/
├── pyproject.toml
├── Makefile
├── README.md
├── blueprint.md
├── core/
│   ├── __init__.py
│   ├── apps.py
│   ├── views.py
│   ├── urls.py
│   └── templates/
│       └── core/
│           └── tensor_gui.html
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── mcp/
│   ├── __init__.py
│   └── server.py
├── debian/
│   ├── control
│   ├── rules
│   └── changelog
├── systemd/
│   ├── numpy-mcp.service
│   ├── numpy-mcp-collector.sh
│   ├── numpy-mcp-collector.service
│   └── numpy-mcp-collector.timer
└── clusters/
    └── minikube/
        ├── apps/
        │   ├── deployment.yaml
        │   ├── service.yaml
        │   └── hpa.yaml
        └── monitoring/
            ├── prometheus-rules.yaml
            ├── alertmanager-config.yaml
            └── mcp-service-alert.yaml

3. Core Architecture & Tensor Bridge (core/views.py)

    Zero-copy tensor bridge leveraging torch.from_numpy() with C-contiguous float32 arrays.

    Thread constraint settings (torch.set_num_threads(2)) to prevent CPU thrashing in containerized environments.

    Strict payload size validation (MAX_ELEMENTS = 1000000) to prevent out-of-memory cascades.

4. Future Delivery Targets: Debian Packaging & Systemd Daemons (debian/ & systemd/)

    Python Module (pyproject.toml): Standardized build metadata and console script entry points (numpy-mcp-server = mcp.server:main).

    Debian packaging is intentionally deferred until authentication/authorization and the read-only platform interfaces are complete. The preferred package target is host-side health/metrics/MCP tooling; the Django/ML service remains container-native.

    Systemd Service (numpy-mcp.service): Unprivileged execution (User=sre-agent), automatic restarts (Restart=on-failure), watchdog health checks (WatchdogSec=30s), and system hardening (ProtectSystem=full).

    Prometheus Textfile Collector (numpy-mcp_collector.sh): Bash script executed via a 15-second systemd timer that writes native metrics (numpy_mcp_service_up) to the node_exporter textfile directory.

5. Kubernetes & Monitoring Manifests (clusters/minikube/)

    Deployment & HPA: Resource requests (500m/512Mi) and limits (1000m/1Gi), with HPA scaling triggered at 70% CPU utilization.

    Prometheus Rules (prometheus-rules.yaml & mcp-service-alert.yaml):

        PodMemoryHighUtilization: Triggers when working set exceeds 85% of limit for 2m.

        PodMemoryCriticalSaturation: Triggers when working set exceeds 95% of limit for 30s.

        PodOOMKilledSoon: Triggers on container exit code 137.

        NumpyMCPServiceDown: Triggers when systemd service metric numpy_mcp_service_up == 0.


---

## 6. Enterprise Cloud Hardening & Multi-Tenant Security Blueprint

### 6.0 Authentication roadmap
Authentication is intentionally not implemented in the current reference service. Before exposing the API beyond a trusted internal boundary, add an explicit authentication and authorization layer (for example, OIDC/JWT validation or an API gateway policy), define scopes/tenant boundaries, and add tests for unauthenticated and unauthorized requests. This is a required follow-up control, not an assumption of the current deployment.

### 6.0.1 Ordered next steps
1. Implement and verify authentication and authorization for HTTP and MCP interfaces.
2. Add tenant/scoped access, rate limits, audit events, and negative security tests.
3. Run integration and failure-path tests in a real or ephemeral Kubernetes cluster.
4. Verify signed images and SBOMs through admission policy.
5. Complete operational drills, SLO evidence, rollback, and recovery testing.
6. Package the authenticated, read-only host-side health/metrics/MCP tooling as a signed Debian artifact.

The current implementation includes deterministic, read-only examples through the GUI, `/api/v1/examples`, and the MCP stdio server. These interfaces deliberately do not mutate Kubernetes, execute arbitrary commands, access secrets, or expose tenant data.

To transition from the local GitOps/Minikube reference implementation to a hardened, enterprise-grade production cloud deployment (EKS, GKE, or AKS), the platform enforces strict multi-tenant zero-trust isolation, least-privilege identity, runtime boundary enforcement, and supply-chain controls.

### 6.1 Zero-Trust Network Policies (Cilium / Calico CNI)
- **Default-Deny Ingress & Egress**: All non-whitelisted pod-to-pod and egress communication in the `ml-workloads` namespace is blocked by default via `NetworkPolicy`.
- **Mesh Ingress Filtering**: App pods only accept ingress traffic originating from Istio Gateway proxies / ztunnel (`istio-system` namespace) on target port 8000. Direct pod-to-pod bypass within the cluster is strictly dropped.
- **Egress Perimeter Controls**: Egress is locked down to authorized endpoints only (e.g., CoreDNS on port 53, cloud-managed object storage like AWS S3 / GCS, and internal managed databases).

### 6.2 Least-Privilege Identity & Scoped RBAC
- **Dedicated Service Account**: Disable auto-mounting of API tokens (`automountServiceAccountToken: false` unless explicitly required). Deploy under dedicated `kube-ml-sa` rather than `default`.
- **Scoped Namespace RBAC**: Restrict application cluster privileges using localized `Role` and `RoleBinding` within `ml-workloads`—never attach `ClusterRoleBinding`.
- **Cloud Workload Identity / IRSA**: Map cloud IAM permissions directly to `kube-ml-sa` (e.g., AWS IRSA annotations or GCP Workload Identity bindings), eliminating long-lived static credentials or Kubernetes Secret storage for cloud resources.

### 6.3 Pod Security Standards (PSS Restricted) & Container Runtime Hardening
- **Namespace-Level PSS Restricted**: Label namespaces with `pod-security.kubernetes.io/enforce: restricted`.
- **Read-Only Root Filesystem**: Set `securityContext.readOnlyRootFilesystem: true`. Temporary or scratch storage is mounted using ephemeral in-memory or bounded `emptyDir` volumes (e.g., `/tmp`).
- **Capability Dropping**: Drop all default Linux capabilities (`drop: ["ALL"]`) and prohibit privilege escalation (`allowPrivilegeEscalation: false`).
- **Non-Root Execution & Seccomp**: Enforce non-root execution (`runAsNonRoot: true`, `runAsUser: 10001`, `runAsGroup: 10001`) with runtime default system call profiling (`seccompProfile.type: RuntimeDefault`).

### 6.4 External Secret Management & Encryption
- **External Secrets Operator (ESO)**: Integrate with HashiCorp Vault, AWS Secrets Manager, or GCP Secret Manager to dynamically inject secrets at runtime without checking sensitive values into Git repositories.
- **Envelope Encryption**: Enforce cluster-level KMS envelope encryption for `etcd` backing all secret and configuration state.

### 6.5 Supply Chain Security & Continuous Governance
- **Image Signing & Attestation**: Sign container images with Cosign (Sigstore) in CI/CD; enforce policy admission with Kyverno or OPA Gatekeeper to block unsigned images from admission.
- **SBOM & Vulnerability Gates**: Generate Software Bill of Materials (SBOM) with Syft/Trivy during container build, enforcing automated break-build triggers on high/critical CVE thresholds.

### 6.6 Authentication and authorization
- **Identity provider integration**: Add OIDC/JWT validation at the gateway or application boundary.
- **Authorization model**: Define scopes, tenant identity, model permissions, and operator/admin roles.
- **Abuse controls**: Add per-identity rate limits, request quotas, replay protection, and audit logging.
- **Verification**: Test missing, expired, malformed, and insufficient-scope credentials; do not treat network location as identity.

### 6.7 Observability, SLOs, and incident response
- **SLIs**: Track availability, request latency percentiles, error rate, payload rejection rate, saturation, and OOM events.
- **SLOs**: Establish versioned availability and latency objectives with an error-budget policy before production launch.
- **Telemetry**: Correlate structured logs, Prometheus metrics, distributed traces, and deployment revisions without recording payload contents or credentials.
- **Alerting**: Alert on SLO burn rate, readiness failures, elevated 5xx responses, resource saturation, and certificate expiry.
- **Operations**: Maintain runbooks, ownership, escalation paths, post-incident reviews, and tested rollback procedures.

### 6.8 Real-cluster and policy validation
- Render and validate Helm/Kustomize output in CI for every change.
- Run ephemeral-cluster integration tests covering rollout, probes, HPA behavior, Gateway routing, NetworkPolicy behavior, and graceful termination.
- Enforce PSS Restricted, RBAC, image provenance, and network-policy rules with policy-as-code (Kyverno, OPA Gatekeeper, or equivalent).
- Exercise failure injection for pod eviction, dependency failure, malformed requests, resource pressure, and partial rollouts.

### 6.9 Disaster recovery and data protection
- Define RPO/RTO targets and ownership for every stateful dependency.
- Keep the application stateless; externalize durable state to managed services with encryption and access controls.
- Automate encrypted backups, retention, restore verification, and cross-zone/region recovery where required.
- Perform scheduled restore drills and record evidence that the declared RPO/RTO is achievable.

### 6.10 Multi-tenancy and model governance
- Isolate tenant data, namespaces, quotas, network paths, and cloud identities according to the selected tenancy model.
- Enforce tenant-aware authorization and prevent cross-tenant identifiers, logs, metrics, caches, and object-storage access.
- Version models and preprocessing contracts; record provenance, evaluation results, rollback metadata, and approved deployment state.
- Define model-specific resource budgets, abuse limits, numerical safety checks, and change-approval requirements.

