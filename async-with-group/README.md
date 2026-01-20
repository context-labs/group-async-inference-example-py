# Inference.net Async API - Python Samples

Sample scripts demonstrating how to use the [inference.net](https://inference.net) Asynchronous Inference API for cost-effective batch processing.

## Overview

The inference.net Async API allows you to submit inference requests that complete within 24-72 hours (but generally finish much faster, often within a few minutes) at significantly reduced costs. This is ideal for:

- Large-scale content generation
- Batch document processing
- Non-urgent data analysis
- Cost-sensitive workloads

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- An inference.net API key

### Installing uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with Homebrew
brew install uv
```

## Quick Start

1. Set your API key:

```bash
export INFERENCE_API_KEY=your-api-key-here
```

2. Run the polling example:

```bash
uv run async_polling_example.py
```

## Configuration

Edit the configuration section at the top of `async_polling_example.py`:

```python
NUM_REQUESTS = 10           # Number of requests to submit (max 50)
MODEL_ID = "your-model-id"  # Model to use for inference
POLL_INTERVAL_SECONDS = 2   # Seconds between polling attempts
MAX_POLL_ATTEMPTS = 120     # Maximum polling attempts
```

## Examples

### Polling Example (`async_polling_example.py`)

Demonstrates submitting a group of inference requests, polling for results, and displaying a comprehensive summary.

**Features:**
- Configurable number of requests (up to 50)
- Progress bar during polling
- Request-response correlation via custom IDs
- Comprehensive summary with success rates, performance metrics, and token usage

**Sample Output:**

```
================================================================================
 INFERENCE.NET ASYNC GROUP API - POLLING EXAMPLE
================================================================================

  Configuration:
    • Requests to submit: 10
    • Model: inference-net/load-test
    • Poll interval: 2s

  Submitting 10 Requests
  --------------------------

    req-001: What is the capital of France?
    req-002: What is 2 + 2?
    req-003: Name one planet in our solar system.
    req-004: What color is the sky on a clear day?
    req-005: How many legs does a spider have?
    ... and 5 more

  Submitting to Group API...
  ✓ Group created: 6Z6oLaIo0PFleu2Wc1LIg
  ✓ Group size: 10

  Polling for Results
  -----------------------

  [  1] |░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░| 0/10 (0%) (⏳ 0 running, 5 queued)
  [  2] |████████████████████████░░░░░░| 8/10 (80%) (⏳ 2 running, 0 queued)
  [  3] |██████████████████████████████| 10/10 (100%)

================================================================================
 GROUP GENERATION SUMMARY
================================================================================

  Success Rate
  ----------------
  ✓ |████████████████████████████████████████| 100.0%

      Successful:    10
      Failed:         0
      Total:         10

  Performance Metrics
  -----------------------
      Total wall-clock time:      12.75s
      Avg generation time:       2803.1ms
      Min generation time:        955.0ms
      Max generation time:       4556.0ms
      Throughput:                  0.78 req/s

  Token Usage
  ---------------
      Prompt tokens:            186
      Completion tokens:      1,000
      Total tokens:           1,186
      Avg completion/req:     100.0

  Request-Response Correlation
  --------------------------------

  ID         Status     Question                       Response
  ---------- ---------- ------------------------------ -------------------------
  req-001    ✓ Success  What is the capital of Fr...   The capital of France...
  req-002    ✓ Success  What is 2 + 2?                 2 + 2 equals 4.
  req-003    ✓ Success  Name one planet in our so...   Mars is a planet in...
  ...

================================================================================
 Generation complete!
================================================================================
```

## How Request-Response Correlation Works

Each request includes a `metadata.custom_id` field that persists through the async processing pipeline:

```python
{
    "model": "your-model",
    "messages": [...],
    "metadata": {"custom_id": "req-001"}  # Your tracking ID
}
```

When retrieving results, the custom_id is available in the response, allowing you to match responses back to your original requests:

```python
# In the generation response:
generation["request"]["metadata"]["custom_id"]  # "req-001"
```

## API Endpoints Used

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/async/group/chat/completions` | POST | Submit a group of chat completion requests |
| `/v1/async/group/{groupId}/generations` | GET | Retrieve results for a group |

## Group API Limits

- Maximum 50 requests per group
- Completion time: 24-72 hours
- Groups expire after 72 hours if not completed

## Documentation

- [Async API Overview](https://docs.inference.net/features/asynchronous-inference/overview)
- [Group API Reference](https://docs.inference.net/features/asynchronous-inference/group)

## License

MIT
