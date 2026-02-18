#!/bin/bash
# Test SSE Streaming Endpoints
# Usage: ./scripts/test-stream.sh [API_KEY] [BASE_URL]

API_KEY="${1:-test-api-key}"
BASE_URL="${2:-http://localhost:8000}"
CANDIDATE_ID="test-candidate-001"
RESUME_TEXT="John Doe - Senior Python Developer with 5 years experience. Skills: Python, FastAPI, Docker, PostgreSQL, AWS. Led team of 3 developers building microservices."

echo "================================"
echo "SSE Streaming Test"
echo "================================"
echo "Base URL: $BASE_URL"
echo "Candidate: $CANDIDATE_ID"
echo ""

# Test 1: Start Interview Stream
echo ">>> Testing POST /interview/start/stream"
echo "Sending request... (events will appear as they stream)"
echo ""

START_RESPONSE=$(curl -X POST "$BASE_URL/interview/start/stream" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d "{\"candidate_id\": \"$CANDIDATE_ID\", \"resume_text\": \"$RESUME_TEXT\"}" \
  --no-buffer \
  -s)

echo ""
echo "--- Start Stream Response ---"
echo "$START_RESPONSE"
echo ""

# Extract session_id from response
SESSION_ID=$(echo "$START_RESPONSE" | grep -o '"session_id":\s*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/')

if [ -n "$SESSION_ID" ]; then
    echo "Extracted session_id: $SESSION_ID"

    # Test 2: Chat Stream
    echo ""
    echo ">>> Testing POST /interview/chat/$SESSION_ID/stream"
    echo "Sending answer... (events will appear as they stream)"
    echo ""

    ANSWER="I have been working with Python for 5 years, primarily building REST APIs with FastAPI and Flask. I led a team of 3 developers and we built a microservices architecture handling 10k requests per second."

    CHAT_RESPONSE=$(curl -X POST "$BASE_URL/interview/chat/$SESSION_ID/stream" \
      -H "Content-Type: application/json" \
      -H "X-API-Key: $API_KEY" \
      -d "{\"answer\": \"$ANSWER\"}" \
      --no-buffer \
      -s)

    echo ""
    echo "--- Chat Stream Response ---"
    echo "$CHAT_RESPONSE"
else
    echo "Could not extract session_id from response"
fi

echo ""
echo "================================"
echo "Test Complete"
echo "================================"
