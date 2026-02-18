"""
Test Time-To-First-Chunk (TTFC) for streaming interview endpoints.

Measures how long it takes for the user to receive the first SSE event
after calling the streaming API endpoints.

Usage:
    python scripts/test_ttfc.py

To test staging, change BASE_URL below.
"""

import time
import httpx
import json
from typing import Optional

# ============ CONFIGURATION ============
# Change this to test different environments
BASE_URL = "http://127.0.0.1:8000"
# BASE_URL = "https://staging.example.com"  # Uncomment for staging

API_KEY = "your-api-key-here"  # Set your API key

# Sample resume for testing
SAMPLE_RESUME = """
John Doe - Senior Software Engineer

Experience:
- 5 years of Python development
- Built REST APIs with FastAPI and Flask
- Experience with PostgreSQL and Redis
- Docker and Kubernetes deployment
- CI/CD with GitHub Actions

Education:
- BS Computer Science, MIT 2018
"""

# ============ HELPERS ============

def get_headers() -> dict:
    """Get request headers with API key."""
    return {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
    }


def measure_ttfc_start_interview(
    candidate_id: str = "test-ttfc-001",
    mode: str = "dynamic_gap"
) -> dict:
    """
    Measure Time-To-First-Chunk for /interview/start/stream endpoint.

    Returns:
        dict with ttfc_ms, first_event_type, session_id, total_time_ms
    """
    url = f"{BASE_URL}/interview/start/stream"
    payload = {
        "candidate_id": candidate_id,
        "resume_text": SAMPLE_RESUME,
        "mode": mode
    }

    print(f"\n{'='*60}")
    print(f"Testing: POST {url}")
    print(f"Mode: {mode}")
    print(f"{'='*60}")

    start_time = time.perf_counter()
    first_chunk_time = None
    first_event = None
    session_id = None
    events_received = []

    try:
        with httpx.Client(timeout=120.0) as client:
            with client.stream(
                "POST",
                url,
                json=payload,
                headers=get_headers()
            ) as response:
                if response.status_code != 200:
                    print(f"Error: HTTP {response.status_code}")
                    print(response.text)
                    return {"error": f"HTTP {response.status_code}"}

                # Read SSE events
                buffer = ""
                for chunk in response.iter_text():
                    if first_chunk_time is None:
                        first_chunk_time = time.perf_counter()

                    buffer += chunk

                    # Parse SSE events from buffer
                    while "\n\n" in buffer:
                        event_text, buffer = buffer.split("\n\n", 1)
                        event_type = None
                        event_data = None

                        for line in event_text.split("\n"):
                            if line.startswith("event:"):
                                event_type = line[6:].strip()
                            elif line.startswith("data:"):
                                try:
                                    event_data = json.loads(line[5:].strip())
                                except json.JSONDecodeError:
                                    event_data = line[5:].strip()

                        if event_type:
                            events_received.append(event_type)

                            if first_event is None:
                                first_event = event_type

                            if event_type == "session" and event_data:
                                session_id = event_data.get("session_id")

                            # Print event info
                            elapsed = (time.perf_counter() - start_time) * 1000
                            print(f"  [{elapsed:7.1f}ms] event: {event_type}")

                            if event_type == "complete":
                                break

                    if events_received and events_received[-1] == "complete":
                        break

    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}

    end_time = time.perf_counter()

    ttfc_ms = (first_chunk_time - start_time) * 1000 if first_chunk_time else None
    total_ms = (end_time - start_time) * 1000

    result = {
        "endpoint": "/interview/start/stream",
        "ttfc_ms": round(ttfc_ms, 2) if ttfc_ms else None,
        "first_event": first_event,
        "session_id": session_id,
        "total_time_ms": round(total_ms, 2),
        "events_count": len(events_received)
    }

    print(f"\n--- Results ---")
    print(f"Time to First Chunk: {result['ttfc_ms']} ms")
    print(f"First Event Type:    {result['first_event']}")
    print(f"Total Time:          {result['total_time_ms']} ms")
    print(f"Events Received:     {result['events_count']}")
    print(f"Session ID:          {result['session_id']}")

    return result


