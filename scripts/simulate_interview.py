"""
Interview Simulation Script

Simulates a complete interview session by:
1. Starting an interview via API
2. Using LLM to generate realistic candidate answers based on persona
3. Continuing until the interview terminates naturally or max answers reached

Usage:
    python scripts/simulate_interview.py [--base-url URL] [--api-key KEY] [--persona PERSONA] [--mode MODE] [--user-name NAME]

Examples:
    # Local with default (predefined_questions mode, uses DEFAULT_QUESTION_SET_ID)
    python scripts/simulate_interview.py

    # Staging with evasive persona
    python scripts/simulate_interview.py --persona evasive

    # Run with dynamic_gap mode
    python scripts/simulate_interview.py --mode dynamic_gap

    # List available personas
    python scripts/simulate_interview.py --list-personas

Modes:
    - predefined_questions: Uses a predefined question set (default)
    - dynamic_gap: Dynamically identifies skill gaps from resume

Personas:
    - detailed: Thorough, provides comprehensive answers (default)
    - concise: Direct and to-the-point answers
    - nervous: Less confident, sometimes vague
    - evasive: Avoids specifics, gives generic answers
    - storyteller: Answers through narratives and stories

Requires:
    pip install httpx
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.llm_service import LLMService

# === CONSTANTS ===
# DEFAULT_BASE_URL = "https://fabric-xz87.onrender.com" # production
DEFAULT_BASE_URL = "https://fabric-free.onrender.com" # production free
# DEFAULT_BASE_URL = "https://fabric-api-jxv8.onrender.com" # staging
DEFAULT_QUESTION_SET_ID = "03b84681-2c75-4bbd-89ee-307861ec7b6b"  # stagging and production
# DEFAULT_BASE_URL = "http://localhost:8000"
# DEFAULT_QUESTION_SET_ID = "7f602e51-8aa4-4e70-9204-6f474550ed8e"  # local
DEFAULT_API_KEY = "tahuB03lat"
DEFAULT_USER_NAME = "Jane Smith"
DEFAULT_USER_EMAIL = "jane.smith@example.com"
DEFAULT_MAX_ANSWERS = 100
DEFAULT_MODE = "predefined_questions"



# === PERSONAS ===
# Different candidate personalities for simulation variety
PERSONAS = {
    "detailed": {
        "name": "Detailed Expert",
        "description": "Thorough, provides comprehensive answers with specific examples and metrics",
        "traits": """
- Always provides detailed, comprehensive answers
- Includes specific numbers, metrics, and concrete examples
- Explains the "why" behind decisions
- Enthusiastic about sharing technical knowledge
- Gives context about team size, scale, and impact
- Sometimes goes deeper than asked, showing expertise
"""
    },
    "concise": {
        "name": "Concise Professional",
        "description": "Direct and to-the-point, answers exactly what's asked",
        "traits": """
- Gives direct, focused answers without unnecessary detail
- Answers exactly what's asked, no more
- Professional and efficient communication style
- Provides specifics only when directly relevant
- Waits for follow-up questions before elaborating
"""
    },
    "nervous": {
        "name": "Nervous Junior",
        "description": "Less confident, sometimes vague, needs prompting",
        "traits": """
- Slightly uncertain in responses, uses hedging language ("I think", "maybe")
- Sometimes gives shorter answers that need follow-up
- Occasionally asks for clarification
- May downplay experience or use vague timeframes
- Shows enthusiasm but lacks confidence in articulation
"""
    },
    "evasive": {
        "name": "Evasive Candidate",
        "description": "Avoids specifics, gives generic answers",
        "traits": """
- Gives vague, non-specific answers
- Avoids mentioning concrete numbers or timeframes
- Uses generic statements like "I have experience with that"
- Redirects questions or answers tangentially
- Rarely provides unprompted detail
"""
    },
    "storyteller": {
        "name": "Storyteller",
        "description": "Answers through narratives and project stories",
        "traits": """
- Frames answers as stories from past projects
- Sets context with team dynamics and challenges faced
- Describes the journey: problem → approach → solution → outcome
- Makes answers memorable through narrative structure
- Connects technical details to business impact
"""
    },
}

DEFAULT_PERSONA = "detailed"

SAMPLE_RESUME = """
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
- Conducted technical interviews and mentored 3 junior developers
- Collaborated with product team on analytics (conversion rates, retention metrics)

Senior Software Engineer - StartupXYZ (2019-2021)

