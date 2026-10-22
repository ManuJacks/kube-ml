# Cloud-Native NumPy & PyTorch Platform with MCP & SRE Hardening

[![CI/CD Pipeline](https://github.com/ManuJacks/kube-ml/actions/workflows/ci.yml/badge.svg?branch=development)](https://github.com/ManuJacks/kube-ml/actions/workflows/ci.yml)

Production-grade, enterprise-tier AI platform reference architecture integrating:
- **Django** web application framework.
- **Zero-Copy Tensor Bridge** leveraging `torch.from_numpy()` with C-contiguous `float32` arrays.
- **CPU Throttling**: Hard limit via `torch.set_num_threads(2)` to prevent CPU thrashing in containerized/pod environments.
- **OOM Cascading Shield**: Strict payload size ceiling (`MAX_ELEMENTS = 1,000,000`) and 25MB body buffer limits.
- **Model Context Protocol (MCP)** server integration.
- **Istio Ambient Mesh**: Zero-sidecar, high-performance mTLS service mesh and HTTPS edge gateway termination.
- **Flux CD GitOps**: Automated continuous reconciliation with branch synchronization and prune management.
- **Enterprise Hardening**: Zero-trust network segmentation, least-privilege RBAC, and Kubernetes Pod Security Standards (PSS Restricted).
- **Minikube / Kubernetes** deployment with HPA scaling and Prometheus observability.

---

## 1. Local Development & Testing

### Prerequisites
- Python 3.10+
- `pip` and `python3-venv`

### Setup Virtual Environment
```bash
# Using Makefile
make venv
make install

# Or manually:
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```
*(Tip: To install CPU-only PyTorch for faster download: `pip install torch --index-url https://download.pytorch.org/whl/cpu`)*

### Run Automated Unit Tests
```bash
python manage.py test core
# or: make test
```
Verifies:
- Zero-copy shared memory buffer integrity (`np.shares_memory`).
- CPU thread constraint enforcement (`torch.get_num_threads() == 2`).
- Payload size boundaries (`MAX_ELEMENTS = 1,000,000` and `DATA_UPLOAD_MAX_MEMORY_SIZE`).
- Error handling (empty payloads, non-list structures, invalid JSON).
- HTML web portal rendering.

### Run Local Development Server
```bash
python manage.py runserver 0.0.0.0:8000
# or: make run-dev
```
- **Web UI**: Navigate to `http://localhost:8000/` to test tensor computations interactively.
- **API Endpoint**:
  ```bash
  curl -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d '{"data": [10.0, 20.0, 30.0, 40.0]}'
  ```

---

## 2. Deploying to Minikube

The Kubernetes architecture uses standard declarative manifests structured under `clusters/minikube/apps/`.

### Prerequisites
- `minikube` installed and running (`minikube status`)
- `kubectl` configured

### Step 1: Start Minikube & Configure Docker Daemon
Point your local Docker CLI to Minikube's in-cluster Docker daemon so images built locally are immediately visible without an external registry:
```bash
# 1. Start minikube if not already running
minikube start --driver=docker

# 2. Point terminal Docker environment to Minikube's Docker daemon
eval $(minikube docker-env)
```

### Step 2: Build the Container Image
With Minikube's Docker environment active, build the container image:
```bash
docker build -t kube-ml-app:v1 .
```

### Step 3: Create the Kubernetes Manifests (`clusters/minikube/apps/`)
Create the target deployment and service files:

#### `clusters/minikube/apps/deployment.yaml`
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kube-ml-platform
  labels:
    app: kube-ml-platform
spec:
  replicas: 1
  selector:
    matchLabels:
      app: kube-ml-platform
  template:
    metadata:
      labels:
        app: kube-ml-platform
    spec:
      containers:
      - name: kube-ml-app
        image: kube-ml-app:v1
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8000
          name: http
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "1000m"
            memory: "1Gi"
        readinessProbe:
          httpGet:
            path: /
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 15
```

#### `clusters/minikube/apps/service.yaml`
```yaml
apiVersion: v1
kind: Service
metadata:
  name: kube-ml-service
spec:
  type: NodePort
  selector:
    app: kube-ml-platform
  ports:
  - port: 8000
    targetPort: 8000
    nodePort: 30080
```

#### `clusters/minikube/apps/hpa.yaml`
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: kube-ml-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: kube-ml-platform
  minReplicas: 1
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### Step 4: Apply Manifests to the Cluster
```bash
kubectl apply -f clusters/minikube/apps/
```

Verify rollout:
```bash
kubectl rollout status deployment/kube-ml-platform
kubectl get pods -l app=kube-ml-platform
kubectl get svc kube-ml-service
```

### Step 5: Access the Service in Minikube
Open the service directly in your browser:
```bash
minikube service kube-ml-service
```
Or forward a port to your local machine:
```bash
kubectl port-forward svc/kube-ml-service 8000:8000
```
Then visit `http://localhost:8000/`.

---

## 3. Istio Ambient Mesh & HTTPS Ingress Gateway

The platform leverages **Istio Ambient Mode** and Kubernetes Gateway API for zero-sidecar, high-performance service mesh networking with mutual TLS (mTLS) and HTTPS edge termination.

### Architecture Overview
1. **Istio Ambient Mode**: The namespace (e.g. `ml-workloads`) is labeled `istio.io/dataplane-mode=ambient`. Traffic is routed through shared node-level `ztunnel` proxies rather than injecting heavy sidecar containers.
2. **Strict mTLS**: Enforced via `PeerAuthentication` (`mode: STRICT`), ensuring all East-West pod-to-pod communications are fully encrypted.
3. **HTTPS Edge Gateway**: An Istio Gateway listener binds to port `443` with `mode: Terminate`, utilizing the TLS secret `django-credential-secret`.

### Accessing HTTPS in Minikube

Because Minikube operates as a local Docker cluster without a cloud load balancer provider, `LoadBalancer` services show `EXTERNAL-IP: <pending>` unless routed. Choose any of the following methods to access the `kube-ml-gateway`:

#### Method 1: Direct via Gateway NodePort (Fastest — No Sudo Required)
The Istio Gateway controller (`kube-ml-gateway-istio`) dynamically allocates a NodePort for port 443 (e.g., `32296`):
```bash
# Retrieve Minikube IP and dynamic HTTPS NodePort for the gateway
GATEWAY_IP=$(minikube ip)
NODE_PORT=$(kubectl get svc kube-ml-gateway-istio -n ml-workloads -o jsonpath='{.spec.ports[?(@.name=="https")].nodePort}')

echo "Access GUI at: https://${GATEWAY_IP}:${NODE_PORT}/"

# Test via curl (use -k for the self-signed certificate)
curl -k https://${GATEWAY_IP}:${NODE_PORT}/
```
Open **`https://${GATEWAY_IP}:${NODE_PORT}/`** in your browser (e.g. `https://192.168.49.2:32296/`) and accept the self-signed TLS prompt. You will see the live interactive **Cloud-Native NumPy & PyTorch Platform**!

#### Method 2: Standard Port 443 via `minikube tunnel`
To route standard port `443` traffic and allocate an external IP directly:
1. In a separate terminal session, run:
   ```bash
   sudo minikube tunnel
   ```
2. Verify that `kube-ml-gateway-istio` receives an `EXTERNAL-IP`:
   ```bash
   kubectl get svc kube-ml-gateway-istio -n ml-workloads
   ```
3. Access directly via the assigned external IP on standard HTTPS:
   ```bash
   curl -k https://<EXTERNAL-IP>/
   ```

#### Method 3: Local Port-Forwarding
Alternatively, forward the HTTPS gateway directly to a local port:
```bash
kubectl port-forward svc/kube-ml-gateway-istio -n ml-workloads 8443:443
```
Then open `https://localhost:8443/` in your browser.

---

## 4. GitOps Continuous Delivery with Flux CD

The repository is configured for automated GitOps continuous reconciliation via [Flux CD](https://fluxcd.io).

### Structure
- `clusters/minikube/apps/kustomization.yaml`: Kustomizes the application manifests (`deployment.yaml`, `service.yaml`, `hpa.yaml`).
- `clusters/minikube/flux-system/gotk-sync.yaml`:
  - `GitRepository`: Watches `https://github.com/ManuJacks/kube-ml.git` on the `development` branch with a 1-minute poll interval.
  - `Kustomization`: Reconciles `./clusters/minikube/apps` into the `ml-workloads` namespace with automated pruning.

### Bootstrapping Flux on Minikube

1. **Install Flux into Minikube**:
   ```bash
   flux install
   ```

2. **Apply the GitOps Sync Manifests**:
   ```bash
   kubectl apply -k clusters/minikube/flux-system/
   ```

3. **Verify GitOps Reconciliation**:
   ```bash
   flux get sources git
   flux get kustomizations
   ```

4. **Trigger Manual Immediate Reconciliation**:
   ```bash
   flux reconcile kustomization kube-ml-apps --with-source
   ```

---

---

## 5. Enterprise Cloud Hardening & Security Compliance

To bridge the gap between local development defaults and enterprise-grade multi-tenant compliance (AWS EKS, GCP GKE, Azure AKS), the platform provides hardened production controls specified in [`clusters/minikube/apps/hardened-manifest.yaml`](clusters/minikube/apps/hardened-manifest.yaml).

### 5.1 Zero-Trust Network Policies (Calico / Cilium)
- **Default-Deny Ingress & Egress**: Blocks all incoming and outgoing traffic by default across the namespace (`ml-workloads`).
- **Gateway Ingress Filtering**: Restricts ingress so the application pod exclusively accepts traffic originating from the Istio ztunnel / ingress gateway proxies in the `istio-system` namespace on port 8000. Direct pod-to-pod attempts bypassing the mesh are rejected.
- **Egress Perimeter Isolation**: Explicitly whitelists outbound traffic to CoreDNS (`kube-dns:53`) and configured cloud storage / database endpoints, blocking data exfiltration channels.

### 5.2 Least-Privilege Identity & Scoped RBAC
- **Dedicated Service Account**: Replaces the default service account with a dedicated `kube-ml-sa` that disables token automounting (`automountServiceAccountToken: false`).
- **Cloud IAM Mapping (IRSA / Workload Identity)**: Pre-configured annotations allow mapping cloud IAM permissions (AWS IAM Roles for Service Accounts or GCP Workload Identity) directly to the Kubernetes Service Account, removing the need for static credentials or committed secrets.
- **Localized Namespace RBAC**: Restricts in-cluster access via namespace-scoped `Role` and `RoleBinding` objects, prohibiting cluster-wide permissions.

### 5.3 Pod Security Standards (PSS Restricted) & Container Hardening
- **Namespace-Level PSS Restricted**: Enforces `pod-security.kubernetes.io/enforce: restricted`.
- **Read-Only Root Filesystem**: `readOnlyRootFilesystem: true` prevents unauthorized tampering or malicious script execution on the container disk. Temporary and scratch files use an in-memory ephemeral `emptyDir` mounted at `/tmp`.
- **Dropped Linux Capabilities**: Drops all default capabilities (`drop: ["ALL"]`) and prevents privilege escalation (`allowPrivilegeEscalation: false`).
- **Non-Root Execution & Seccomp**: Enforces UID/GID `10001` (`runAsNonRoot: true`) combined with standard kernel filter profiles (`seccompProfile.type: RuntimeDefault`).

### 5.4 External Secret Management & Supply Chain Governance
- **External Secrets Operator (ESO)**: Decouples credentials from GitOps manifests, synchronizing secrets on-demand from HashiCorp Vault, AWS Secrets Manager, or GCP Secret Manager.
- **Supply Chain Attestation**: Integrates with Cosign (Sigstore) image signing and Trivy/Syft SBOM generation in the CI/CD pipeline, enforced via admission controllers (Kyverno / OPA Gatekeeper).

---

## 6. Repository Structure
```text
.
├── .github/workflows/ci.yml         # GitHub Actions CI pipeline (Unit tests + Docker)
├── pyproject.toml                   # Python build metadata & entry points
├── Makefile                         # Automation targets
├── Dockerfile                       # Multi-stage/lean container build
├── manage.py                        # Django management script
├── config/                          # Django project configuration
│   ├── settings.py                  # Core settings & OOM body limit
│   ├── urls.py                      # Root routing
│   └── wsgi.py                      # WSGI entry point
├── core/                            # Core tensor application
│   ├── apps.py                      # App configuration
│   ├── views.py                     # Zero-copy tensor bridge & endpoints
│   ├── urls.py                      # Core route declarations
│   ├── tests.py                     # Unit & integration test suite
│   └── templates/core/              # Interactive HTML GUI
│       └── tensor_gui.html
├── mcp/                             # Model Context Protocol server
│   └── server.py
└── clusters/minikube/               # GitOps & Kubernetes manifests
    ├── apps/                        # Application Kustomization & manifests
    │   ├── kustomization.yaml
    │   ├── deployment.yaml
    │   ├── service.yaml
    │   ├── hpa.yaml
    │   └── hardened-manifest.yaml   # PSS Restricted, NetworkPolicies, & SA
    └── flux-system/                 # Flux GitOps source & sync manifests
        ├── kustomization.yaml
        └── gotk-sync.yaml
```
