# Inference.net Async API - Python Samples

Sample scripts demonstrating how to use the [inference.net](https://inference.net) Asynchronous Inference API for cost-effective batch processing.

## Overview

The inference.net Async API allows you to submit inference requests that complete within 24-72 hours (but generally finish much faster, often within a few minutes) at significantly reduced costs. This repository contains two approaches for working with the async API:

| Approach | Description | Best For |
|----------|-------------|----------|
| [**Single Request**](./async/) | Submit requests individually, poll each separately | Streaming, fine-grained control |
| [**Group API**](./async-with-group/) | Submit up to 50 requests as a batch | Batch processing, simpler tracking |

## Quick Comparison

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SINGLE REQUEST APPROACH                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Request 1 ──► /v1/async/chat/completions ──► ID-1 ──► Poll /generation/1  │
│   Request 2 ──► /v1/async/chat/completions ──► ID-2 ──► Poll /generation/2  │
│   Request 3 ──► /v1/async/chat/completions ──► ID-3 ──► Poll /generation/3  │
│                                                                             │
│   • Each request tracked independently                                      │
│   • Poll each generation ID separately                                      │
│   • Process results as they complete                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           GROUP API APPROACH                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐                                                           │
│   │ Request 1   │                                                           │
│   │ Request 2   │──► /v1/async/group/chat/completions ──► Group ID          │
│   │ Request 3   │                                              │            │
│   └─────────────┘                                              ▼            │
│                                            Poll /group/{id}/generations     │
│                                                              │              │
│   • Single API call for multiple requests                    ▼              │
│   • One group ID tracks all requests          ┌─────────────────────────┐   │
│   • Get all results in one response           │ All results together    │   │
│                                               └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Feature Comparison

| Feature | Single Request | Group API |
|---------|---------------|-----------|
| Max requests | Unlimited | 50 per group |
| Submission | Individual API calls | Single batch call |
| Tracking | One ID per request | One ID for entire group |
| Polling | Poll each request | Poll once for all |
| Results | Process as completed | Get all at once |
| Complexity | More code, more control | Simpler, less flexible |

## When to Use Each Approach

### Use Single Request (`async/`) when:

- Requests arrive over time (streaming/real-time)
- You need different retry logic per request
- You want to process results immediately as each completes
- You're integrating with existing per-request workflows
- You need more than 50 requests

### Use Group API (`async-with-group/`) when:

- You have a batch of related requests ready to submit
- You want simpler code with less polling logic
- You're processing up to 50 requests together
- You want to track completion of an entire batch
- You plan to use webhook notifications (coming soon)

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

2. Run either example:

```bash
# Single request approach
uv run async/async_polling_example.py

# Group API approach
uv run async-with-group/async_polling_example.py
```

## Project Structure

```
python-async-samples/
├── README.md                          # This file
├── async/                             # Single request approach
│   ├── README.md                      # Detailed documentation
│   └── async_polling_example.py       # Example script
└── async-with-group/                  # Group API approach
    ├── README.md                      # Detailed documentation
    └── async_polling_example.py       # Example script
```

## API Endpoints Reference

### Single Request API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/async/chat/completions` | POST | Submit a single async request |
| `/v1/generation/{id}` | GET | Get result for a generation |

### Group API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/async/group/chat/completions` | POST | Submit a group of requests |
| `/v1/async/group/{groupId}/generations` | GET | Get all results for a group |

## Documentation

- [Async API Overview](https://docs.inference.net/features/asynchronous-inference/overview)
- [Group API Reference](https://docs.inference.net/features/asynchronous-inference/group)

## License

MIT
