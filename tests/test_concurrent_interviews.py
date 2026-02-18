"""
Test script to reproduce concurrent interview start issue.

Sends 2 simultaneous POST requests to /interview/start to reproduce
the concurrency bug where shared state causes DB conflicts.

Usage:
    python tests/test_concurrent_interviews.py

Requires:
    - API server running (uvicorn api.main:app --reload)
    - Set API_KEY below to a valid key from your api_keys table
"""

import json
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
BASE_URL = "http://127.0.0.1:8000"
API_KEY = "tahuB03lat"  # Replace with your actual API key
QUESTION_SET_ID = "03b84681-2c75-4bbd-89ee-307861ec7b6b"  # From seed_predefined_questions.py

# Test scenarios
DYNAMIC_GAP_REQUESTS = [
    {
        "candidate_id": "concurrent-test-dynamic-1",
        "resume_text": (
            "John Doe - Senior Python Developer\n"
            "Experience:\n"
            "- 5 years Python development at TechCorp\n"
            "- Built microservices with FastAPI and Flask\n"
            "- PostgreSQL and Redis for data storage\n"
            "- Docker and Kubernetes for deployment\n"
            "- Led team of 4 developers\n"
            "Skills: Python, FastAPI, PostgreSQL, Docker, Kubernetes"
        ),
        "mode": "dynamic_gap"
    },
    {
        "candidate_id": "concurrent-test-dynamic-2",
        "resume_text": (
            "Jane Smith - Full Stack Engineer\n"
            "Experience:\n"
            "- 3 years React/TypeScript frontend development\n"
            "- 2 years Node.js backend APIs\n"
            "- AWS Lambda and DynamoDB serverless architecture\n"
            "- CI/CD with GitHub Actions\n"
            "- Mentored 2 junior developers\n"
            "Skills: React, TypeScript, Node.js, AWS, DynamoDB"
        ),
        "mode": "dynamic_gap"
    }
]

PREDEFINED_REQUESTS = [
    {
        "candidate_id": "concurrent-test-predefined-1",
        "resume_text": (
            "Alice Chen - Backend Engineer\n"
            "Experience:\n"
            "- 4 years Java/Spring Boot development\n"
            "- Designed REST APIs serving 10k+ requests/sec\n"
            "- MySQL and MongoDB for data persistence\n"
            "- AWS ECS and Terraform for infrastructure\n"
            "Skills: Java, Spring Boot, MySQL, MongoDB, AWS"
        ),
        "mode": "predefined_questions",
        "question_set_id": QUESTION_SET_ID
    },
    {
        "candidate_id": "concurrent-test-predefined-2",
        "resume_text": (
            "Bob Martinez - DevOps Engineer\n"
            "Experience:\n"
            "- 6 years infrastructure and platform engineering\n"
            "- Kubernetes cluster management at scale\n"
            "- CI/CD pipelines with Jenkins and ArgoCD\n"
            "- Monitoring with Prometheus and Grafana\n"
            "Skills: Kubernetes, Terraform, Jenkins, ArgoCD, AWS"
        ),
        "mode": "predefined_questions",
        "question_set_id": QUESTION_SET_ID
    }
]


def start_interview(request_data: dict, label: str) -> dict:
    """Send a single start interview request."""
    print(f"[{label}] Sending request...")
    start_time = time.time()

    try:
        payload = json.dumps(request_data).encode("utf-8")
        req = urllib.request.Request(
            f"{BASE_URL}/interview/start",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": API_KEY,
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            elapsed = time.time() - start_time
            status = resp.status
            body = json.loads(resp.read().decode("utf-8"))
            print(f"[{label}] Status: {status} ({elapsed:.2f}s)")
            print(f"[{label}] Session ID: {body['session_id']}")
            print(f"[{label}] Question: {body['question'][:100]}...")
            return {"success": True, "data": body, "label": label}

    except urllib.error.HTTPError as e:
        elapsed = time.time() - start_time
        error_body = e.read().decode("utf-8") if e.fp else ""
        print(f"[{label}] HTTP {e.code} ({elapsed:.2f}s): {error_body}")
        return {"success": False, "status": e.code, "error": error_body, "label": label}

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[{label}] Exception ({elapsed:.2f}s): {type(e).__name__}: {e}")
        return {"success": False, "error": str(e), "label": label}


def run_concurrent(requests: list, scenario_name: str) -> list:
    """Run a list of requests concurrently and return results."""
    print(f"\n{'─' * 60}")
    print(f"Scenario: {scenario_name}")
    print(f"{'─' * 60}")
    print(f"Sending {len(requests)} simultaneous requests...\n")

    results = []
    with ThreadPoolExecutor(max_workers=len(requests)) as executor:
        futures = {
            executor.submit(start_interview, requests[i], f"{scenario_name}-{i+1}"): i
            for i in range(len(requests))
        }
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                results.append({"success": False, "error": str(e), "label": f"{scenario_name}-{futures[future]+1}"})

    return results


def main():
    print("=" * 60)
    print("Concurrent Interview Start Test")
    print("=" * 60)
    print(f"Target: {BASE_URL}/interview/start")

    all_results = []

    # Parse CLI args for mode selection
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode in ("all", "dynamic"):
        all_results += run_concurrent(DYNAMIC_GAP_REQUESTS, "dynamic_gap")

    if mode in ("all", "predefined"):
        all_results += run_concurrent(PREDEFINED_REQUESTS, "predefined_questions")

    if mode not in ("all", "dynamic", "predefined"):
        print(f"\nUsage: python {sys.argv[0]} [all|dynamic|predefined]")
        sys.exit(2)

    # Summary
    print("\n" + "=" * 60)
    print("Results Summary")
    print("=" * 60)

    successes = 0
    failures = 0
    for r in all_results:
        if r.get("success"):
            successes += 1
            print(f"  {r['label']}: SUCCESS (session={r['data']['session_id']})")
        else:
            failures += 1
            print(f"  {r['label']}: FAILED ({r.get('error', 'unknown')[:200]})")

    print(f"\nTotal: {successes} success, {failures} failed")

    if failures > 0:
        print("\n*** CONCURRENCY BUG REPRODUCED ***")
        sys.exit(1)
    else:
        print("\nAll interviews started successfully - no concurrency issue detected.")
        sys.exit(0)


if __name__ == "__main__":
    main()
