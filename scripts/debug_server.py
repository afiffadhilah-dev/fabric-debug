"""
Server Diagnostic Script

Tests the Render server to debug 502 Bad Gateway errors.
Measures response times, checks connectivity, and identifies bottlenecks.

Usage:
    python scripts/debug_server.py
    python scripts/debug_server.py --base-url http://localhost:8000
    python scripts/debug_server.py --full  # Run full interview start test
"""

import argparse
import time
import httpx

DEFAULT_BASE_URL = "https://fabric-xz87.onrender.com"
DEFAULT_API_KEY = "tahuB03lat"
DEFAULT_QUESTION_SET_ID = "03b84681-2c75-4bbd-89ee-307861ec7b6b"

SAMPLE_RESUME_SHORT = "Jane Smith, Senior Engineer, 7 years experience in React, Node.js, Python."

SAMPLE_RESUME_FULL = """
Jane Smith
Senior Fullstack Engineer

PROFESSIONAL SUMMARY:
7+ years of experience building scalable web applications. Strong expertise in React, Node.js,
Python, and cloud infrastructure. Led teams of 5+ engineers and delivered high-impact products
serving 100k+ daily active users.

EXPERIENCE:

Tech Lead - Acme Corp (2021-Present)
- Lead team of 5 fullstack engineers building SaaS platform (React, Node.js, PostgreSQL)
- Architected microservices handling 150k+ daily active users
- Built real-time notification system using WebSockets and Redis pub/sub
- Implemented CI/CD pipelines with GitHub Actions, Docker, and Kubernetes

Senior Software Engineer - StartupXYZ (2019-2021)
- Developed React frontend and Node.js/Express backend for B2B analytics platform
- Built RESTful APIs and GraphQL endpoints serving 50k+ requests/day
- Designed PostgreSQL database schema with master-slave replication

Software Engineer - TechCo (2017-2019)
- Built mobile app using React Native for iOS and Android
- Integrated with REST APIs and managed state with Redux

TECHNICAL SKILLS:
- Frontend: React (expert), TypeScript, Next.js
- Backend: Node.js/Express (expert), Python/FastAPI
- Databases: PostgreSQL (expert), MongoDB, Redis
- Cloud/DevOps: AWS, Docker, Kubernetes, Terraform
"""


def timed_request(client: httpx.Client, method: str, url: str, **kwargs) -> tuple[httpx.Response | None, float, str | None]:
    """Make a request and return (response, elapsed_seconds, error)."""
    start = time.time()
    try:
        response = getattr(client, method)(url, **kwargs)
        elapsed = time.time() - start
        return response, elapsed, None
    except httpx.TimeoutException as e:
        elapsed = time.time() - start
        return None, elapsed, f"TIMEOUT after {elapsed:.1f}s: {e}"
    except httpx.ConnectError as e:
        elapsed = time.time() - start
        return None, elapsed, f"CONNECTION ERROR: {e}"
    except Exception as e:
        elapsed = time.time() - start
        return None, elapsed, f"ERROR: {e}"


def print_result(label: str, response: httpx.Response | None, elapsed: float, error: str | None):
    """Print formatted test result."""
    if error:
        print(f"  {'FAIL':<6} {label:<40} {elapsed:>7.2f}s  {error}")
    else:
        status = response.status_code
        status_icon = "OK" if status < 400 else "FAIL"
        size = len(response.content)
        print(f"  {status_icon:<6} {label:<40} {elapsed:>7.2f}s  HTTP {status}  ({size} bytes)")
        if status >= 400:
            # Show response body for errors
            try:
                body = response.text[:500]
                print(f"         Response: {body}")
            except Exception:
                pass


