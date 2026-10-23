#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
MOCK_DIR="$(mktemp -d)"
LOG_FILE="$MOCK_DIR/commands.log"
trap 'rm -rf "$MOCK_DIR"' EXIT

cat > "$MOCK_DIR/minikube" <<'EOF'
#!/usr/bin/env bash
printf 'minikube %s\n' "$*" >> "$RESTART_TEST_LOG"
case "${1:-}" in
    status)
        printf 'host: Running\n'
        ;;
    docker-env)
        printf ':\n'
        ;;
    service)
        printf 'http://192.0.2.10:30000\nhttp://192.0.2.10:30443\n'
        ;;
esac
EOF

cat > "$MOCK_DIR/kubectl" <<'EOF'
#!/usr/bin/env bash
printf 'kubectl %s\n' "$*" >> "$RESTART_TEST_LOG"
exit 0
EOF

cat > "$MOCK_DIR/helm" <<'EOF'
#!/usr/bin/env bash
printf 'helm %s\n' "$*" >> "$RESTART_TEST_LOG"
exit 0
EOF

cat > "$MOCK_DIR/docker" <<'EOF'
#!/usr/bin/env bash
printf 'docker %s\n' "$*" >> "$RESTART_TEST_LOG"
exit 0
EOF

chmod +x "$MOCK_DIR"/*

RESTART_TEST_LOG="$LOG_FILE" \
PATH="$MOCK_DIR:$PATH" \
SKIP_START=1 \
SKIP_TUNNEL=1 \
REPAIR_NETWORK=0 \
  "$ROOT_DIR/scripts/restart_ml_env.sh" > "$MOCK_DIR/output.txt"

grep -q 'http://192.0.2.10:30443' "$MOCK_DIR/output.txt"
grep -q 'helm uninstall django-release' "$LOG_FILE"
grep -q 'set image deployment/kube-ml-platform' "$LOG_FILE"
grep -q 'rollout restart deployment/kube-ml-platform' "$LOG_FILE"

if grep -Eq 'docker system prune|rollout restart deployment coredns|scale deployment/kube-ml-gateway-istio|delete pod' "$LOG_FILE"; then
    echo "safe restart mode performed a network-repair action" >&2
    exit 1
fi

echo "restart script safe-mode test passed"
