# GitOps & delivery pipeline

Delivery is fully declarative: GitHub Actions builds, scans, signs, and promotes an immutable
image; [Flux CD](https://fluxcd.io) reconciles the result into the cluster.

## Layout

- `clusters/minikube/apps/kustomization.yaml`: the hardened deployment, service, HPA, Gateway API,
  and network/security manifests.
- `clusters/minikube/flux-system/gotk-sync.yaml`:
  - `GitRepository` watching `https://github.com/ManuJacks/kube-ml.git` on `development`,
    polling every minute.
  - `Kustomization` reconciling `./clusters/minikube/apps` into `ml-workloads` with automated
    pruning.

## Bootstrapping Flux on Minikube

```bash
flux install                                        # 1. install Flux
kubectl apply -k clusters/minikube/flux-system/     # 2. apply the sync manifests
flux get sources git                                # 3. verify
flux get kustomizations
flux reconcile kustomization kube-ml-apps --with-source   # 4. force a reconcile
```

## Automated image promotion

On every push to `development`, GitHub Actions:

1. Builds and publishes a commit-tagged image to GHCR.
2. Scans the published image with Trivy.
3. Produces an SPDX SBOM and signs the image with keyless Cosign using GitHub OIDC.
4. Updates the Kustomize and Helm image references to the immutable commit tag.
5. Commits that promotion back to `development`.
6. Lets Flux reconcile the changed manifests into the cluster.

Promotion is repeatable: each successful push replaces the previously promoted tag. The
promotion commit is marked `[skip ci]` so it doesn't trigger another image build, while Flux
still observes the commit normally.

> **Signature enforcement:** signing alone is not a boundary. A cluster admission policy
> (Kyverno or OPA Gatekeeper) must verify the Cosign signature before this becomes an enforced
> supply-chain control.

Other CI safeguards: automated tests, Ruff linting, Helm/Kustomize rendering, and `pip-audit`
dependency auditing.

## Pull access to GHCR

The GHCR package must be readable by the target cluster. For a private package, configure an
`imagePullSecret` through your secret-management system and never commit registry credentials.
Flux controllers must already be installed and authorized to reconcile the repository.

## After pushing a change

**Local development:** no image wait is needed.

```bash
git pull origin development
make run-dev
```

**Minikube + Flux:** wait for the workflow, then verify promotion and reconciliation.

```bash
gh run list --workflow ci.yml --limit 1
flux get kustomizations
flux reconcile source git kube-ml -n flux-system
flux reconcile kustomization kube-ml-apps -n flux-system --with-source
kubectl -n ml-workloads rollout status deployment/kube-ml-platform
kubectl -n ml-workloads get pods -o wide
```

The cluster updates only when **all** of these hold: the image was published to GHCR, the
manifests were promoted to the new commit tag, Flux is healthy, and the cluster can pull the
image. Confirm the deployed version with:

```bash
curl http://<service-or-gateway>/healthz
```

The response includes the application version; the GUI shows it as `v<version>`.
