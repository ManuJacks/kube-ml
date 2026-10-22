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

4. Debian Packaging & Systemd Daemons (debian/ & systemd/)

    Python Module (pyproject.toml): Standardized build metadata and console script entry points (numpy-mcp-server = mcp.server:main).

    Debian Package (debian/control): Complete dpkg-buildpackage configuration with automatic dependency tracking (python3-torch, python3-numpy).

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

