# Async API - Single Request Polling

This example demonstrates using the inference.net Async API to submit individual inference requests and poll for results.

## Overview

The single-request async approach:
1. Submits each request individually to `/v1/async/chat/completions`
2. Receives a unique generation ID for each request immediately
3. Polls `/v1/generation/{id}` for each request until complete
4. Uses concurrent polling for efficiency

## When to Use This Approach

- **Fine-grained control**: When you need to track and manage each request independently
- **Streaming submissions**: When requests arrive over time rather than all at once
- **Custom retry logic**: When you need different retry strategies per request
- **Real-time progress**: When you want to process results as soon as each completes

## Quick Start

```bash
export INFERENCE_API_KEY=your-api-key
uv run async_polling_example.py
```

## Configuration

Edit the configuration section at the top of `async_polling_example.py`:

```python
NUM_REQUESTS = 10           # Number of requests to submit
MODEL_ID = "your-model-id"  # Model to use for inference
POLL_INTERVAL_SECONDS = 1   # Seconds between polling attempts
MAX_POLL_ATTEMPTS = 120     # Maximum attempts per request
MAX_CONCURRENT_POLLS = 5    # Concurrent polling threads
```

## How It Works

### 1. Submit Requests

Each request is submitted individually and returns a generation ID immediately:

```python
response = requests.post(
    "https://api.inference.net/v1/async/chat/completions",
    headers={"Authorization": f"Bearer {api_key}"},
    json={
        "model": "your-model",
        "messages": [{"role": "user", "content": "Hello"}],
        "metadata": {"custom_id": "my-tracking-id"}
    }
)
generation_id = response.json()["id"]
```

### 2. Poll for Results

Poll the generation endpoint until the request completes:

```python
response = requests.get(
    f"https://api.inference.net/v1/generation/{generation_id}",
    headers={"Authorization": f"Bearer {api_key}"}
)
result = response.json()

if result["state"] == "Success":
    content = result["response"]["choices"][0]["message"]["content"]
```

### 3. Correlate Responses

The `metadata.custom_id` you provide is preserved in the response:

```python
custom_id = result["request"]["metadata"]["custom_id"]
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/async/chat/completions` | POST | Submit a single async request |
| `/v1/generation/{id}` | GET | Retrieve result for a generation |

## Sample Output

```
================================================================================
 INFERENCE.NET ASYNC API - SINGLE REQUEST POLLING EXAMPLE
================================================================================

  Configuration:
    • Requests to submit: 10
    • Model: inference-net/load-test
    • Poll interval: 1s
    • Concurrent polls: 5

  Submitting 10 Requests
  --------------------------

    ✓ req-001: What is the capital of France? → N2mZQjrvh-k_...
    ✓ req-002: What is 2 + 2? → X4pLMnrth-j_...
    ...

  Polling for Results
  -----------------------

  [  1/10] |███░░░░░░░░░░░░░░░░░░░░░░░░░░░| 10% ✓ req-003
  [  2/10] |██████░░░░░░░░░░░░░░░░░░░░░░░░| 20% ✓ req-001
  ...

================================================================================
 ASYNC GENERATION SUMMARY
================================================================================

  Success Rate
  ----------------
  ✓ |████████████████████████████████████████| 100.0%

      Successful:    10
      Failed:         0
      Total:         10
  ...
```

## Comparison with Group API

| Feature | Single Request | Group API |
|---------|---------------|-----------|
| Submission | One request at a time | Up to 50 requests at once |
| Tracking | Individual generation IDs | Single group ID |
| Polling | Poll each request separately | Poll once for all results |
| Best for | Streaming, fine-grained control | Batch processing |

For batch processing of related requests, see the [Group API example](../async-with-group/).
