"""Shared, read-only examples used by the HTTP API and GUI."""

MAX_ELEMENTS = 1_000_000
EXAMPLES = {
    "basic-vector": {"description": "Calculate an L2 norm and scale a small vector by two.", "payload": {"data": [3.0, 4.0]}},
    "feature-vector": {"description": "Process a four-feature float vector through the tensor bridge.", "payload": {"data": [10.0, 20.0, 30.0, 40.0]}},
    "numpy-stats": {"category": "NumPy", "description": "Compute shape, L2 norm, and scaled output for a NumPy-compatible vector.", "payload": {"data": [1.0, 2.0, 3.0, 4.0]}},
    "numpy-broadcast": {"category": "NumPy", "description": "Demonstrate element-wise broadcasting through a contiguous float32 array.", "payload": {"data": [2.0, 4.0, 6.0]}},
    "numpy-matrix": {"category": "NumPy", "description": "Process a flattened matrix-shaped feature input through the bridge.", "payload": {"data": [1.0, 2.0, 3.0, 4.0]}},
    "numpy-negative": {"category": "NumPy", "description": "Process signed values and preserve numerical stability across zero.", "payload": {"data": [-3.0, -1.0, 0.0, 2.0]}},
    "numpy-batch": {"category": "NumPy", "description": "Process a larger bounded feature batch with contiguous float32 conversion.", "payload": {"data": [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]}},
    "numpy-sparse-like": {"category": "NumPy", "description": "Process a sparse-like vector containing mostly zero-valued features.", "payload": {"data": [0.0, 0.0, 7.0, 0.0, 0.0, 2.0]}},
    "numpy-timeseries": {"category": "NumPy", "description": "Process an ordered time-series window of sensor readings.", "payload": {"data": [12.1, 12.4, 12.2, 12.8, 13.0, 12.7]}},
    "numpy-pixels": {"category": "NumPy", "description": "Process normalized pixel-like channel values in a bounded vector.", "payload": {"data": [0.0, 0.25, 0.5, 0.75, 1.0, 0.5]}},
    "numpy-normalization": {"category": "NumPy", "description": "Process normalized feature values ready for model input.", "payload": {"data": [0.12, 0.38, 0.64, 0.91]}},
    "torch-reduction": {"category": "PyTorch", "description": "Run a PyTorch tensor reduction and inspect its norm and shape.", "payload": {"data": [3.0, 4.0]}},
    "torch-elementwise": {"category": "PyTorch", "description": "Apply a PyTorch element-wise scale operation with shared NumPy memory.", "payload": {"data": [5.0, 10.0, 15.0]}},
    "torch-features": {"category": "PyTorch", "description": "Process a bounded continuous feature vector with two worker threads.", "payload": {"data": [10.0, 20.0, 30.0, 40.0]}},
    "torch-negative": {"category": "PyTorch", "description": "Run tensor reduction over signed values and zero-crossing features.", "payload": {"data": [-5.0, -2.0, 1.0, 4.0]}},
    "torch-batch": {"category": "PyTorch", "description": "Run a bounded six-value tensor batch through the worker-limited bridge.", "payload": {"data": [0.25, 0.5, 0.75, 1.0, 1.25, 1.5]}},
    "torch-sparse-like": {"category": "PyTorch", "description": "Run a tensor with sparse-like zero-valued features and two active values.", "payload": {"data": [0.0, 0.0, 8.0, 0.0, 3.0, 0.0]}},
    "torch-batched": {"category": "PyTorch", "description": "Run a small batched-inference style feature window.", "payload": {"data": [2.0, 4.0, 6.0, 8.0, 10.0, 12.0]}},
    "torch-logits": {"category": "PyTorch", "description": "Process bounded logits-like values before downstream scoring.", "payload": {"data": [-2.0, -0.5, 0.5, 2.0]}},
    "torch-embedding": {"category": "PyTorch", "description": "Process a compact embedding-like vector with shared memory.", "payload": {"data": [0.11, -0.24, 0.53, 0.72, -0.08, 0.31]}},
}


def example_catalog(version):
    return {"version": version, "max_elements": MAX_ELEMENTS, "examples": EXAMPLES}
