#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests>=2.31.0",
# ]
# ///
"""
Inference.net Async API - Single Request Polling Example

This script demonstrates how to use the inference.net Async API to submit
individual inference requests and poll for their results. Each request is
submitted separately and tracked independently.

Usage:
    uv run async_polling_example.py

Environment Variables:
    INFERENCE_API_KEY: Your inference.net API key

API Documentation:
    https://docs.inference.net/features/asynchronous-inference/overview
"""

import os
import sys
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# =============================================================================
# Configuration - Customize these values
# =============================================================================

NUM_REQUESTS = 10  # Number of requests to submit
MODEL_ID = "inference-net/load-test"
POLL_INTERVAL_SECONDS = 1
MAX_POLL_ATTEMPTS = 120  # 2 minutes max per request
MAX_CONCURRENT_POLLS = 5  # Number of requests to poll concurrently

BASE_URL = "https://api.inference.net/v1"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class RequestInfo:
    """Tracks information about a submitted request."""

    custom_id: str
    generation_id: str
    question: str
    submitted_at: datetime


@dataclass
class GenerationResult:
    """Parsed result from a generation response."""

    custom_id: str
    generation_id: str
    state: str
    question: str
    response_content: str | None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    finish_reason: str | None
    error_message: str | None
    duration_ms: float | None


# =============================================================================
# Utility Functions
# =============================================================================


def get_api_key() -> str:
    """Retrieve the API key from environment variables."""
    api_key = os.getenv("INFERENCE_API_KEY")
    if not api_key:
        print("Error: INFERENCE_API_KEY environment variable is not set.")
        print("Please set it with: export INFERENCE_API_KEY=your-api-key")
        sys.exit(1)
    return api_key


