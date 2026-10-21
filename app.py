# app.py
import os
import sys
import numpy as np
from django.conf import settings
from django.core.management import execute_from_command_line
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt

# 1. Inline Django settings configuration (no database required for this ML utility)
if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY="ml-interview-secret-key",
        ROOT_URLCONF=__name__,
        ALLOWED_HOSTS=["*"],
    )

# 2. Web Interface (HTML View)
def home_view(request):
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Django + NumPy ML Portal</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background: #f0f2f5; color: #333; }
            .container { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); max-width: 600px; margin: auto; }
            h2 { color: #092e20; border-bottom: 2px solid #417690; padding-bottom: 10px; }
            input { padding: 12px; width: 75%; margin-right: 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 16px; }
            button { padding: 12px 24px; background: #417690; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; font-weight: bold; }
            button:hover { background: #092e20; }
            #result { margin-top: 25px; padding: 15px; background: #e8f4f8; border-left: 5px solid #417690; border-radius: 4px; display: none; line-height: 1.6; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Django & NumPy Array Processing Portal</h2>
            <p>Enter continuous features as a vector (comma-separated numbers):</p>
            <input type="text" id="arrayInput" value="10, 20, 30, 40">
            <button onclick="calculateMatrix()">Execute NumPy</button>
            <div id="result"></div>
        </div>

        <script>
            async function calculateMatrix() {
                const input = document.getElementById('arrayInput').value;
                const dataArray = input.split(',').map(Number);
                
                const response = await fetch('/predict', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ data: dataArray })
                });
                const result = await response.json();
                
                const resultDiv = document.getElementById('result');
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = `
                    <strong>Original Vector:</strong> [${result.original}]<br>
                    <strong>Matrix Shape:</strong> ${result.shape}<br>
                    <strong>L2 Norm (Magnitude):</strong> ${result.l2_norm}<br>
                    <strong>NumPy Scaled Result (x2):</strong> [${result.numpy_processed}]
                `;
            }
        </script>
    </body>
    </html>
    """
    return HttpResponse(html_content)

# 3. NumPy ML Processing Endpoint
@csrf_exempt
def predict_view(request):
    if request.method == 'POST':
        import json
        payload = json.loads(request.body)
        raw_data = payload.get('data', [])
        
        # Core NumPy Operations
        np_vector = np.array(raw_data, dtype=float)
        vector_shape = str(np_vector.shape)
        l2_norm = round(float(np.linalg.norm(np_vector)), 3) # Computes array magnitude
        scaled_result = np.dot(np_vector, 2).tolist()        # Linear scaling via dot product
        
        return JsonResponse({
            "original": raw_data,
            "shape": vector_shape,
            "l2_norm": l2_norm,
            "numpy_processed": scaled_result
        })
    return JsonResponse({"error": "Only POST requests allowed"}, status=400)

# 4. Django URL Routing
from django.urls import path
urlpatterns = [
    path('', home_view),
    path('predict', predict_view),
]
if __name__ == '__main__':
    # Build a clean flat argument array to override Kubernetes runtime flags
    args = [sys.argv[0], "runserver", "0.0.0.0:5000"]
    execute_from_command_line(args)

