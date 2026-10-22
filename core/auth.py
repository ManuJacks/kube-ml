import hmac
from functools import wraps

from django.conf import settings
from django.http import JsonResponse


def require_api_token(view):
    """Require a constant-time checked Bearer token for protected endpoints."""
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        configured = getattr(settings, "KUBE_ML_API_TOKEN", "")
        scheme, _, supplied = request.headers.get("Authorization", "").partition(" ")
        if not configured or scheme.lower() != "bearer" or not hmac.compare_digest(supplied, configured):
            response = JsonResponse({"error": "Valid Bearer token required"}, status=401)
            response["WWW-Authenticate"] = "Bearer"
            return response
        return view(request, *args, **kwargs)
    return wrapped