def get_headers(api_key: str) -> dict[str, str]:
    """Build HTTP headers for API requests."""
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def truncate(text: str, max_len: int = 50) -> str:
    """Truncate text with ellipsis if too long."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


# =============================================================================
# API Functions
# =============================================================================


def submit_async_request(
    api_key: str,
    request_payload: dict[str, Any],
) -> str:
    """
    Submit a single inference request to the async API.

    Args:
        api_key: Your inference.net API key
        request_payload: Chat completion request object

    Returns:
        The generation ID for polling
    """
    url = f"{BASE_URL}/async/chat/completions"
    response = requests.post(url, headers=get_headers(api_key), json=request_payload)
    response.raise_for_status()
    result = response.json()
    return result["id"]


def get_generation(api_key: str, generation_id: str) -> dict[str, Any] | None:
    """
    Retrieve the result of a single generation.

    Returns None if not yet available (404) or transient error (5xx).
    """
    url = f"{BASE_URL}/generation/{generation_id}"
    response = requests.get(url, headers=get_headers(api_key))

    # Handle 404 (not ready) and 5xx (transient errors) gracefully
    if response.status_code == 404 or response.status_code >= 500:
        return None

    response.raise_for_status()
    return response.json()


def poll_single_request(
    api_key: str,
    request_info: RequestInfo,
    poll_interval: int = POLL_INTERVAL_SECONDS,
    max_attempts: int = MAX_POLL_ATTEMPTS,
) -> dict[str, Any]:
    """
    Poll for a single generation result until complete.

    Returns the generation result when complete.
    Raises TimeoutError if max_attempts exceeded.
    """
    for _ in range(max_attempts):
        result = get_generation(api_key, request_info.generation_id)

        if result is None:
            time.sleep(poll_interval)
            continue

        state = result.get("state", "Unknown")
        if state in ("Success", "Failed"):
            return result

        time.sleep(poll_interval)

    raise TimeoutError(f"Polling timed out for {request_info.custom_id}")


# =============================================================================
# Request Creation
# =============================================================================


def get_sample_questions(count: int) -> list[str]:
    """Get a list of sample questions."""
    questions = [
        "What is the capital of France?",
        "What is 2 + 2?",
        "Name one planet in our solar system.",
        "What color is the sky on a clear day?",
        "How many legs does a spider have?",
        "What is the chemical symbol for water?",
        "Who wrote Romeo and Juliet?",
        "What is the largest mammal on Earth?",
        "How many continents are there?",
        "What is the speed of light in a vacuum?",
        "What year did World War II end?",
        "What is the smallest prime number?",
        "Name the closest star to Earth.",
        "What is the capital of Japan?",
        "How many bones are in the human body?",
    ]
    return [questions[i % len(questions)] for i in range(count)]


def create_request_payload(question: str, custom_id: str) -> dict[str, Any]:
    """Create a chat completion request payload."""
    return {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant. Be concise."},
            {"role": "user", "content": question},
        ],
        "max_tokens": 100,
        "metadata": {"custom_id": custom_id},
    }


# =============================================================================
# Result Parsing
# =============================================================================


def parse_generation(gen: dict[str, Any], request_info: RequestInfo) -> GenerationResult:
    """Parse a generation response into a structured result."""
    state = gen.get("state", "Unknown")
    response_data = gen.get("response", {})
    choices = response_data.get("choices", [])
    usage = response_data.get("usage", {})

    response_content = None
    finish_reason = None
    if choices:
        message = choices[0].get("message", {})
        response_content = message.get("content")
        finish_reason = choices[0].get("finish_reason")

    # Calculate duration if timestamps available
    duration_ms = None
    finished = gen.get("finishedAt")
    if request_info.submitted_at and finished:
        try:
            d2 = datetime.fromisoformat(finished.replace("Z", "+00:00"))
            duration_ms = (d2 - request_info.submitted_at.astimezone()).total_seconds() * 1000
        except (ValueError, TypeError):
            pass

    return GenerationResult(
        custom_id=request_info.custom_id,
        generation_id=request_info.generation_id,
        state=state,
        question=request_info.question,
        response_content=response_content,
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        total_tokens=usage.get("total_tokens", 0),
        finish_reason=finish_reason,
        error_message=gen.get("stateMessage") if state == "Failed" else None,
        duration_ms=duration_ms,
    )


# =============================================================================
# Display Functions
# =============================================================================


def print_header(title: str, char: str = "=") -> None:
    """Print a formatted section header."""
    width = 80
    print()
    print(char * width)
    print(f" {title}")
    print(char * width)


def print_subheader(title: str) -> None:
    """Print a formatted subsection header."""
    print(f"\n  {title}")
    print("  " + "-" * (len(title) + 4))


def display_summary(results: list[GenerationResult], total_time_seconds: float) -> None:
    """Display a comprehensive summary of all generation results."""

    # Calculate statistics
    total = len(results)
    successful = [r for r in results if r.state == "Success"]
    failed = [r for r in results if r.state == "Failed"]
    success_count = len(successful)
    fail_count = len(failed)

    total_prompt_tokens = sum(r.prompt_tokens for r in results)
    total_completion_tokens = sum(r.completion_tokens for r in results)
    total_tokens = sum(r.total_tokens for r in results)

    durations = [r.duration_ms for r in results if r.duration_ms is not None]
    avg_duration_ms = sum(durations) / len(durations) if durations else 0
    min_duration_ms = min(durations) if durations else 0
    max_duration_ms = max(durations) if durations else 0

    # =========================================================================
    # SUMMARY HEADER
    # =========================================================================
    print_header("ASYNC GENERATION SUMMARY")

    # =========================================================================
    # SUCCESS RATE
    # =========================================================================
    print_subheader("Success Rate")

    success_pct = 100 * success_count / total if total > 0 else 0
    bar_width = 40
    filled = int(bar_width * success_count / total) if total > 0 else 0

    if success_pct == 100:
        bar = "█" * filled
        status_icon = "✓"
    elif success_pct >= 80:
        bar = "█" * filled + "░" * (bar_width - filled)
        status_icon = "●"
    else:
        bar = "█" * filled + "░" * (bar_width - filled)
        status_icon = "✗"

    print(f"  {status_icon} |{bar}| {success_pct:.1f}%")
    print()
    print(f"      Successful:  {success_count:4d}")
    print(f"      Failed:      {fail_count:4d}")
    print(f"      Total:       {total:4d}")

    # =========================================================================
    # PERFORMANCE METRICS
    # =========================================================================
    print_subheader("Performance Metrics")

    print(f"      Total wall-clock time:   {total_time_seconds:8.2f}s")
    print(f"      Avg generation time:     {avg_duration_ms:8.1f}ms")
    print(f"      Min generation time:     {min_duration_ms:8.1f}ms")
    print(f"      Max generation time:     {max_duration_ms:8.1f}ms")
    if total_time_seconds > 0:
        throughput = total / total_time_seconds
        print(f"      Throughput:              {throughput:8.2f} req/s")

    # =========================================================================
    # TOKEN USAGE
    # =========================================================================
    print_subheader("Token Usage")

    print(f"      Prompt tokens:       {total_prompt_tokens:8,d}")
    print(f"      Completion tokens:   {total_completion_tokens:8,d}")
    print(f"      Total tokens:        {total_tokens:8,d}")
    if success_count > 0:
        avg_completion = total_completion_tokens / success_count
        print(f"      Avg completion/req:  {avg_completion:8.1f}")

    # =========================================================================
    # REQUEST-RESPONSE CORRELATION TABLE
    # =========================================================================
    print_subheader("Request-Response Correlation")

    print()
    print(f"  {'ID':<10} {'Status':<10} {'Question':<30} {'Response':<25}")
    print(f"  {'-'*10} {'-'*10} {'-'*30} {'-'*25}")

    sorted_results = sorted(results, key=lambda r: r.custom_id)

    for r in sorted_results:
        status = "✓ Success" if r.state == "Success" else "✗ Failed"
        question = truncate(r.question, 28)
        response = truncate(r.response_content or r.error_message or "N/A", 23)
        print(f"  {r.custom_id:<10} {status:<10} {question:<30} {response:<25}")

    # =========================================================================
    # DETAILED RESULTS (for failed requests)
    # =========================================================================
    if failed:
        print_subheader("Failed Request Details")
        for r in failed:
            print(f"      {r.custom_id}: {r.error_message or 'Unknown error'}")

    # =========================================================================
    # FOOTER
    # =========================================================================
    print()
    print("=" * 80)
    print(" Generation complete!")
    print("=" * 80)
    print()


# =============================================================================
# Main
# =============================================================================


def main() -> None:
    """Main entry point for the async polling example."""

    print_header("INFERENCE.NET ASYNC API - SINGLE REQUEST POLLING EXAMPLE")
    print()
    print(f"  Configuration:")
    print(f"    • Requests to submit: {NUM_REQUESTS}")
    print(f"    • Model: {MODEL_ID}")
    print(f"    • Poll interval: {POLL_INTERVAL_SECONDS}s")
    print(f"    • Concurrent polls: {MAX_CONCURRENT_POLLS}")

    api_key = get_api_key()
    questions = get_sample_questions(NUM_REQUESTS)

    # =========================================================================
    # SUBMIT REQUESTS
    # =========================================================================
    print_subheader(f"Submitting {NUM_REQUESTS} Requests")
    print()

    submitted_requests: list[RequestInfo] = []
    start_time = time.time()

    for i, question in enumerate(questions):
        custom_id = f"req-{i + 1:03d}"
        payload = create_request_payload(question, custom_id)

        generation_id = submit_async_request(api_key, payload)
        now = datetime.now().astimezone()

        request_info = RequestInfo(
            custom_id=custom_id,
            generation_id=generation_id,
            question=question,
            submitted_at=now,
        )
        submitted_requests.append(request_info)

        print(f"    ✓ {custom_id}: {truncate(question, 40)} → {generation_id[:12]}...")

    print()
    print(f"  Submitted {len(submitted_requests)} requests")

    # =========================================================================
    # POLL FOR RESULTS
    # =========================================================================
    print_subheader("Polling for Results")
    print()

    results: list[GenerationResult] = []
    completed = 0

    def poll_and_parse(req_info: RequestInfo) -> GenerationResult:
        """Poll for a single request and parse the result."""
        gen_result = poll_single_request(api_key, req_info)
        return parse_generation(gen_result, req_info)

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_POLLS) as executor:
        futures = {executor.submit(poll_and_parse, req): req for req in submitted_requests}

        for future in as_completed(futures):
            req_info = futures[future]
            try:
                result = future.result()
                results.append(result)
                completed += 1

                # Progress update
                bar_width = 30
                filled = int(bar_width * completed / NUM_REQUESTS)
                bar = "█" * filled + "░" * (bar_width - filled)
                pct = 100 * completed / NUM_REQUESTS
                status = "✓" if result.state == "Success" else "✗"

                print(f"  [{completed:3d}/{NUM_REQUESTS}] |{bar}| {pct:.0f}% {status} {req_info.custom_id}")

            except TimeoutError as e:
                print(f"  ✗ {req_info.custom_id}: {e}")
                results.append(GenerationResult(
                    custom_id=req_info.custom_id,
                    generation_id=req_info.generation_id,
                    state="Failed",
                    question=req_info.question,
                    response_content=None,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    finish_reason=None,
                    error_message="Polling timeout",
                    duration_ms=None,
                ))
                completed += 1

    end_time = time.time()
    total_time = end_time - start_time

    # =========================================================================
    # DISPLAY SUMMARY
    # =========================================================================
    display_summary(results, total_time)


if __name__ == "__main__":
    main()