def run_diagnostics(base_url: str, api_key: str, question_set_id: str, run_full: bool):
    """Run all diagnostic tests."""
    base_url = base_url.rstrip("/")
    headers = {"Content-Type": "application/json", "X-API-Key": api_key}

    print(f"\n{'='*70}")
    print(f"  SERVER DIAGNOSTICS: {base_url}")
    print(f"{'='*70}")

    # --- Phase 1: Basic connectivity ---
    print(f"\n--- Phase 1: Basic Connectivity ---\n")

    # Use short timeout for basic checks, longer for interview
    client = httpx.Client(timeout=30.0)

    # Test 1: Ping (no auth)
    resp, elapsed, err = timed_request(client, "get", f"{base_url}/ping")
    print_result("/ping (no auth)", resp, elapsed, err)
    if err or (resp and resp.status_code != 200):
        print("\n  ** Server is not responding. It may be sleeping (cold start).")
        print("  ** Waiting 30s for cold start, then retrying...\n")
        time.sleep(30)
        resp, elapsed, err = timed_request(client, "get", f"{base_url}/ping")
        print_result("/ping (retry after cold start)", resp, elapsed, err)
        if err:
            print("\n  ** Server still not responding. Check Render dashboard for logs.")
            client.close()
            return

    # Test 2: Health
    resp, elapsed, err = timed_request(client, "get", f"{base_url}/health")
    print_result("/health (no auth)", resp, elapsed, err)

    # Test 3: Root
    resp, elapsed, err = timed_request(client, "get", f"{base_url}/")
    print_result("/ (root)", resp, elapsed, err)

    # --- Phase 2: Auth check ---
    print(f"\n--- Phase 2: Authentication ---\n")

    # Test without API key
    resp, elapsed, err = timed_request(
        client, "post", f"{base_url}/interview/start",
        json={"candidate_id": "test", "resume_text": "test", "mode": "dynamic_gap"},
    )
    print_result("/interview/start (no auth)", resp, elapsed, err)
    if resp and resp.status_code == 403:
        print("         Auth is working (403 without key = expected)")

    # Test with API key but bad payload
    resp, elapsed, err = timed_request(
        client, "post", f"{base_url}/interview/start",
        json={},
        headers=headers,
    )
    print_result("/interview/start (empty payload)", resp, elapsed, err)
    if resp and resp.status_code == 422:
        print("         Validation is working (422 = expected)")

    # --- Phase 3: Lightweight interview start ---
    print(f"\n--- Phase 3: Interview Start (lightweight) ---\n")

    # Use longer timeout for actual interview operations
    client_long = httpx.Client(timeout=300.0)

    # Test with minimal resume (dynamic_gap)
    payload_dynamic = {
        "candidate_id": f"diag-dynamic-{int(time.time())}",
        "resume_text": SAMPLE_RESUME_SHORT,
        "mode": "dynamic_gap",
    }
    resp, elapsed, err = timed_request(
        client_long, "post", f"{base_url}/interview/start",
        json=payload_dynamic,
        headers=headers,
    )
    print_result("dynamic_gap (short resume)", resp, elapsed, err)

    # Test with predefined_questions mode
    payload_predefined = {
        "candidate_id": f"diag-predef-{int(time.time())}",
        "resume_text": SAMPLE_RESUME_SHORT,
        "mode": "predefined_questions",
        "question_set_id": question_set_id,
    }
    resp, elapsed, err = timed_request(
        client_long, "post", f"{base_url}/interview/start",
        json=payload_predefined,
        headers=headers,
    )
    print_result("predefined_questions (short resume)", resp, elapsed, err)

    # --- Phase 4: Full resume test (optional) ---
    if run_full:
        print(f"\n--- Phase 4: Full Resume Test ---\n")

        payload_full_dynamic = {
            "candidate_id": f"diag-full-dyn-{int(time.time())}",
            "resume_text": SAMPLE_RESUME_FULL,
            "mode": "dynamic_gap",
        }
        resp, elapsed, err = timed_request(
            client_long, "post", f"{base_url}/interview/start",
            json=payload_full_dynamic,
            headers=headers,
        )
        print_result("dynamic_gap (full resume)", resp, elapsed, err)

        payload_full_predef = {
            "candidate_id": f"diag-full-pre-{int(time.time())}",
            "resume_text": SAMPLE_RESUME_FULL,
            "mode": "predefined_questions",
            "question_set_id": question_set_id,
        }
        resp, elapsed, err = timed_request(
            client_long, "post", f"{base_url}/interview/start",
            json=payload_full_predef,
            headers=headers,
        )
        print_result("predefined_questions (full resume)", resp, elapsed, err)

        # If dynamic_gap succeeded, test a chat follow-up
        if resp and resp.status_code in (200, 201):
            try:
                session_id = resp.json().get("session_id")
                if session_id:
                    print(f"\n  Testing chat follow-up on session {session_id}...")
                    chat_resp, chat_elapsed, chat_err = timed_request(
                        client_long, "post",
                        f"{base_url}/interview/chat/{session_id}",
                        json={"answer": "I have 7 years of experience with React and Node.js."},
                        headers=headers,
                    )
                    print_result(f"chat/{session_id[:8]}...", chat_resp, chat_elapsed, chat_err)
            except Exception as e:
                print(f"  Could not test chat: {e}")

    # --- Phase 5: Concurrent requests test ---
    print(f"\n--- Phase 5: Concurrent Load Test (3 pings) ---\n")

    import concurrent.futures

    def ping_server(i):
        c = httpx.Client(timeout=15.0)
        start = time.time()
        try:
            r = c.get(f"{base_url}/ping")
            return i, r.status_code, time.time() - start, None
        except Exception as e:
            return i, None, time.time() - start, str(e)
        finally:
            c.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(ping_server, i) for i in range(3)]
        for f in concurrent.futures.as_completed(futures):
            idx, status_code, elapsed, err = f.result()
            if err:
                print(f"  Ping #{idx+1}: FAIL  {elapsed:.2f}s  {err}")
            else:
                print(f"  Ping #{idx+1}: HTTP {status_code}  {elapsed:.2f}s")

    # --- Summary ---
    print(f"\n{'='*70}")
    print("  DIAGNOSIS TIPS")
    print(f"{'='*70}")
    print("""
  If /ping fails:
    -> Server is down or sleeping. Check Render dashboard.
    -> Free tier services sleep after 15min inactivity.

  If /ping works but /interview/start returns 502:
    -> Server crashes during request processing.
    -> Check Render logs for Python tracebacks.
    -> Common causes:
       - Database connection timeout (check DATABASE_URL on Render)
       - Out of memory (resume processing + LLM calls)
       - LLM API key missing or expired on server

  If short resume works but full resume 502s:
    -> Server runs out of memory or LLM call times out.
    -> Consider upgrading Render instance.

  If dynamic_gap 502s but predefined_questions works:
    -> Gap analysis (LLM call) is too heavy for the instance.

  If everything works here but simulate_interview.py fails:
    -> The simulation adds LLM answer generation load.
    -> Check if multiple simulations run concurrently.
""")

    client.close()
    client_long.close()


def main():
    parser = argparse.ArgumentParser(description="Debug Render server 502 errors")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"API base URL (default: {DEFAULT_BASE_URL})")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="API key")
    parser.add_argument("--question-set-id", default=DEFAULT_QUESTION_SET_ID, help="Question set ID for predefined mode")
    parser.add_argument("--full", action="store_true", help="Run full interview start test with large resume")
    args = parser.parse_args()

    run_diagnostics(args.base_url, args.api_key, args.question_set_id, args.full)


if __name__ == "__main__":
    main()
