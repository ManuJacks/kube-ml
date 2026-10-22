import json
import logging
import numpy as np
import torch
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from django.core.exceptions import RequestDataTooBig
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed
from django.shortcuts import render
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from .examples import EXAMPLES, example_catalog
from .auth import require_api_token

logger = logging.getLogger(__name__)

# Enforce thread constraint to prevent CPU thrashing in containerized environments
torch.set_num_threads(2)

# Strict payload size validation to prevent out-of-memory cascades
MAX_ELEMENTS = 1_000_000
PREDICTIONS = Counter("kube_ml_predictions_total", "Prediction requests", ["status"])
PREDICTION_LATENCY = Histogram("kube_ml_prediction_duration_seconds", "Prediction latency")


def tensor_gui_view(request):
    """Renders the interactive HTML portal for tensor calculations."""
    return render(request, "core/tensor_gui.html", {"app_version": settings.APP_VERSION})


def health_view(request):
    """Liveness endpoint: the process is alive if Django can answer."""
    return JsonResponse({"status": "ok", "version": settings.APP_VERSION})


def ready_view(request):
    """Readiness endpoint for load balancers and Kubernetes probes."""
    return JsonResponse({"status": "ready", "version": settings.APP_VERSION})


@require_api_token
def metrics_view(request):
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)


@require_api_token
def examples_view(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    return JsonResponse(example_catalog(settings.APP_VERSION))


@require_api_token
def example_view(request, name):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    example = EXAMPLES.get(name)
    if example is None:
        return JsonResponse({"error": "Unknown example"}, status=404)
    return JsonResponse({"name": name, **example})


@csrf_exempt
@require_api_token
@PREDICTION_LATENCY.time()
def predict_view(request):
    """
    Zero-copy tensor bridge endpoint:
    - Parses vector features.
    - Validates payload size (<= MAX_ELEMENTS).
    - Bridges contiguous NumPy float32 array into PyTorch without data copying.
    - Computes L2 norm and scalar multiplication.
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        payload = json.loads(request.body)
    except RequestDataTooBig:
        return HttpResponseBadRequest(
            json.dumps({"error": f"Payload exceeds maximum allowed memory size (MAX_ELEMENTS limit: {MAX_ELEMENTS})"}),
            content_type="application/json"
        )
    except (json.JSONDecodeError, UnicodeDecodeError):
        return HttpResponseBadRequest(json.dumps({"error": "Invalid JSON payload"}), content_type="application/json")

    raw_data = payload.get("data") if isinstance(payload, dict) else None
    if raw_data is None or not isinstance(raw_data, list):
        return HttpResponseBadRequest(
            json.dumps({"error": "Field 'data' must be a list of numbers"}),
            content_type="application/json"
        )

    num_elements = len(raw_data)
    if num_elements == 0:
        return HttpResponseBadRequest(
            json.dumps({"error": "Payload array cannot be empty"}),
            content_type="application/json"
        )

    if num_elements > MAX_ELEMENTS:
        return HttpResponseBadRequest(
            json.dumps({"error": f"Payload exceeds MAX_ELEMENTS limit ({MAX_ELEMENTS})"}),
            content_type="application/json"
        )

    if any(not isinstance(value, (int, float)) or not np.isfinite(value) for value in raw_data):
        PREDICTIONS.labels("invalid").inc()
        return HttpResponseBadRequest(json.dumps({"error": "data must contain finite numbers only"}), content_type="application/json")

    try:
        # Zero-copy bridge requires C-contiguous float32 array
        np_vector = np.ascontiguousarray(raw_data, dtype=np.float32)
        tensor = torch.from_numpy(np_vector)

        # Confirm zero-copy guarantee
        is_zero_copy = np.shares_memory(np_vector, tensor.numpy())

        # Computations via PyTorch / NumPy
        l2_norm = round(float(torch.linalg.norm(tensor).item()), 3)
        scaled_result = (tensor * 2.0).tolist()

        PREDICTIONS.labels("success").inc()
        return JsonResponse({
            "original": raw_data,
            "shape": str(np_vector.shape),
            "l2_norm": l2_norm,
            "numpy_processed": scaled_result,
            "zero_copy": is_zero_copy,
            "threads": torch.get_num_threads()
        })
    except (TypeError, ValueError, OverflowError):
        PREDICTIONS.labels("invalid").inc()
        return HttpResponseBadRequest(json.dumps({"error": "data contains unsupported numeric values"}), content_type="application/json")
    except Exception:
        PREDICTIONS.labels("error").inc()
        logger.exception("Unexpected tensor processing failure")
        return JsonResponse({"error": "Internal tensor processing error"}, status=500)
