# Deploying to Minikube

Manifests live under [`clusters/minikube/apps/`](../clusters/minikube/apps/). The checked-in
Kustomization is the single authoritative deployment path: it includes the hardened deployment,
namespace security labels, default-deny network policy, service, HPA, and Gateway API resources.

## Prerequisites

- `minikube` installed and running (`minikube status`)
- `kubectl` configured

## 1. Start Minikube and use its Docker daemon

Pointing your Docker CLI at Minikube's daemon makes locally built images visible to the cluster
without an external registry.

```bash
minikube start --driver=docker
eval $(minikube docker-env)
```

## 2. Build the image

```bash
docker build -t kube-ml-app:v1 .
```

## 3. Render and apply

Create the API token out of band before applying the Deployment. Do not commit the generated
Secret manifest:

```bash
export KUBE_ML_API_TOKEN="$(openssl rand -hex 32)"
kubectl -n ml-workloads create secret generic kube-ml-api-token \
  --from-literal=token="$KUBE_ML_API_TOKEN" --dry-run=client -o yaml | kubectl apply -f -
```

```bash
kubectl kustomize clusters/minikube/apps     # inspect the rendered output
kubectl apply -k clusters/minikube/apps
```

Verify the rollout (the workload runs in the `ml-workloads` namespace):

```bash
kubectl -n ml-workloads rollout status deployment/kube-ml-platform
kubectl -n ml-workloads get pods -l app=kube-ml-platform
kubectl -n ml-workloads get svc
```

## 4. Reach the service

```bash
minikube service kube-ml-service -n ml-workloads
# or
kubectl -n ml-workloads port-forward svc/kube-ml-service 8000:8000
```

Then visit <http://localhost:8000/>.

For HTTPS through the Istio gateway, see [Service mesh & HTTPS ingress](service-mesh.md).

## Reference manifests

Rather than duplicating YAML here (where it goes stale), read the source of truth:

| Resource | File |
| --- | --- |
| Deployment | [`deployment.yaml`](../clusters/minikube/apps/deployment.yaml) |
| Service | [`service.yaml`](../clusters/minikube/apps/service.yaml) |
| HorizontalPodAutoscaler | [`hpa.yaml`](../clusters/minikube/apps/hpa.yaml) |
| Network policy, RBAC, PSS | [`hardened-manifest.yaml`](../clusters/minikube/apps/hardened-manifest.yaml) |
| Kustomization | [`kustomization.yaml`](../clusters/minikube/apps/kustomization.yaml) |
