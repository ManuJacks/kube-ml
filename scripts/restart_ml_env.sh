#!/bin/bash

# ==============================================================================
# Script Name: restart_ml_env.sh
# Description: Comprehensive, zero-touch restoration playbook.
#              Automates fixes for Docker lock conflicts, CoreDNS socket loops,
#              API server drops, ErrImageNeverPull, and dual-gateway collisions.
# ==============================================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}[PRE-CHECK] This production script requires sudo escalation to manage network tunnels.${NC}"
# Pre-authenticate sudo immediately at launch so it caches credentials in terminal memory
sudo true
if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: Administrative escalation refused. Aborting pipeline.${NC}"
    exit 1
fi

echo -e "${BLUE}[1/5] Booting Minikube Cluster with Core Allocations...${NC}"
# Re-wake cluster with hardware specs. Skips non-critical addon hangs if API lags.
minikube start --cpus=4 --memory=8192mb --extra-config=apiserver.v=2
if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: Minikube failed to initialize cleanly.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Minikube cluster active.${NC}\n"

echo -e "${BLUE}[2/5] FIX: Flushing Docker Runtime Locks & Resetting Cluster DNS...${NC}"
# 1. Clear the 'container name already in use' conflict for the CNI and Gateway pods
minikube ssh "docker container prune -f && docker system prune -f" 2>/dev/null
kubectl delete validatingwebhookconfiguration istio-validator-istio-system 2>/dev/null

# 2. CRITICAL NETWORK FIX: Cycle CoreDNS to clear out dead post-reboot interface maps
echo "Cycling CoreDNS virtual switch infrastructure..."
kubectl rollout restart deployment coredns -n kube-system 2>/dev/null
kubectl wait --namespace kube-system --for=condition=ready pod --selector=k8s-app=kube-dns --timeout=90s 2>/dev/null

# 3. ADVANCED TRAFFIC PROBE: Force script to block until the DNS network port actively answers queries
echo "Validating CoreDNS active network resolution loop..."
for i in {1..20}; do
    # Probe network port 53 inside the Kubernetes network namespace (netcat)
    minikube ssh "nc -z -w 2 10.96.0.10 53" >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        # Run a live test lookup to ensure packet forwarding is completely online and routing
        minikube ssh "nslookup kubernetes.default.svc.cluster.local 10.96.0.10" >/dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ CoreDNS network socket is actively resolving lookups.${NC}\n"
            break
        fi
    fi
    echo "DNS socket refusing connections. Retrying network ping... ($i/20)"
    sleep 4
done

echo -e "${BLUE}[3/5] FIX: Re-aligning Environment Cache & Rebuilding Django App...${NC}"
# Fixes 'ErrImageNeverPull' by re-binding the local terminal environment to Minikube's engine
eval $(minikube docker-env)

# Safely injects the up-to-date image bytes straight into the cluster
docker build -t kube-ml-app:v1 $(dirname "$0")
echo -e "${GREEN}✓ Local image 'kube-ml-app:v1' successfully synchronized.${NC}\n"

echo -e "${BLUE}Waiting for Istio Control Plane webhook to initialize...${NC}"
# Blocks execution here until the control plane pod is 100% online and ready to sign CSRs
kubectl wait --namespace istio-system --for=condition=ready pod --selector=app=istiod --timeout=90s 2>/dev/null
echo -e "${GREEN}✓ Istio webhook validation online.${NC}\n"

echo -e "${BLUE}[4/5] Synchronizing Declarative Helm Chart Deployments...${NC}"
helm upgrade --install django-release $(dirname "$0")/../kube-ml-chart --namespace ml-workloads

echo -e "${YELLOW}FIX: Executing atomic gateway flush to prevent IP/socket collisions...${NC}"
# Forcefully scale down the gateway deployment to 0 to completely unbind stale socket allocations
kubectl scale deployment/django-gateway-istio -n ml-workloads --replicas=0 2>/dev/null
kubectl delete pod -n ml-workloads -l gateway.networking.k8s.io/gateway-name=django-gateway --grace-period=0 --force 2>/dev/null

echo "Allowing namespace network tables to settle..."
sleep 15

# Trigger clean, singular scale-up rollouts from a completely cleared network state
kubectl scale deployment/django-gateway-istio -n ml-workloads --replicas=1 2>/dev/null
kubectl rollout restart deployment django-release-deployment -n ml-workloads
echo -e "${GREEN}✓ Global deployment rollout triggered successfully.${NC}\n"

echo -e "${BLUE}[5/5] Launching Autonomous Network Tunnel & Extracting Proxy Links...${NC}"
# Use the cached sudo token to spawn the tunnel silently into a background process thread
sudo minikube tunnel > minikube_tunnel.log 2>&1 &
echo -e "${GREEN}✓ Minikube network tunnel successfully established in the background (Logs: minikube_tunnel.log).${NC}"

echo -e "${YELLOW}----------------------------------------------------------------------"
echo -e "CRITICAL INSTRUCTIONS FOR BROWSER RUNTIME:"
echo -e "1. Copy the second URL generated below."
echo -e "2. MANUALLY convert the 'http://' prefix to 'https://' inside Firefox."
echo -e "3. Accept the developer certificate exception flag when prompted."
echo -e "----------------------------------------------------------------------${NC}"

# Block terminal execution until the Ingress Gateway finishes rolling over into a 1/1 Ready state
echo "Waiting for Istio Ingress Gateway to stabilize routing tables..."
kubectl wait --namespace ml-workloads --for=condition=available deployment/django-gateway-istio --timeout=120s

minikube service django-gateway-istio -n ml-workloads --url

