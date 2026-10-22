# Local development

## Prerequisites

- Python 3.10+
- `pip` and `python3-venv`

## Setup

```bash
# Using the Makefile
make venv
make install

# Or manually
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

> **Tip:** for a faster, CPU-only PyTorch install:
> `pip install torch --index-url https://download.pytorch.org/whl/cpu`

## Run the tests

```bash
python manage.py test core    # or: make test
```

The suite verifies:

- Zero-copy buffer integrity (`np.shares_memory`).
- CPU thread constraint (`torch.get_num_threads() == 2`).
- Payload boundaries (`MAX_ELEMENTS = 1,000,000` and `DATA_UPLOAD_MAX_MEMORY_SIZE`).
- Error handling: empty payloads, non-list structures, invalid JSON.
- HTML portal rendering.
- Liveness, readiness, metrics, and rejection of non-finite numbers.

## Run the dev server

Protected endpoints require a bearer token (see [Authentication](authentication.md)). Create
`.env.local` (ignored by Git) before starting:

```bash
export KUBE_ML_API_TOKEN="$(openssl rand -hex 32)"
printf 'KUBE_ML_API_TOKEN=%s\n' "$KUBE_ML_API_TOKEN" > .env.local

make run-dev    # or: python manage.py runserver 0.0.0.0:8000
```

- **Web UI:** <http://localhost:8000/>. Paste the token into the password field.
- **API:**

  ```bash
  curl -X POST http://localhost:8000/predict \
    -H "Authorization: Bearer $KUBE_ML_API_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"data": [10.0, 20.0, 30.0, 40.0]}'
  ```

The Django development server is for local iteration only. For a production-like local run,
build the image and use its Gunicorn entrypoint.

## Endpoints

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/healthz` | no | Liveness; response includes the app version |
| `GET` | `/readyz` | no | Readiness |
| `GET` | `/metrics` | yes | Prometheus exposition format |
| `POST` | `/predict` | yes | Tensor computation |
| `GET` | `/api/v1/examples` | yes | List deterministic examples and limits |
| `GET` | `/api/v1/examples/basic-vector` | yes | Retrieve a safe example payload |

The OpenAPI 3.1 contract lives in [`openapi.yaml`](openapi.yaml).

## MCP server

The `numpy-mcp-server` stdio command exposes the same eighteen read-only examples through
`tools/list`, `run_example`, and `run_tensor_example`. It requires the `KUBE_ML_API_TOKEN`
environment variable and a `token` argument on every `tools/call`.
