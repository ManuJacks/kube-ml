# Minikube restart runbook

[`scripts/restart_ml_env.sh`](../scripts/restart_ml_env.sh) is the repeatable local
restart and validation path for the Minikube environment. It targets the current
Kustomize resources in `ml-workloads`; it does not target dynamically generated pod
names.

The current stable resource names are:

| Resource | Name |
| --- | --- |
| Application Deployment | `kube-ml-platform` |
| Application Service | `kube-ml-service` |
| Gateway | `kube-ml-gateway` |
| Gateway Deployment/Service | `kube-ml-gateway-istio` |
| Namespace | `ml-workloads` |

## Normal restart

Make sure Docker is running, then run:

```bash
./scripts/restart_ml_env.sh
```

The normal mode starts or reuses Minikube, builds the repository root Dockerfile in
Minikube's Docker daemon, removes the obsolete `django-release` Helm release if it
exists, applies the current runtime manifests, uses the local `kube-ml-app:v1`
image, restarts the application Deployment, and validates the Istio Gateway.

The default is NodePort mode and does not require `sudo`. The HTTPS URL is the
second URL printed at the end, usually similar to:

```text
https://192.168.49.2:32296/
```

The certificate is self-signed. Accept the browser certificate warning locally.

## Modes and environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `SKIP_START` | `0` | Set to `1` when Minikube is already running. |
| `SKIP_TUNNEL` | `1` | Use NodePort access without `sudo`; set to `0` for `minikube tunnel`. |
| `REPAIR_NETWORK` | `0` | Enable exceptional Docker, CoreDNS, and Gateway recovery actions. |

For a quick repeat against an already-running cluster:

```bash
SKIP_START=1 ./scripts/restart_ml_env.sh
```

For network/Gateway recovery, use the more invasive mode deliberately:

```bash
REPAIR_NETWORK=1 SKIP_START=1 ./scripts/restart_ml_env.sh
```

Repair mode prunes unused Docker data inside Minikube, restarts CoreDNS, and
temporarily scales/recreates the Istio Gateway. It should not be used for every
routine restart.

To use a host-level tunnel instead of the Gateway NodePort:

```bash
SKIP_TUNNEL=0 ./scripts/restart_ml_env.sh
```

This requires interactive `sudo` authentication. The tunnel log is written to
`scripts/minikube_tunnel.log`. A LoadBalancer `EXTERNAL-IP` may remain `<pending>`
without the tunnel; that is normal for Minikube.

## Prerequisites

- Docker daemon access for the current user.
- `minikube`, `kubectl`, `helm`, and `curl` on `PATH`.
- A running Istio control plane and Gateway API support in Minikube.
- The `ml-workloads` namespace and `kube-ml-api-token` Secret. The Secret is not
  created by the script because credentials must remain out of source control.

Create the application Secret if it does not exist:

```bash
export KUBE_ML_API_TOKEN="$(openssl rand -hex 32)"
kubectl -n ml-workloads create secret generic kube-ml-api-token \
  --from-literal=token="$KUBE_ML_API_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -
```

## Validation

The script waits for the application and Gateway rollouts and prints access URLs.
Independently verify the final state with:

```bash
kubectl -n ml-workloads get deployment,pods,svc,gateway,httproute -o wide

GATEWAY_IP="$(minikube ip)"
GATEWAY_PORT="$(kubectl -n ml-workloads get svc kube-ml-gateway-istio \
  -o jsonpath='{.spec.ports[?(@.name=="https")].nodePort}')"

curl -k "https://${GATEWAY_IP}:${GATEWAY_PORT}/healthz"
```

A successful response resembles:

```json
{"status": "ok", "version": "0.1.5"}
```

## Troubleshooting

### Sudo or tunnel failure

Use NodePort mode instead:

```bash
SKIP_TUNNEL=1 ./scripts/restart_ml_env.sh
```

### Old `django-*` resources appear

The script removes the Helm release named `django-release`. Check for leftovers:

```bash
kubectl -n ml-workloads get all -o name | grep django- || true
helm -n ml-workloads list
```

### Optional policy CRDs are missing

Kyverno `ClusterPolicy` and Prometheus Operator `PrometheusRule` objects are
optional. The script applies them only when their CRDs are installed; runtime
deployment and health checks do not depend on them.

### Gateway replacement is rejected by Pod Security

The script applies `seccompProfile.type: RuntimeDefault` to the generated Gateway
Deployment before a repair-mode recreation. If the Gateway remains unavailable:

```bash
kubectl -n ml-workloads describe deployment kube-ml-gateway-istio
kubectl -n ml-workloads get events --sort-by=.lastTimestamp
```

This script is intended for the local Minikube reference environment. It is not a
production cluster recovery or deployment tool.
