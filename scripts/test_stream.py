"""
Test SSE Streaming Endpoints

Usage:
    python scripts/test_stream.py [--api-key KEY] [--base-url URL]

Requires:
    pip install httpx-sse httpx
"""

import argparse
import json
import httpx
from httpx_sse import connect_sse


def test_start_stream(client: httpx.Client, base_url: str, api_key: str):
    """Test the /interview/start/stream endpoint"""
    print("\n" + "=" * 50)
    print("Testing POST /interview/start/stream")
    print("=" * 50)

    payload = {
        "candidate_id": "test-candidate-001",
        "resume_text": "John Doe - Senior Python Developer with 5 years experience. Skills: Python, FastAPI, Docker, PostgreSQL, AWS."
    }

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key
    }

    session_id = None
    event_count = 0

    try:
        with connect_sse(
            client,
            "POST",
            f"{base_url}/interview/start/stream",
            json=payload,
            headers=headers
        ) as event_source:
            print("\nReceiving events:\n")
            for event in event_source.iter_sse():
                event_count += 1
                print(f"[{event_count}] event: {event.event}")
                print(f"    data: {event.data}")
                print()

                # Extract session_id
                if event.event == "session":
                    try:
                        data = json.loads(event.data)
                        session_id = data.get("session_id")
                    except:
                        pass

    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

    print(f"\nTotal events received: {event_count}")
    return session_id


def test_chat_stream(client: httpx.Client, base_url: str, api_key: str, session_id: str):
    """Test the /interview/chat/{session_id}/stream endpoint"""
    print("\n" + "=" * 50)
    print(f"Testing POST /interview/chat/{session_id}/stream")
    print("=" * 50)

    payload = {
        "answer": "I have been working with Python for 5 years, primarily building REST APIs with FastAPI and Flask. I led a team of 3 developers."
    }

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key
    }

    event_count = 0

    try:
        with connect_sse(
            client,
            "POST",
            f"{base_url}/interview/chat/{session_id}/stream",
            json=payload,
            headers=headers
        ) as event_source:
            print("\nReceiving events:\n")
            for event in event_source.iter_sse():
                event_count += 1
                print(f"[{event_count}] event: {event.event}")
                print(f"    data: {event.data}")
                print()

    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

    print(f"\nTotal events received: {event_count}")


def main():
    parser = argparse.ArgumentParser(description="Test SSE Streaming Endpoints")
    parser.add_argument("--api-key", default="tahuB03lat", help="API key")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL")
    parser.add_argument("--skip-chat", action="store_true", help="Skip chat test")
    args = parser.parse_args()

    print("=" * 50)
    print("SSE Streaming Test")
    print("=" * 50)
    print(f"Base URL: {args.base_url}")
    print(f"API Key: {args.api_key[:10]}...")

    # Use httpx client with longer timeout for streaming
    with httpx.Client(timeout=120.0) as client:
        # Test start stream
        session_id = test_start_stream(client, args.base_url, args.api_key)

        # Test chat stream if we got a session_id
        if session_id and not args.skip_chat:
            print(f"\nExtracted session_id: {session_id}")
            test_chat_stream(client, args.base_url, args.api_key, session_id)
        elif not session_id:
            print("\nNo session_id extracted, skipping chat test")

    print("\n" + "=" * 50)
    print("Test Complete")
    print("=" * 50)


if __name__ == "__main__":
    main()
