# API Integration Guide

Quick start guide for integrating with the Fabric interview platform. For complete endpoint reference, see the interactive [Swagger documentation](/docs).

---

## Authentication

All API endpoints (except `/ping` and `/health`) require an API key.

```bash
curl -H "X-API-Key: your-api-key" https://api.example.com/interview/start
```

---

## Workflow 1: Conduct an Interview

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/interview/start` | Start a new interview session |
| POST | `/interview/chat/{session_id}` | Submit candidate answer |
| GET | `/interview/session/{session_id}/messages` | Get conversation history |

### 1. Start Interview

```http
POST /interview/start

{
  "candidate_id": "candidate-123",
  "mode": "predefined_questions",
  "question_set_id": "your-question-set-uuid",
  "resume_text": "(optional) candidate resume..."
}
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "question": "How would you design a rate limiter?",
  "mode": "predefined_questions"
}
```

### 2. Submit Answers

```http
POST /interview/chat/{session_id}

{
  "answer": "I would use a token bucket algorithm..."
}
```

**Response (continues):**
```json
{
  "question": "Explain the difference between SQL and NoSQL databases.",
  "completed": false
}
```

**Response (complete):**
```json
{
  "question": null,
  "completed": true,
  "termination_reason": "complete",
  "completion_message": "Thank you for sharing your experiences."
}
```

### 3. Get Conversation History

```http
GET /interview/session/{session_id}/messages
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "messages": [
    {"role": "interviewer", "content": "How would you design a rate limiter?"},
    {"role": "candidate", "content": "I would use a token bucket algorithm..."}
  ]
}
```

---

## Workflow 2: Set Up Question Sets

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/predefined/roles` | Create a new role |
| POST | `/predefined/question-sets/bulk` | Create question set with questions |
| POST | `/predefined/import-from-document` | Import questions from document |
| POST | `/predefined/question-sets/{id}/activate` | Activate a question set |

> **Important:** You must create a Role first before creating or importing Question Sets. Each Question Set belongs to a specific Role.

### Understanding `is_active`

Only **one question set can be active per role** at a time. This allows you to manage multiple versions of questions for different recruitment periods:

- **Q1 Recruitment:** Activate "Backend Screen Q1 2024"
- **Q2 Recruitment:** Activate "Backend Screen Q2 2024" (automatically deactivates Q1)

When starting an interview, the system uses the currently active question set for the specified role.

### 1. Create a Role

```http
POST /predefined/roles

{
  "name": "Backend Developer",
  "level": "Senior",
  "description": "Server-side development with APIs and databases"
}
```

**Response:**
```json
{
  "id": "role-uuid-here",
  "name": "Backend Developer",
  "level": "Senior",
  "is_active": true
}
```

### 2. Create Question Set

```http
POST /predefined/question-sets/bulk

{
  "role_id": "role-uuid",
  "name": "Backend Technical Screen",
  "version": "v1.0",
  "is_active": true,
  "questions": [
    {
      "category": "System Design",
      "question_text": "How would you design a rate limiter?",
      "what_assesses": ["system design", "scalability"],
      "order": 1,
      "is_required": true
    }
  ]
}
```

**Response:**
```json
{
  "id": "question-set-uuid",
  "name": "Backend Technical Screen",
  "version": "v1.0",
  "is_active": true,
  "questions_count": 1
}
```

### Alternative: Import from Document

