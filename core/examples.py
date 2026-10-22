"""Shared, read-only examples used by the HTTP API and GUI."""

MAX_ELEMENTS = 1_000_000
EXAMPLES = {
    "basic-vector": {"description": "Calculate an L2 norm and scale a small vector by two.", "payload": {"data": [3.0, 4.0]}},
    "feature-vector": {"description": "Process a four-feature float vector through the tensor bridge.", "payload": {"data": [10.0, 20.0, 30.0, 40.0]}},
}


def example_catalog(version):
    return {"version": version, "max_elements": MAX_ELEMENTS, "examples": EXAMPLES}
