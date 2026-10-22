# Service mesh & HTTPS ingress

The platform uses **Istio Ambient Mode** and the Kubernetes Gateway API for sidecar-free
service mesh networking with mutual TLS and HTTPS edge termination.

## How it fits together

1. **Ambient mode.** The `ml-workloads` namespace is labeled `istio.io/dataplane-mode=ambient`.
   Traffic flows through shared node-level `ztunnel` proxies instead of per-pod sidecars.
2. **Strict mTLS.** A `PeerAuthentication` with `mode: STRICT` encrypts all east-west
   pod-to-pod traffic.
3. **HTTPS edge gateway.** An Istio Gateway listener on port `443` terminates TLS using the
   secret `django-credential-secret`.

## Accessing HTTPS in Minikube

Minikube has no cloud load balancer, so `LoadBalancer` services show `EXTERNAL-IP: <pending>`
unless routed. Pick one of the methods below to reach the `kube-ml-gateway`.

### Method 1: Gateway NodePort (fastest, no sudo)

The gateway controller (`kube-ml-gateway-istio`) allocates a NodePort for port 443:

```bash
GATEWAY_IP=$(minikube ip)
NODE_PORT=$(kubectl get svc kube-ml-gateway-istio -n ml-workloads \
  -o jsonpath='{.spec.ports[?(@.name=="https")].nodePort}')

echo "Open: https://${GATEWAY_IP}:${NODE_PORT}/"
curl -k https://${GATEWAY_IP}:${NODE_PORT}/     # -k: self-signed certificate
```

Open the printed URL in your browser and accept the self-signed certificate prompt.

### Method 2: Standard port 443 via `minikube tunnel`

```bash
# In a separate terminal
sudo minikube tunnel

# Confirm the gateway receives an EXTERNAL-IP
kubectl get svc kube-ml-gateway-istio -n ml-workloads

curl -k https://<EXTERNAL-IP>/
```

### Method 3: Port-forward

```bash
kubectl port-forward svc/kube-ml-gateway-istio -n ml-workloads 8443:443
```

Then open <https://localhost:8443/>.
