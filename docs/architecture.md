# Architecture

## Request path

```mermaid
flowchart LR
    C[Client / MCP agent] -->|HTTPS :443| GW[Istio Gateway<br/>TLS termination]
    GW -->|mTLS via ztunnel| APP

    subgraph NS[ml-workloads namespace · PSS Restricted · default-deny]
        APP[Django pods<br/>NumPy → torch.from_numpy<br/>2 torch threads]
        HPA[HPA<br/>CPU 70%] -.scales.-> APP
    end

    PROM[Prometheus] -.scrapes /metrics.-> APP
```

## Delivery path

```mermaid
flowchart LR
    DEV[git push<br/>development] --> CI[GitHub Actions<br/>test · lint · scan · SBOM · Cosign]
    CI --> REG[(GHCR<br/>commit-tagged image)]
    CI -->|promotion commit<br/>skip ci| DEV
    FLUX[Flux CD] -->|polls every 1 min| DEV
    FLUX -->|reconcile + prune| K8S[Cluster]
    REG -->|image pull| K8S
```

## Repository structure

Abridged; see the repository for the full tree (Helm chart, additional manifests, and so on).

```text
.
├── .github/workflows/ci.yml         # CI/CD: tests, lint, scan, build, sign, promote
├── pyproject.toml                   # Build metadata & entry points
├── Makefile                         # Automation targets
├── Dockerfile                       # Lean container build
├── manage.py                        # Django management script
├── config/                          # Django project configuration
│   ├── settings.py                  # Core settings & request-size limits
│   ├── urls.py                      # Root routing
│   └── wsgi.py                      # WSGI entry point
├── core/                            # Tensor application
│   ├── views.py                     # Zero-copy tensor bridge & endpoints
│   ├── urls.py                      # Route declarations
│   ├── tests.py                     # Unit & integration tests
│   └── templates/core/
│       └── tensor_gui.html          # Interactive GUI
├── mcp/
│   └── server.py                    # Model Context Protocol server
├── docs/                            # Documentation (this folder), incl. openapi.yaml
└── clusters/minikube/               # GitOps & Kubernetes manifests
    ├── apps/
    │   ├── kustomization.yaml
    │   ├── deployment.yaml
    │   ├── service.yaml
    │   ├── hpa.yaml
    │   └── hardened-manifest.yaml   # PSS Restricted, NetworkPolicies, ServiceAccount
    └── flux-system/
        ├── kustomization.yaml
        └── gotk-sync.yaml           # Flux source & sync
```
