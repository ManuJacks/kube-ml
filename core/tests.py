import json
import numpy as np
import torch
from django.test import SimpleTestCase, Client
from core.views import MAX_ELEMENTS

class TensorBridgeTests(SimpleTestCase):
    def setUp(self):
        self.client = Client()

    def test_gui_renders_successfully(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'NumPy & PyTorch Zero-Copy Platform')
        self.assertContains(response, 'v0.1.2')

    def test_method_not_allowed_for_get_predict(self):
        response = self.client.get('/predict')
        self.assertEqual(response.status_code, 405)

    def test_health_readiness_and_metrics_endpoints(self):
        self.assertEqual(self.client.get('/healthz').status_code, 200)
        self.assertEqual(self.client.get('/readyz').json()['status'], 'ready')
        self.assertIn('kube_ml_predictions_total', self.client.get('/metrics').content.decode())

    def test_examples_api_is_read_only_and_deterministic(self):
        response = self.client.get('/api/v1/examples')
        self.assertEqual(response.status_code, 200)
        self.assertIn('basic-vector', response.json()['examples'])
        example = self.client.get('/api/v1/examples/basic-vector')
        self.assertEqual(example.json()['payload'], {'data': [3.0, 4.0]})

    def test_non_finite_values_are_rejected(self):
        response = self.client.post('/predict', data=json.dumps({'data': [1.0, float('nan')]}), content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_zero_copy_and_calculations(self):
        payload = {"data": [3.0, 4.0]}
        response = self.client.post(
            '/predict',
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["original"], [3.0, 4.0])
        self.assertEqual(data["shape"], "(2,)")
        self.assertEqual(data["l2_norm"], 5.0)
        self.assertEqual(data["numpy_processed"], [6.0, 8.0])
        self.assertTrue(data["zero_copy"])
        self.assertEqual(data["threads"], 2)

    def test_thread_constraint_enforced(self):
        self.assertEqual(torch.get_num_threads(), 2)

    def test_max_elements_payload_limit_enforced(self):
        oversized = [1.0] * (MAX_ELEMENTS + 1)
        response = self.client.post(
            '/predict',
            data=json.dumps({"data": oversized}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("exceeds MAX_ELEMENTS", data["error"])

    def test_invalid_payload_rejected(self):
        # Empty array
        res = self.client.post('/predict', data=json.dumps({"data": []}), content_type="application/json")
        self.assertEqual(res.status_code, 400)

        # Non-list data
        res = self.client.post('/predict', data=json.dumps({"data": "invalid"}), content_type="application/json")
        self.assertEqual(res.status_code, 400)

        # Malformed JSON
        res = self.client.post('/predict', data="not-json", content_type="application/json")
        self.assertEqual(res.status_code, 400)

    def test_buffer_memory_sharing(self):
        arr = np.ascontiguousarray([10.0, 20.0, 30.0], dtype=np.float32)
        t = torch.from_numpy(arr)
        self.assertTrue(np.shares_memory(arr, t.numpy()))
        t[0] = 99.0
        self.assertEqual(arr[0], 99.0)
