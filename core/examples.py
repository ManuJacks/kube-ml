"""Shared, read-only examples used by the HTTP API and GUI."""

MAX_ELEMENTS = 1_000_000
EXAMPLES = {
    "basic-vector": {"description": "Calculate an L2 norm and scale a small vector by two.", "payload": {"data": [3.0, 4.0]}},
    "feature-vector": {"description": "Process a four-feature float vector through the tensor bridge.", "payload": {"data": [10.0, 20.0, 30.0, 40.0]}},
    "numpy-stats": {"category": "NumPy", "description": "Compute shape, L2 norm, and scaled output for a NumPy-compatible vector.", "payload": {"data": [1.0, 2.0, 3.0, 4.0]}},
    "numpy-broadcast": {"category": "NumPy", "description": "Demonstrate element-wise broadcasting through a contiguous float32 array.", "payload": {"data": [2.0, 4.0, 6.0]}},
    "numpy-matrix": {"category": "NumPy", "description": "Process a flattened matrix-shaped feature input through the bridge.", "payload": {"data": [1.0, 2.0, 3.0, 4.0]}},
    "torch-reduction": {"category": "PyTorch", "description": "Run a PyTorch tensor reduction and inspect its norm and shape.", "payload": {"data": [3.0, 4.0]}},
    "torch-elementwise": {"category": "PyTorch", "description": "Apply a PyTorch element-wise scale operation with shared NumPy memory.", "payload": {"data": [5.0, 10.0, 15.0]}},
    "torch-features": {"category": "PyTorch", "description": "Process a bounded continuous feature vector with two worker threads.", "payload": {"data": [10.0, 20.0, 30.0, 40.0]}},
}


def example_catalog(version):
    return {"version": version, "max_elements": MAX_ELEMENTS, "examples": EXAMPLES}