- Developed React frontend and Node.js/Express backend for B2B analytics platform
- Built RESTful APIs and GraphQL endpoints serving 50k+ requests/day
- Designed PostgreSQL database schema with master-slave replication
- Implemented event-driven architecture using RabbitMQ
- Deployed to AWS (EC2, RDS, S3, Lambda) using Terraform

Software Engineer - TechCo (2017-2019)

- Built mobile app using React Native for iOS and Android
- Integrated with REST APIs and managed state with Redux
- Worked with PostgreSQL and MongoDB databases
- Participated in code reviews and sprint planning

TECHNICAL SKILLS:

- Frontend: React (expert), TypeScript, Next.js, HTML/CSS, Responsive design
- Mobile: React Native, iOS/Android deployment
- Backend: Node.js/Express (expert), Python/FastAPI, Go (basic)
- Databases: PostgreSQL (expert), MongoDB, Redis
- Real-time: WebSockets, Server-Sent Events, Socket.io
- Message Queues: RabbitMQ, Kafka (basic)
- Cloud/DevOps: AWS (EC2, RDS, S3, Lambda), Docker, Kubernetes, Terraform
- CI/CD: GitHub Actions, Jenkins
- Testing: Jest, React Testing Library, Cypress, TDD practices

LEADERSHIP & SOFT SKILLS:

- Led hiring for 3 engineer positions (designed take-home tests, conducted interviews)
- Mentored junior developers through pair programming and code reviews
- Collaborated with product managers on roadmap prioritization
- Presented technical designs to stakeholders
"""

ANSWER_GENERATION_PROMPT = """You are simulating a candidate in a technical interview.
You are playing the role of a senior fullstack engineer with 7 years of experience.

=== PERSONA ===
You must embody this persona throughout the interview:
{persona_traits}

=== INSTRUCTIONS ===
Given the interview question and resume context, generate a realistic answer
that matches your persona. The answer should:
- Be conversational and natural (not too formal)
- Stay consistent with the persona traits above
- Draw from the resume experience when relevant
- Feel like a real person talking, not a script

Resume for context:
{resume}

Previous conversation:
{conversation_history}

Current question: {question}

