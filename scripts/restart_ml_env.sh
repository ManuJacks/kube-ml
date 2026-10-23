#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
NAMESPACE="ml-workloads"
APP_DEPLOYMENT="kube-ml-platform"
GATEWAY_DEPLOYMENT="kube-ml-gateway-istio"
LOCAL_IMAGE="kube-ml-app:v1"
SKIP_TUNNEL="${SKIP_TUNNEL:-1}"
SKIP_START="${SKIP_START:-0}"
REPAIR_NETWORK="${REPAIR_NETWORK:-0}"

# ==============================================================================
# Script Name: restart_ml_env.sh
# Description: Repeatable Minikube application restart and validation.
#              Set REPAIR_NETWORK=1 only for exceptional Docker/CoreDNS/Gateway
#              recovery. Set SKIP_TUNNEL=0 when a sudo-managed tunnel is needed.
# ==============================================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

if [ "$SKIP_TUNNEL" = "1" ]; then
    echo -e "${YELLOW}[PRE-CHECK] SKIP_TUNNEL=1: running without sudo; NodePort validation will be used.${NC}"
else
    echo -e "${YELLOW}[PRE-CHECK] This production script requires sudo escalation to manage network tunnels.${NC}"
    # Pre-authenticate sudo immediately at launch so it caches credentials in terminal memory
    sudo true
    if [ $? -ne 0 ]; then
        echo -e "${RED}ERROR: Administrative escalation refused. Set SKIP_TUNNEL=1 to use NodePort validation.${NC}"
        exit 1
    fi
fi

echo -e "${BLUE}[1/5] Booting Minikube Cluster with Core Allocations...${NC}"
# Re-wake cluster with hardware specs. Skips non-critical addon hangs if API lags.
if [ "$SKIP_START" = "1" ]; then
    minikube status
else
    minikube start --cpus=4 --memory=8192mb --extra-config=apiserver.v=2
    if [ $? -ne 0 ]; then
        echo -e "${RED}ERROR: Minikube failed to initialize cleanly.${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✓ Minikube cluster active.${NC}\n"

if [ "$REPAIR_NETWORK" = "1" ]; then
    echo -e "${BLUE}[2/5] REPAIR: Flushing Docker Runtime Locks & Resetting Cluster DNS...${NC}"
    # 1. Clear the 'container name already in use' conflict for the CNI and Gateway pods
    minikube ssh "docker container prune -f && docker system prune -f" 2>/dev/null
    kubectl delete validatingwebhookconfiguration istio-validator-istio-system 2>/dev/null || true

    # 2. Cycle CoreDNS to clear out dead post-reboot interface maps
    echo "Cycling CoreDNS virtual switch infrastructure..."
    kubectl rollout restart deployment coredns -n kube-system 2>/dev/null
    kubectl wait --namespace kube-system --for=condition=ready pod --selector=k8s-app=kube-dns --timeout=90s 2>/dev/null

    # 3. Wait until the DNS service has port 53 endpoints. Querying the API
    # avoids a hanging `minikube ssh` session during node recovery.
    echo "Validating CoreDNS service endpoints..."
    for i in {1..20}; do
        if kubectl get endpoints kube-dns --namespace kube-system \
            -o jsonpath='{.subsets[*].ports[*].port}' 2>/dev/null | grep -qw 53; then
            echo -e "${GREEN}✓ CoreDNS service has active DNS endpoints.${NC}\n"
            break
        fi
        echo "CoreDNS service has no port 53 endpoint. Retrying... ($i/20)"
        sleep 4
    done
else
    echo -e "${BLUE}[2/5] Skipping network repair (set REPAIR_NETWORK=1 for recovery mode).${NC}"
fi

echo -e "${BLUE}[3/5] FIX: Re-aligning Environment Cache & Rebuilding Django App...${NC}"
# Fixes 'ErrImageNeverPull' by re-binding the local terminal environment to Minikube's engine
eval $(minikube docker-env)

# Safely injects the up-to-date image bytes straight into the cluster.
# The Dockerfile is at the repository root, not in scripts/.
docker build -t "$LOCAL_IMAGE" "$REPO_ROOT"
echo -e "${GREEN}✓ Local image 'kube-ml-app:v1' successfully synchronized.${NC}\n"

echo -e "${BLUE}Waiting for Istio Control Plane webhook to initialize...${NC}"
# Blocks execution here until the control plane pod is 100% online and ready to sign CSRs
kubectl wait --namespace istio-system --for=condition=ready pod --selector=app=istiod --timeout=90s 2>/dev/null
echo -e "${GREEN}✓ Istio webhook validation online.${NC}\n"

