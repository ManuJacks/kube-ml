# Authentication

Protected endpoints (`/predict`, `/metrics`, `/api/v1/examples`) require an
`Authorization: Bearer <token>` header. `/healthz` and `/readyz` stay unauthenticated so
Kubernetes probes keep working. The GUI accepts the token in its password field and keeps it
only in the current browser tab.

This is a single shared bearer token. Per-user identity, scopes, tenant boundaries, and rate
limiting are on the [roadmap](roadmap.md); add them (or gateway-enforced OIDC/JWT) before
exposing `/predict` outside a trusted boundary.

## Local development

Generate a strong token rather than a short human-readable one:

```bash
export KUBE_ML_API_TOKEN="$(openssl rand -hex 32)"
printf 'KUBE_ML_API_TOKEN=%s\n' "$KUBE_ML_API_TOKEN" > .env.local   # ignored by Git
make run-dev
```

Call a protected endpoint:

```bash
curl -H "Authorization: Bearer $KUBE_ML_API_TOKEN" \
  http://localhost:8000/api/v1/examples

curl -X POST -H "Authorization: Bearer $KUBE_ML_API_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"data":[3,4]}' http://localhost:8000/predict
```

## Kubernetes

Create the expected Secret out of band:

```bash
kubectl -n ml-workloads create secret generic kube-ml-api-token \
  --from-literal=token="$KUBE_ML_API_TOKEN" --dry-run=client -o yaml | kubectl apply -f -
```

## MCP server

The stdio server requires the same `KUBE_ML_API_TOKEN` environment variable plus a `token`
argument on every `tools/call`.

## Rotating the token

Create a new token, update the Secret, and restart the deployment. Existing clients get `401`
until they are updated.

```bash
export NEW_KUBE_ML_API_TOKEN="$(openssl rand -hex 32)"
kubectl -n ml-workloads create secret generic kube-ml-api-token \
  --from-literal=token="$NEW_KUBE_ML_API_TOKEN" --dry-run=client -o yaml | kubectl apply -f -
kubectl -n ml-workloads rollout restart deployment/kube-ml-platform
kubectl -n ml-workloads rollout status deployment/kube-ml-platform
```

## Rules

Never commit tokens, `.env.local`, or rendered Secret manifests. Keep the token out of
Deployment manifests, Helm values, shell history, issues, and logs.

## Troubleshooting `401`

- Check the header spelling (`Authorization: Bearer <token>`).
- Confirm the application has the current Secret (restart after rotation).
- Confirm the client uses the same token as the running deployment.
