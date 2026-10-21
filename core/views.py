import json
import logging
import numpy as np
import torch
from django.core.exceptions import RequestDataTooBig
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotAllowed
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

# Enforce thread constraint to prevent CPU thrashing in containerized environments
torch.set_num_threads(2)

# Strict payload size validation to prevent out-of-memory cascades
MAX_ELEMENTS = 1_000_000


def tensor_gui_view(request):
    """Renders the interactive HTML portal for tensor calculations."""
    return render(request, "core/tensor_gui.html")


@csrf_exempt
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

    raw_data = payload.get("data")
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

    try:
        # Zero-copy bridge requires C-contiguous float32 array
        np_vector = np.ascontiguousarray(raw_data, dtype=np.float32)
        tensor = torch.from_numpy(np_vector)

        # Confirm zero-copy guarantee
        is_zero_copy = np.shares_memory(np_vector, tensor.numpy())

        # Computations via PyTorch / NumPy
        l2_norm = round(float(torch.linalg.norm(tensor).item()), 3)
        scaled_result = (tensor * 2.0).tolist()

        return JsonResponse({
            "original": raw_data,
            "shape": str(np_vector.shape),
            "l2_norm": l2_norm,
            "numpy_processed": scaled_result,
            "zero_copy": is_zero_copy,
            "threads": torch.get_num_threads()
        })
    except Exception as exc:
        logger.exception("Error processing tensor vector: %s", exc)
        return JsonResponse({"error": f"Internal tensor processing error: {str(exc)}"}, status=500)