echo -e "${BLUE}[4/5] Synchronizing Declarative Kubernetes Deployments...${NC}"
# Remove the obsolete Helm release so its old django-* Gateway and Deployment do
# not compete with the current kube-ml-* resources.
helm uninstall django-release --namespace "$NAMESPACE" --ignore-not-found
# Apply the runtime resources from the repository's authoritative Minikube path.
# The bundle also contains optional Kyverno/Prometheus resources; those CRDs are
# not required for a restart and are not installed in every Minikube profile.
APP_MANIFEST_DIR="$REPO_ROOT/clusters/minikube/apps"
kubectl apply -f "$APP_MANIFEST_DIR/hardened-manifest.yaml"
kubectl apply --namespace "$NAMESPACE" -f "$APP_MANIFEST_DIR/service.yaml"
kubectl apply -f "$APP_MANIFEST_DIR/hpa.yaml" \
    -f "$APP_MANIFEST_DIR/gateway.yaml" \
    -f "$APP_MANIFEST_DIR/httproute.yaml"
if kubectl api-resources --api-group=kyverno.io 2>/dev/null | grep -q ClusterPolicy \
    && kubectl api-resources --api-group=monitoring.coreos.com 2>/dev/null | grep -q PrometheusRule; then
    kubectl apply -f "$APP_MANIFEST_DIR/policies.yaml"
else
    echo -e "${YELLOW}Optional Kyverno/Prometheus CRDs unavailable; skipping policy resources.${NC}"
fi
# The Minikube trial uses the image built above rather than the registry image in
# the production-oriented manifest.
kubectl -n "$NAMESPACE" set image "deployment/$APP_DEPLOYMENT" "kube-ml-app=$LOCAL_IMAGE"
kubectl -n "$NAMESPACE" rollout status "deployment/$APP_DEPLOYMENT" --timeout=120s

if [ "$REPAIR_NETWORK" = "1" ]; then
    echo -e "${YELLOW}REPAIR: Executing atomic gateway flush to prevent IP/socket collisions...${NC}"
    # Istio's generated gateway pod must satisfy the namespace's restricted Pod
    # Security profile before it is recreated.
    kubectl patch "deployment/$GATEWAY_DEPLOYMENT" -n "$NAMESPACE" --type=merge \
        -p '{"spec":{"template":{"spec":{"securityContext":{"seccompProfile":{"type":"RuntimeDefault"}}}}}}' \
        2>/dev/null || true
    kubectl scale "deployment/$GATEWAY_DEPLOYMENT" -n "$NAMESPACE" --replicas=0 2>/dev/null || true
    kubectl delete pod -n "$NAMESPACE" -l gateway.networking.k8s.io/gateway-name=kube-ml-gateway --grace-period=0 --force 2>/dev/null || true
    echo "Allowing namespace network tables to settle..."
    sleep 15
    kubectl scale "deployment/$GATEWAY_DEPLOYMENT" -n "$NAMESPACE" --replicas=1 2>/dev/null || true
else
    echo -e "${BLUE}Leaving the healthy Gateway untouched (set REPAIR_NETWORK=1 for recovery mode).${NC}"
fi
kubectl rollout restart "deployment/$APP_DEPLOYMENT" -n "$NAMESPACE"
echo -e "${GREEN}✓ Global deployment rollout triggered successfully.${NC}\n"

echo -e "${BLUE}[5/5] Extracting Proxy Links...${NC}"
if [ "$SKIP_TUNNEL" = "1" ]; then
    echo -e "${YELLOW}Skipping minikube tunnel; validating the Gateway NodePort instead.${NC}"
else
    # Use the cached sudo token to spawn the tunnel silently into a background process thread
    sudo minikube tunnel > "$SCRIPT_DIR/minikube_tunnel.log" 2>&1 &
    echo -e "${GREEN}✓ Minikube network tunnel successfully established in the background (Logs: $SCRIPT_DIR/minikube_tunnel.log).${NC}"
fi

echo -e "${YELLOW}----------------------------------------------------------------------"
echo -e "CRITICAL INSTRUCTIONS FOR BROWSER RUNTIME:"
echo -e "1. Copy the second URL generated below."
echo -e "2. MANUALLY convert the 'http://' prefix to 'https://' inside Firefox."
echo -e "3. Accept the developer certificate exception flag when prompted."
echo -e "----------------------------------------------------------------------${NC}"

# Block terminal execution until the Ingress Gateway finishes rolling over into a 1/1 Ready state
echo "Waiting for Istio Ingress Gateway to stabilize routing tables..."
kubectl wait --namespace "$NAMESPACE" --for=condition=available "deployment/$GATEWAY_DEPLOYMENT" --timeout=120s

minikube service "$GATEWAY_DEPLOYMENT" -n "$NAMESPACE" --url

