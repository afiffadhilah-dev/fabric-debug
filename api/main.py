import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.predefined_questions import router as predefined_questions_router
from api.routes.interview import router as interview_router
from api.routes.candidate_summarization import router as candidate_summarization_router
from api.routes.candidate import router as candidate_router

DESCRIPTION = """
AI-powered interview platform for conducting technical interviews, extracting skills, and generating candidate profiles.

## Authentication

All endpoints (except `/ping` and `/health`) require an API key via the `X-API-Key` header.

Use the **Authorize** button above to set your API key for testing.

## Quick Start

1. **Start an interview** → `POST /interview/start` with candidate ID and resume
2. **Submit answers** → `POST /interview/chat/{session_id}` with candidate's answer
3. **Get results** → `GET /interview/session/{session_id}/messages` for full conversation

## Interview Modes

| Mode | Description |
|------|-------------|
| `dynamic_gap` | AI analyzes resume and asks adaptive questions |
| `predefined_questions` | Uses a predefined question set |

## Streaming

For real-time UI updates, use the `/stream` endpoints which return Server-Sent Events (SSE).
"""

tags_metadata = [
    {
        "name": "Health",
        "description": "Health check endpoints. No authentication required.",
    },
    {
        "name": "Interview",
        "description": "Conduct AI-powered technical interviews. Start → Submit answers → Get results.",
    },
    {
        "name": "Predefined Questions",
        "description": "Manage predefined interview question sets. Hierarchy: Role → Question Set → Questions.",
    },
    {
        "name": "Summarization",
        "description": "Generate candidate profile summaries from completed interviews. Uses async background tasks.",
    },
]

app = FastAPI(
    title="Fabric API",
    description=DESCRIPTION,
    version="1.0.0",
    openapi_tags=tags_metadata,
)

# Configure CORS
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
def root():
    """Root endpoint with API information and documentation links"""
    return {
        "message": "Welcome to Fabric API",
        "version": "1.0.0",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        },
        "authentication": {
            "type": "API Key",
            "header": "X-API-Key",
            "note": "Required for all endpoints except /ping and /health"
        },
        "endpoints": {
            "health": "/health",
            "ping": "/ping",
            "predefined_questions": "/predefined",
            "interview": "/interview",
            "candidate_summarization": "/summarization"
        }
    }


# Health check endpoints (public - no authentication required)
@app.get("/ping", tags=["Health"])
def ping():
    """Simple ping endpoint to check if API is responding. No authentication required."""
    return {"message": "pong"}


@app.get("/health", tags=["Health"])
def health():
    """Health check endpoint with basic status information. No authentication required."""
    return {
        "status": "healthy",
        "service": "AI Agents API",
        "version": "1.0.0"
    }


# Register routers
app.include_router(predefined_questions_router)
app.include_router(interview_router)
app.include_router(candidate_summarization_router)
app.include_router(candidate_router)