Instead of creating questions manually, you can import from a document. This will automatically create the Role (if it doesn't exist) and Question Set.

```http
POST /predefined/import-from-document
Content-Type: multipart/form-data

file: (your document file)
role_name: Backend Developer
role_level: Senior
question_set_name: Technical Screen Q1 2024
is_active: true
```

Supported formats: `.md`, `.docx`, `.txt`, `.pdf`

> **Example:** See [Fullstack_developer_senior.md](./Fullstack_developer_senior.md) for a properly formatted document.

### 3. Activate Question Set

Switch to a different question set for the role. This automatically deactivates other question sets for the same role.

```http
POST /predefined/question-sets/{question_set_id}/activate
```

**Response:**
```json
{
  "id": "question-set-uuid",
  "is_active": true
}
```

**Example use case:** When Q2 recruitment starts, activate the Q2 question set:
```http
POST /predefined/question-sets/{q2-question-set-id}/activate
```
All new interviews for that role will now use the Q2 questions.

---

## Workflow 3: Generate Candidate Profile

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/summarization/analyze-session` | Trigger profile analysis (async) |
| GET | `/summarization/task-status/{task_id}` | Poll task status |
| GET | `/summarization/profile` | Get structured profile JSON |

### 1. Trigger Analysis

```http
POST /summarization/analyze-session

{
  "session_id": "interview-session-id"
}
```

**Response (202 Accepted):**
```json
{
  "task_id": "task-uuid",
  "status": "INITIATED",
  "message": "Session summarization task queued..."
}
```

### 2. Poll Status

```http
GET /summarization/task-status/{task_id}
```

**Response:**
```json
{
  "task_id": "task-uuid",
  "status": "SUCCESS"
}
```

### 3. Get Profile

```http
GET /summarization/profile?candidate_id=candidate-123
```

**Response:**
```json
{
  "candidate_id": "candidate-123",
  "profile": {
    "skills": [...],
    "behavioral_observations": [...],
    "aspirations": [...],
    "gaps": [...]
  },
  "status": "success"
}
```

---

## Workflow 4: Retrieve & Manage Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/interview/sessions/{candidate_id}` | List all sessions for a candidate |
| GET | `/interview/session/{session_id}` | Get session details |
| GET | `/summarization/profile-summary` | Get profile as markdown |

### List Sessions for a Candidate

```http
GET /interview/sessions/{candidate_id}
```

**Response:**
```json
{
  "candidate_id": "candidate-123",
  "sessions": [
    {
      "id": "session-uuid-1",
      "status": "completed",
      "termination_reason": "complete",
      "questions_asked": 5,
      "created_at": "2024-01-15T10:00:00Z"
    },
    {
      "id": "session-uuid-2",
      "status": "in_progress",
      "questions_asked": 2,
      "created_at": "2024-01-20T14:30:00Z"
    }
  ]
}
```

### Get Session Details

```http
GET /interview/session/{session_id}
```

**Response:**
```json
{
  "id": "session-uuid",
  "candidate_id": "candidate-123",
  "status": "completed",
  "termination_reason": "complete",
  "questions_asked": 5,
  "completeness_score": 0.85,
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:45:00Z"
}
```

### Get Profile Summary (Markdown)

For a human-readable summary instead of structured JSON:

```http
GET /summarization/profile-summary?candidate_id=candidate-123&summary_type=GENERAL
```

**Response:**
```json
{
  "candidate_id": "candidate-123",
  "summary_type": "GENERAL",
  "markdown": "## Candidate Profile\n\n### Skills\n- **Python**: 5 years, production experience...\n\n### Strengths\n- Strong system design skills...",
  "status": "success"
}
```

**Available summary types:**
| Type | Description |
|------|-------------|
| `GENERAL` | Overall candidate profile |
| `TECHNICAL` | Technical skills focus |
| `BEHAVIORAL` | Soft skills and behaviors |

---

## Streaming (SSE)

For real-time UI updates, use streaming endpoints:

| Endpoint | Description |
|----------|-------------|
| `POST /interview/start/stream` | Stream interview initialization |
| `POST /interview/chat/{id}/stream` | Stream answer processing |

### Event Types

| Event | Description |
|-------|-------------|
| `session` | Session ID at start |
| `node` | Processing step completed |
| `token` | LLM token for typewriter effect |
| `progress` | Answer processing stage |
| `complete` | Final result |
| `error` | Error occurred |

---

## Additional Resources

- **Swagger UI:** `/docs`
- **OpenAPI Schema:** `/openapi.json`
- **ReDoc:** `/redoc`
