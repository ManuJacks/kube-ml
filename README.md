# Cloud-Native NumPy & PyTorch Platform with MCP & SRE Hardening

[![CI/CD Pipeline](https://github.com/ManuJacks/kube-ml/actions/workflows/ci.yml/badge.svg?branch=development)](https://github.com/ManuJacks/kube-ml/actions/workflows/ci.yml)

Production-grade, enterprise-tier AI platform reference architecture integrating:
- **Django** web application framework.
- **Zero-Copy Tensor Bridge** leveraging `torch.from_numpy()` with C-contiguous `float32` arrays.
- **CPU Throttling**: Hard limit via `torch.set_num_threads(2)` to prevent CPU thrashing in containerized/pod environments.
- **OOM Cascading Shield**: Strict payload size ceiling (`MAX_ELEMENTS = 1,000,000`) and 25MB body buffer limits.
- **Model Context Protocol (MCP)** server integration.
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

Per the project [blueprint.md](blueprint.md), the Kubernetes architecture uses standard manifests structured under `clusters/minikube/apps/`.

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
docker build -t django-numpy-app:v1 .
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
        image: django-numpy-app:v1
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

Because Minikube operates as a local Docker cluster without a cloud load balancer provider, `LoadBalancer` services will show `EXTERNAL-IP: <pending>` unless routed. Choose any of the following methods to access your HTTPS gateway:

#### Method 1: Direct via NodePort (Fastest — No Sudo Required)
The gateway service exposes port 443 via a dynamically assigned NodePort (e.g., `31313`):
```bash
# Obtain Minikube node IP and assigned HTTPS NodePort
GATEWAY_IP=$(minikube ip)
NODE_PORT=$(kubectl get svc django-gateway-istio -n ml-workloads -o jsonpath='{.spec.ports[?(@.name=="https")].nodePort}')

# Send HTTPS request (use -k for self-signed certificates)
curl -k https://${GATEWAY_IP}:${NODE_PORT}/
```
You can also open `https://${GATEWAY_IP}:${NODE_PORT}/` directly in your browser (accept the self-signed certificate prompt).

#### Method 2: Standard Port 443 via `minikube tunnel`
To route standard port `443` traffic and allocate an external IP directly:
1. In a separate terminal session, run:
   ```bash
   sudo minikube tunnel
   ```
2. Verify that the gateway service receives an `EXTERNAL-IP`:
   ```bash
   kubectl get svc django-gateway-istio -n ml-workloads
   ```
3. Access directly via the assigned external IP:
   ```bash
   curl -k https://<EXTERNAL-IP>/
   ```

#### Method 3: Local Port-Forwarding
Alternatively, forward the HTTPS port to a local high port:
```bash
kubectl port-forward svc/django-gateway-istio -n ml-workloads 8443:443
```
Then visit `https://localhost:8443/` in your browser.

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

## 5. Repository Structure
```text
.
├── .github/workflows/ci.yml         # GitHub Actions CI pipeline (Unit tests + Docker)
├── blueprint.md                     # Architectural specification
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
    ├── apps/                        # Application Kustomization (Deployment, Service, HPA)
    │   ├── kustomization.yaml
    │   ├── deployment.yaml
    │   ├── service.yaml
    │   └── hpa.yaml
    └── flux-system/                 # Flux GitOps source & sync manifests
        ├── kustomization.yaml
        └── gotk-sync.yaml
```
│   ├── views.py                     # Zero-copy tensor bridge & endpoints
│   ├── urls.py                      # Core route declarations
│   ├── tests.py                     # Unit & integration test suite
│   └── templates/core/              # Interactive HTML GUI
│       └── tensor_gui.html
├── mcp/                             # Model Context Protocol server
│   └── server.py
└── clusters/minikube/               # Kubernetes & monitoring manifests
    ├── apps/                        # Deployment, Service, HPA
    └── monitoring/                  # Prometheus rules & Alertmanager
```
