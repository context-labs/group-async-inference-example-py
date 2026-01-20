#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests>=2.31.0",
# ]
# ///
"""
Inference.net Async Group API - Polling Example

This script demonstrates how to use the inference.net Group API to submit
multiple inference requests and poll for results. The Group API is ideal
for processing related tasks (up to 50 requests) without requiring file uploads.

Usage:
    uv run async_polling_example.py

Environment Variables:
    INFERENCE_API_KEY: Your inference.net API key

API Documentation:
    https://docs.inference.net/features/asynchronous-inference/group
"""

import os
import sys
import time
import requests
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# =============================================================================
# Configuration - Customize these values
# =============================================================================

NUM_REQUESTS = 10  # Number of requests to submit (max 50 for Group API)
MODEL_ID = "inference-net/load-test"
POLL_INTERVAL_SECONDS = 2
MAX_POLL_ATTEMPTS = 120  # 4 minutes max at 2 second intervals

BASE_URL = "https://api.inference.net/v1/async"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class RequestInfo:
    """Tracks information about a submitted request."""

    custom_id: str
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


def submit_group_request(
    api_key: str,
    requests_list: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Submit a group of inference requests to the async API.

    Args:
        api_key: Your inference.net API key
        requests_list: List of chat completion request objects

    Returns:
        Response containing groupId and groupSize
    """
    url = f"{BASE_URL}/group/chat/completions"
    payload = {"requests": requests_list}

    response = requests.post(url, headers=get_headers(api_key), json=payload)
    response.raise_for_status()
    return response.json()


def get_group_generations(api_key: str, group_id: str) -> dict[str, Any] | None:
    """
    Retrieve the generations for a group.

    Returns None if the group is not yet available (404).
    """
    url = f"{BASE_URL}/group/{group_id}/generations"
    response = requests.get(url, headers=get_headers(api_key))

    if response.status_code == 404:
        return None

    response.raise_for_status()
    return response.json()


def poll_for_results(
    api_key: str,
    group_id: str,
    expected_count: int,
    poll_interval: int = POLL_INTERVAL_SECONDS,
    max_attempts: int = MAX_POLL_ATTEMPTS,
) -> list[dict[str, Any]]:
    """
    Poll the API until all generations in a group are complete.

    Returns list of generation objects when all are complete.
    Raises TimeoutError if max_attempts exceeded.
    """
    completed_count = 0

    for attempt in range(1, max_attempts + 1):
        result = get_group_generations(api_key, group_id)

        if result is None:
            print(f"  [{attempt:3d}] Waiting for group to be available...")
            time.sleep(poll_interval)
            continue

        generations = result.get("generations", [])
        completed = [g for g in generations if g.get("state") in ("Success", "Failed")]
        pending = [g for g in generations if g.get("state") not in ("Success", "Failed")]
        completed_count = len(completed)

        # Build progress bar
        bar_width = 30
        filled = int(bar_width * completed_count / expected_count)
        bar = "█" * filled + "░" * (bar_width - filled)
        pct = 100 * completed_count / expected_count

        status = ""
        if pending:
            in_progress = sum(1 for g in pending if g.get("state") == "In Progress")
            queued = sum(1 for g in pending if g.get("state") == "Queued")
            if in_progress or queued:
                status = f" (⏳ {in_progress} running, {queued} queued)"

        print(f"  [{attempt:3d}] |{bar}| {completed_count}/{expected_count} ({pct:.0f}%){status}")

        if completed_count >= expected_count:
            return generations

        time.sleep(poll_interval)

    raise TimeoutError(
        f"Polling timed out after {max_attempts} attempts. "
        f"Only {completed_count}/{expected_count} generations completed."
    )


# =============================================================================
# Request Creation
# =============================================================================


def create_sample_requests(count: int) -> tuple[list[dict[str, Any]], dict[str, RequestInfo]]:
    """
    Create sample chat completion requests with custom IDs for correlation.

    Returns:
        Tuple of (requests_list, request_map) where request_map maps custom_id to RequestInfo
    """
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

    requests_list = []
    request_map: dict[str, RequestInfo] = {}
    now = datetime.now()

    for i in range(count):
        custom_id = f"req-{i + 1:03d}"
        question = questions[i % len(questions)]

        request_map[custom_id] = RequestInfo(
            custom_id=custom_id,
            question=question,
            submitted_at=now,
        )

        requests_list.append({
            "model": MODEL_ID,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant. Be concise."},
                {"role": "user", "content": question},
            ],
            "max_tokens": 100,
            "metadata": {"custom_id": custom_id},
        })

    return requests_list, request_map


# =============================================================================
# Result Parsing
# =============================================================================


def parse_generation(gen: dict[str, Any], request_map: dict[str, RequestInfo]) -> GenerationResult:
    """Parse a generation response into a structured result."""
    # Extract custom_id from request metadata
    request_data = gen.get("request", {})
    metadata = request_data.get("metadata", {})
    custom_id = metadata.get("custom_id", "unknown")

    # Get the original question from our request map
    request_info = request_map.get(custom_id)
    question = request_info.question if request_info else "Unknown"

    # Parse response data
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
    dispatched = gen.get("dispatchedAt")
    finished = gen.get("finishedAt")
    if dispatched and finished:
        try:
            d1 = datetime.fromisoformat(dispatched.replace("Z", "+00:00"))
            d2 = datetime.fromisoformat(finished.replace("Z", "+00:00"))
            duration_ms = (d2 - d1).total_seconds() * 1000
        except (ValueError, TypeError):
            pass

    return GenerationResult(
        custom_id=custom_id,
        generation_id=gen.get("id", "N/A"),
        state=state,
        question=question,
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
    print_header("GROUP GENERATION SUMMARY")

    # =========================================================================
    # SUCCESS RATE
    # =========================================================================
    print_subheader("Success Rate")

    success_pct = 100 * success_count / total if total > 0 else 0
    bar_width = 40
    filled = int(bar_width * success_count / total) if total > 0 else 0

    # Color the bar based on success rate
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

    # Table header
    print()
    print(f"  {'ID':<10} {'Status':<10} {'Question':<30} {'Response':<25}")
    print(f"  {'-'*10} {'-'*10} {'-'*30} {'-'*25}")

    # Sort by custom_id for consistent ordering
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
    """Main entry point for the polling example."""

    print_header("INFERENCE.NET ASYNC GROUP API - POLLING EXAMPLE")
    print()
    print(f"  Configuration:")
    print(f"    • Requests to submit: {NUM_REQUESTS}")
    print(f"    • Model: {MODEL_ID}")
    print(f"    • Poll interval: {POLL_INTERVAL_SECONDS}s")

    # Get API key
    api_key = get_api_key()

    # Create sample requests with correlation tracking
    requests_list, request_map = create_sample_requests(NUM_REQUESTS)

    print_subheader(f"Submitting {NUM_REQUESTS} Requests")
    print()
    for req_info in list(request_map.values())[:5]:
        print(f"    {req_info.custom_id}: {truncate(req_info.question, 50)}")
    if NUM_REQUESTS > 5:
        print(f"    ... and {NUM_REQUESTS - 5} more")

    # Submit the group request
    start_time = time.time()
    print()
    print("  Submitting to Group API...")
    group_result = submit_group_request(api_key, requests_list)
    group_id = group_result["groupId"]
    group_size = group_result["groupSize"]

    print(f"  ✓ Group created: {group_id}")
    print(f"  ✓ Group size: {group_size}")

    # Poll for results
    print_subheader("Polling for Results")
    print()

    generations = poll_for_results(api_key, group_id, group_size)
    end_time = time.time()
    total_time = end_time - start_time

    # Parse and display results
    results = [parse_generation(gen, request_map) for gen in generations]
    display_summary(results, total_time)


if __name__ == "__main__":
    main()