Generate a realistic candidate answer matching your persona (respond only with the answer, no labels or prefixes):"""


class InterviewSimulator:
    """Simulates an interview session using API calls and LLM-generated answers."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        max_answers: int = DEFAULT_MAX_ANSWERS,
        resume_text: str = SAMPLE_RESUME,
        persona: str = DEFAULT_PERSONA,
        verbose: bool = True,
        mode: str = "dynamic_gap",
        question_set_id: str | None = None,
        language: str | None = None,
        user_name: str | None = None,
        user_email: str | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.max_answers = max_answers
        self.resume_text = resume_text
        self.verbose = verbose
        self.mode = mode
        self.question_set_id = question_set_id
        self.lang = language
        self.user_name = user_name
        self.user_email = user_email

        # Set persona
        if persona not in PERSONAS:
            raise ValueError(f"Unknown persona: {persona}. Available: {list(PERSONAS.keys())}")
        self.persona = PERSONAS[persona]
        self.persona_name = persona

        # Initialize LLM for answer generation
        self.llm_service = LLMService.fast()

        # HTTP client with longer timeout for API calls (especially finalization)
        self.client = httpx.Client(timeout=300.0)  # 5 minutes for slow staging

        # Interview state
        self.session_id = None
        self.conversation_history = []
        self.answer_count = 0

    def _headers(self) -> dict:
        """Get common headers for API requests."""
        return {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
        }

    def _log(self, message: str, prefix: str = ""):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(f"{prefix}{message}")

    def _log_question(self, question: str):
        """Log interviewer question."""
        self._log(f"\n{'='*60}")
        self._log(f"[INTERVIEWER] Question #{self.answer_count + 1}:")
        self._log(f"{question}")
        self._log(f"{'='*60}")

    def _log_answer(self, answer: str):
        """Log candidate answer."""
        self._log(f"\n[CANDIDATE] Answer:")
        self._log(f"{answer}")
        self._log(f"{'-'*60}")

    def generate_answer(self, question: str) -> str:
        """Use LLM to generate a realistic candidate answer based on persona."""
        # Build conversation history string (last 8 Q&A pairs for context)
        history_str = ""
        for item in self.conversation_history[-8:]:
            history_str += f"Q: {item['question']}\nA: {item['answer']}\n\n"

        prompt = ANSWER_GENERATION_PROMPT.format(
            persona_traits=self.persona["traits"],
            resume=self.resume_text,
            conversation_history=history_str if history_str else "(Start of interview)",
            question=question,
        )

        try:
            answer = self.llm_service.generate(
                prompt=question,
                system_prompt=prompt,
            )
            return answer.strip()
        except Exception as e:
            self._log(f"[ERROR] Failed to generate answer: {e}")
            # Fallback generic answer
            return "I have experience with that. In my previous role, I worked on similar challenges and learned a lot from the experience."

    def upsert_candidate(self) -> str:
        """Create or update candidate via API to ensure org isolation. Returns candidate_id."""
        self._log("\n[Upserting candidate...]")

        payload = {
            "name": self.user_name or DEFAULT_USER_NAME,
            "email": self.user_email or DEFAULT_USER_EMAIL,
        }

        try:
            response = self.client.post(
                f"{self.base_url}/candidates/",
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()
            candidate_id = data["id"]
            self._log(f"Candidate ready: {candidate_id} (name: {data.get('name')})")
            return candidate_id

        except httpx.HTTPStatusError as e:
            self._log(f"[ERROR] Failed to upsert candidate: HTTP {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            self._log(f"[ERROR] Failed to upsert candidate: {e}")
            raise

    def start_interview(self) -> dict:
        """Start a new interview session via API."""
        self._log("\n" + "=" * 60)
        self._log("Starting Interview Simulation")
        self._log(f"Base URL: {self.base_url}")
        self._log(f"Mode: {self.mode}")
        if self.question_set_id:
            self._log(f"Question Set ID: {self.question_set_id}")
        self._log(f"Persona: {self.persona['name']} ({self.persona_name})")
        self._log(f"User Name: {self.user_name or '(not set)'}")
        self._log(f"Language: {self.lang or 'en (default)'}")
        self._log(f"Max Answers: {self.max_answers}")
        self._log("=" * 60)

        # Upsert candidate first to ensure org isolation
        candidate_id = self.upsert_candidate()

        payload = {
            "candidate_id": candidate_id,
            "resume_text": self.resume_text,
            "mode": self.mode,
        }
        if self.user_name:
            payload["user"] = self.user_name
        if self.question_set_id:
            payload["question_set_id"] = self.question_set_id
        if self.lang:
            payload["language"] = self.lang

        try:
            response = self.client.post(
                f"{self.base_url}/interview/start",
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()

            self.session_id = data["session_id"]
            self._log(f"\nSession started: {self.session_id}")

            return data

        except httpx.HTTPStatusError as e:
            self._log(f"[ERROR] HTTP {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            self._log(f"[ERROR] Failed to start interview: {e}")
            raise

    def continue_interview(self, answer: str, max_retries: int = 2) -> dict:
        """Continue interview with candidate's answer via API."""
        if not self.session_id:
            raise ValueError("No active session. Call start_interview() first.")

        payload = {"answer": answer}

        for attempt in range(max_retries + 1):
            try:
                response = self.client.post(
                    f"{self.base_url}/interview/chat/{self.session_id}",
                    json=payload,
                    headers=self._headers(),
                )
                response.raise_for_status()
                return response.json()

            except httpx.TimeoutException as e:
                if attempt < max_retries:
                    self._log(f"[RETRY] Timeout on attempt {attempt + 1}, retrying...")
                    time.sleep(2)
                    continue
                self._log(f"[ERROR] Timeout after {max_retries + 1} attempts: {e}")
                raise
            except httpx.HTTPStatusError as e:
                self._log(f"[ERROR] HTTP {e.response.status_code}: {e.response.text}")
                raise
            except Exception as e:
                self._log(f"[ERROR] Failed to continue interview: {e}")
                raise

    def run(self) -> dict:
        """Run the full interview simulation until completion."""
        start_time = time.time()

        # Start interview
        start_response = self.start_interview()
        current_question = start_response["question"]

        # Main interview loop
        while self.answer_count < self.max_answers:
            # Log the question
            self._log_question(current_question)

            # Generate answer using LLM
            self._log("\n[Generating answer...]")
            answer = self.generate_answer(current_question)
            self._log_answer(answer)

            # Store in conversation history
            self.conversation_history.append({
                "question": current_question,
                "answer": answer,
            })

            # Send answer to API
            self.answer_count += 1
            self._log(f"\n[Sending answer #{self.answer_count} to API...]")

            response = self.continue_interview(answer)

            # Check if interview is complete
            if response.get("completed"):
                self._log("\n" + "=" * 60)
                self._log("INTERVIEW COMPLETED")
                self._log("=" * 60)
                self._log(f"Termination Reason: {response.get('termination_reason')}")
                if response.get("completion_message"):
                    self._log(f"\n[INTERVIEWER] Closing Message:")
                    self._log(response.get("completion_message"))
                break

            # Get next question
            current_question = response.get("question")
            if not current_question:
                self._log("[WARNING] No question received but interview not marked complete")
                break

        # Summary
        elapsed_time = time.time() - start_time
        summary = {
            "session_id": self.session_id,
            "persona": self.persona_name,
            "total_answers": self.answer_count,
            "completed": response.get("completed", False),
            "termination_reason": response.get("termination_reason"),
            "elapsed_seconds": round(elapsed_time, 2),
            "conversation": self.conversation_history,
        }

        self._log("\n" + "=" * 60)
        self._log("SIMULATION SUMMARY")
        self._log("=" * 60)
        self._log(f"Session ID: {self.session_id}")
        self._log(f"Persona: {self.persona['name']}")
        self._log(f"Total Q&A: {self.answer_count}")
        self._log(f"Completed: {summary['completed']}")
        self._log(f"Termination Reason: {summary['termination_reason']}")
        self._log(f"Elapsed Time: {summary['elapsed_seconds']}s")

        return summary

    def close(self):
        """Close the HTTP client."""
        self.client.close()


def main():
    # Build persona choices for help text
    persona_choices = list(PERSONAS.keys())
    persona_help = f"Candidate persona ({', '.join(persona_choices)}). Default: {DEFAULT_PERSONA}\n"
    for key, val in PERSONAS.items():
        persona_help += f"  - {key}: {val['description']}\n"

    parser = argparse.ArgumentParser(
        description="Simulate an interview session with LLM-generated answers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"API base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--api-key",
        default=DEFAULT_API_KEY,
        help="API key for authentication",
    )
    parser.add_argument(
        "--max-answers",
        type=int,
        default=DEFAULT_MAX_ANSWERS,
        help=f"Maximum number of answers before stopping (default: {DEFAULT_MAX_ANSWERS})",
    )
    parser.add_argument(
        "--persona",
        choices=persona_choices,
        default=DEFAULT_PERSONA,
        help=persona_help,
    )
    parser.add_argument(
        "--user-name",
        type=str,
        default=DEFAULT_USER_NAME,
        help=f"Candidate name sent as 'user' field (default: {DEFAULT_USER_NAME})",
    )
    parser.add_argument(
        "--user-email",
        type=str,
        default=DEFAULT_USER_EMAIL,
        help=f"Candidate email for upsert lookup (default: {DEFAULT_USER_EMAIL})",
    )
    parser.add_argument(
        "--lang",
        type=str,
        default=None,
        help="ISO 639-1 language code for interview (e.g. 'id', 'es', 'fr'). Default: English.",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path for JSON results",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output",
    )
    parser.add_argument(
        "--list-personas",
        action="store_true",
        help="List available personas and exit",
    )
    parser.add_argument(
        "--mode",
        choices=["dynamic_gap", "predefined_questions"],
        default=DEFAULT_MODE,
        help=f"Interview mode (default: {DEFAULT_MODE})",
    )
    parser.add_argument(
        "--question-set-id",
        type=str,
        default=DEFAULT_QUESTION_SET_ID or None,
        help="UUID of predefined question set (required if mode=predefined_questions)",
    )
    args = parser.parse_args()

    # List personas and exit if requested
    if args.list_personas:
        print("\nAvailable Personas:\n")
        for key, val in PERSONAS.items():
            print(f"  {key}:")
            print(f"    {val['name']} - {val['description']}")
            print(f"    Traits:{val['traits']}")
        return

    # Validate predefined_questions mode requires question_set_id
    if args.mode == "predefined_questions" and not args.question_set_id:
        parser.error("--question-set-id is required when --mode=predefined_questions")

    simulator = InterviewSimulator(
        base_url=args.base_url,
        api_key=args.api_key,
        max_answers=args.max_answers,
        persona=args.persona,
        verbose=not args.quiet,
        mode=args.mode,
        question_set_id=args.question_set_id,
        language=args.lang,
        user_name=args.user_name,
        user_email=args.user_email,
    )

    try:
        result = simulator.run()

        # Save results if output path specified
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\nResults saved to: {args.output}")

    except KeyboardInterrupt:
        print("\n\n[Interrupted by user]")
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        sys.exit(1)
    finally:
        simulator.close()


if __name__ == "__main__":
    main()
