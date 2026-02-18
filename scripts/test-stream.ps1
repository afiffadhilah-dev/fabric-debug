# Test SSE Streaming Endpoints
# Usage: .\scripts\test-stream.ps1 [-ApiKey "your-key"] [-BaseUrl "http://localhost:8000"]

param(
    [string]$ApiKey = "tahuB03lat",
    [string]$BaseUrl = "http://localhost:8000",
    [string]$CandidateId = "test-candidate-001",
    [string]$ResumeText = "John Doe - Senior Python Developer with 5 years experience. Skills: Python, FastAPI, Docker, PostgreSQL, AWS. Led team of 3 developers building microservices."
)

Write-Host "================================" -ForegroundColor Cyan
Write-Host "SSE Streaming Test" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Base URL: $BaseUrl"
Write-Host "Candidate: $CandidateId"
Write-Host ""

# Test 1: Start Interview Stream
Write-Host ">>> Testing POST /interview/start/stream" -ForegroundColor Yellow
Write-Host "Sending request... (events will appear as they stream)" -ForegroundColor Gray
Write-Host ""

# Build JSON body (escape quotes for curl)
$body = "{`"candidate_id`": `"$CandidateId`", `"resume_text`": `"$ResumeText`"}"

# Run curl as single line
$startResult = & curl.exe -X POST "$BaseUrl/interview/start/stream" -H "Content-Type: application/json" -H "X-API-Key: $ApiKey" -d $body --no-buffer -s 2>&1

Write-Host ""
Write-Host "--- Start Stream Response ---" -ForegroundColor Green
Write-Host $startResult
Write-Host ""

# Extract session_id from the response
if ($startResult) {
    $sessionMatch = [regex]::Match($startResult, '"session_id":\s*"([^"]+)"')
    if ($sessionMatch.Success) {
        $sessionId = $sessionMatch.Groups[1].Value
        Write-Host "Extracted session_id: $sessionId" -ForegroundColor Cyan

        # Test 2: Chat Stream
        Write-Host ""
        Write-Host ">>> Testing POST /interview/chat/$sessionId/stream" -ForegroundColor Yellow
        Write-Host "Sending answer... (events will appear as they stream)" -ForegroundColor Gray
        Write-Host ""

        $answer = "I have been working with Python for 5 years, primarily building REST APIs with FastAPI and Flask. I led a team of 3 developers."
        $chatBody = "{`"answer`": `"$answer`"}"

        $chatResult = & curl.exe -X POST "$BaseUrl/interview/chat/$sessionId/stream" -H "Content-Type: application/json" -H "X-API-Key: $ApiKey" -d $chatBody --no-buffer -s 2>&1

        Write-Host ""
        Write-Host "--- Chat Stream Response ---" -ForegroundColor Green
        Write-Host $chatResult
    } else {
        Write-Host "Could not extract session_id from response" -ForegroundColor Red
    }
} else {
    Write-Host "No response received from server" -ForegroundColor Red
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Test Complete" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
