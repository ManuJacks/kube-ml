curl -s -X POST http://localhost:8000/predict \
      -H "Content-Type: application/json" \
      -d '{"data": [3.0, 4.0]}' | jq .        
