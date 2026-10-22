"""Read-only MCP stdio server for deterministic platform examples."""
import json
import sys

import numpy as np
import torch

VERSION = "0.1.4"
TOOLS = [
    {"name": "list_examples", "description": "List deterministic tensor examples.", "inputSchema": {"type": "object"}},
    {"name": "run_example", "description": "Execute one named NumPy or PyTorch example.", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "run_tensor_example", "description": "Run a bounded tensor example.", "inputSchema": {"type": "object", "properties": {"data": {"type": "array", "items": {"type": "number"}}}, "required": ["data"]}},
    {"name": "get_platform_metadata", "description": "Get version and safety limits.", "inputSchema": {"type": "object"}},
]


def _result(value):
    return {"content": [{"type": "text", "text": json.dumps(value)}]}


def call_tool(name, arguments):
    examples = {"numpy-stats": [1.0, 2.0, 3.0, 4.0], "numpy-broadcast": [2.0, 4.0, 6.0], "numpy-matrix": [1.0, 2.0, 3.0, 4.0], "numpy-negative": [-3.0, -1.0, 0.0, 2.0], "numpy-batch": [0.5, 1.5, 2.5, 3.5, 4.5, 5.5], "numpy-sparse-like": [0.0, 0.0, 7.0, 0.0, 0.0, 2.0], "numpy-timeseries": [12.1, 12.4, 12.2, 12.8, 13.0, 12.7], "numpy-pixels": [0.0, 0.25, 0.5, 0.75, 1.0, 0.5], "numpy-normalization": [0.12, 0.38, 0.64, 0.91], "torch-reduction": [3.0, 4.0], "torch-elementwise": [5.0, 10.0, 15.0], "torch-features": [10.0, 20.0, 30.0, 40.0], "torch-negative": [-5.0, -2.0, 1.0, 4.0], "torch-batch": [0.25, 0.5, 0.75, 1.0, 1.25, 1.5], "torch-sparse-like": [0.0, 0.0, 8.0, 0.0, 3.0, 0.0], "torch-batched": [2.0, 4.0, 6.0, 8.0, 10.0, 12.0], "torch-logits": [-2.0, -0.5, 0.5, 2.0], "torch-embedding": [0.11, -0.24, 0.53, 0.72, -0.08, 0.31]}
    if name == "list_examples":
        return _result({"version": VERSION, "examples": examples})
    if name == "run_example":
        example_name = arguments.get("name") if isinstance(arguments, dict) else None
        if example_name not in examples:
            raise ValueError("Unknown example")
        return call_tool("run_tensor_example", {"data": examples[example_name]})
    if name == "get_platform_metadata":
        return _result({"version": VERSION, "max_elements": 1_000_000, "threads": torch.get_num_threads(), "read_only": True})
    if name == "run_tensor_example":
        data = arguments.get("data") if isinstance(arguments, dict) else None
        if not isinstance(data, list) or not data or len(data) > 1_000_000 or any(not isinstance(x, (int, float)) or not np.isfinite(x) for x in data):
            raise ValueError("data must be a non-empty list of finite numbers within MAX_ELEMENTS")
        vector = np.ascontiguousarray(data, dtype=np.float32)
        tensor = torch.from_numpy(vector)
        return _result({"shape": str(vector.shape), "l2_norm": round(float(torch.linalg.norm(tensor).item()), 3), "scaled": (tensor * 2).tolist(), "zero_copy": bool(np.shares_memory(vector, tensor.numpy()))})
    raise ValueError("Unknown tool")


def main():
    torch.set_num_threads(2)
    for line in sys.stdin:
        request = {}
        try:
            request = json.loads(line)
            method = request.get("method")
            if method == "initialize":
                response = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "kube-ml", "version": VERSION}}
            elif method == "tools/list":
                response = {"tools": TOOLS}
            elif method == "tools/call":
                params = request.get("params", {})
                response = call_tool(params["name"], params.get("arguments", {}))
            else:
                raise ValueError("Unsupported method")
            print(json.dumps({"jsonrpc": "2.0", "id": request.get("id"), "result": response}), flush=True)
        except Exception as exc:
            print(json.dumps({"jsonrpc": "2.0", "id": request.get("id"), "error": {"code": -32602, "message": str(exc)}}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