def measure_ttfc_chat(
    session_id: str,
    answer: str = "I have 5 years of experience with Python, mainly building backend services."
) -> dict:
    """
    Measure Time-To-First-Chunk for /interview/chat/{session_id}/stream endpoint.

    Args:
        session_id: Session ID from start_interview
        answer: User's answer to send

    Returns:
        dict with ttfc_ms, first_event_type, total_time_ms
    """
    url = f"{BASE_URL}/interview/chat/{session_id}/stream"
    payload = {"answer": answer}

    print(f"\n{'='*60}")
    print(f"Testing: POST {url}")
    print(f"Answer: {answer[:50]}...")
    print(f"{'='*60}")

    start_time = time.perf_counter()
    first_chunk_time = None
    first_event = None
    events_received = []
    completed = False
    next_question = None

    try:
        with httpx.Client(timeout=120.0) as client:
            with client.stream(
                "POST",
                url,
                json=payload,
                headers=get_headers()
            ) as response:
                if response.status_code != 200:
                    print(f"Error: HTTP {response.status_code}")
                    print(response.text)
                    return {"error": f"HTTP {response.status_code}"}

                # Read SSE events
                buffer = ""
                for chunk in response.iter_text():
                    if first_chunk_time is None:
                        first_chunk_time = time.perf_counter()

                    buffer += chunk

                    # Parse SSE events from buffer
                    while "\n\n" in buffer:
                        event_text, buffer = buffer.split("\n\n", 1)
                        event_type = None
                        event_data = None

                        for line in event_text.split("\n"):
                            if line.startswith("event:"):
                                event_type = line[6:].strip()
                            elif line.startswith("data:"):
                                try:
                                    event_data = json.loads(line[5:].strip())
                                except json.JSONDecodeError:
                                    event_data = line[5:].strip()

                        if event_type:
                            events_received.append(event_type)

                            if first_event is None:
                                first_event = event_type

                            if event_type == "complete" and event_data:
                                completed = event_data.get("completed", False)
                                next_question = event_data.get("question")

                            # Print event info
                            elapsed = (time.perf_counter() - start_time) * 1000
                            print(f"  [{elapsed:7.1f}ms] event: {event_type}")

                            if event_type == "complete":
                                break

                    if events_received and events_received[-1] == "complete":
                        break

    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}

    end_time = time.perf_counter()

    ttfc_ms = (first_chunk_time - start_time) * 1000 if first_chunk_time else None
    total_ms = (end_time - start_time) * 1000

    result = {
        "endpoint": f"/interview/chat/{session_id}/stream",
        "ttfc_ms": round(ttfc_ms, 2) if ttfc_ms else None,
        "first_event": first_event,
        "total_time_ms": round(total_ms, 2),
        "events_count": len(events_received),
        "interview_completed": completed
    }

    print(f"\n--- Results ---")
    print(f"Time to First Chunk: {result['ttfc_ms']} ms")
    print(f"First Event Type:    {result['first_event']}")
    print(f"Total Time:          {result['total_time_ms']} ms")
    print(f"Events Received:     {result['events_count']}")
    print(f"Interview Completed: {result['interview_completed']}")
    if next_question:
        print(f"Next Question:       {next_question[:60]}...")

    return result


def run_full_test():
    """Run complete TTFC test for start and chat endpoints."""
    print("\n" + "="*60)
    print("  TIME-TO-FIRST-CHUNK (TTFC) TEST")
    print(f"  Base URL: {BASE_URL}")
    print("="*60)

    # Test 1: Start interview
    start_result = measure_ttfc_start_interview(
        candidate_id=f"ttfc-test-{int(time.time())}"
    )

    if "error" in start_result or not start_result.get("session_id"):
        print("\n❌ Start interview failed, cannot test chat endpoint")
        return

    session_id = start_result["session_id"]

    # Test 2: Chat endpoint
    chat_result = measure_ttfc_chat(
        session_id=session_id,
        answer="I have been working with Python for about 5 years now. I started with Django for web development, then moved to FastAPI for building microservices. I've also used Python extensively for data processing scripts and automation."
    )

    # Summary
    print("\n" + "="*60)
    print("  SUMMARY")
    print("="*60)
    print(f"\n  /interview/start/stream")
    print(f"    TTFC:       {start_result.get('ttfc_ms')} ms")
    print(f"    Total:      {start_result.get('total_time_ms')} ms")

    print(f"\n  /interview/chat/{{session_id}}/stream")
    print(f"    TTFC:       {chat_result.get('ttfc_ms')} ms")
    print(f"    Total:      {chat_result.get('total_time_ms')} ms")

    print("\n" + "="*60)


if __name__ == "__main__":
    run_full_test()
