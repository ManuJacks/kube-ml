# Operations, SLOs, and recovery

This document is the operational contract for a production deployment. Values must be reviewed
with the service owner before being adopted as a formal commitment.

## Initial SLO proposal

- Availability: 99.9% successful readiness over a calendar month.
- API success rate: at least 99.0% of valid requests return 2xx.
- Latency: p95 prediction latency below 500 ms for payloads up to 10,000 elements.
- Recovery: RTO of 30 minutes and RPO of 15 minutes for any future stateful dependency.

Measure these with Prometheus and review error-budget burn weekly. Alert on fast and slow burn,
readiness loss, sustained 5xx responses, OOM kills, HPA saturation, and certificate expiry.

## Incident response

1. Confirm impact using `/healthz`, `/readyz`, metrics, and recent deployment revisions.
2. Stop promotion and roll back to the last known-good immutable image tag.
3. Preserve logs, metrics, and deployment metadata without collecting request payloads or secrets.
4. Record the timeline, customer impact, root cause, corrective actions, and verification evidence.

## Recovery requirements

The application is stateless today. Before adding durable model or tenant data, define encrypted
backups, retention, restore verification, cross-zone recovery, and an exercised disaster-recovery
runbook. A declared RPO/RTO is not complete until a restore drill demonstrates it.
