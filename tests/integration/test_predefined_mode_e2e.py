"""
End-to-End test for predefined questions mode.

Tests complete interview flow: start -> answer questions -> completion -> skill extraction.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlmodel import Session, create_engine, SQLModel
from agents.conversational.service import ConversationalInterviewService
from utils.llm_service import LLMService
from utils.prompt_loader import PromptLoader
from models.candidate import Candidate
from config.settings import settings
import json


# Sample resume for testing
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


# Predefined answers for common question categories
PREDEFINED_ANSWERS = {
    "GENERAL INFORMATION": """
    I'm currently a Tech Lead at Acme Corp, leading a team of 5 fullstack engineers.
    We build a B2B SaaS platform that serves enterprise clients. My main responsibilities
    include architecture decisions, code reviews, mentoring team members, and ensuring
    we deliver quality features on schedule. I've worked on products ranging from internal
    tools to customer-facing applications serving over 150k daily active users.
    """,

    "LEADERSHIP EXPERIENCE": """
    I've led a team of 5 engineers for the past 2 years at Acme Corp. My leadership involves:
    - Daily standups and sprint planning
    - Mentoring 3 junior developers through pair programming and code reviews
    - Making architecture decisions and ensuring code quality
    - Conducting technical interviews and designing assessment tests
    - Resolving conflicts and unblocking team members
    - Working with product team on prioritization and trade-offs

    I focus on enabling team performance rather than micromanaging. I hold weekly 1-on-1s
    and help team members grow their technical skills.
    """,

    "PRODUCT ANALYTICS EXPERIENCE": """
    I work closely with our product team on analytics. We track metrics like:
    - Daily Active Users (DAU) - currently 150k+
    - Conversion rates through signup funnel (improved from 12% to 18% last quarter)
    - Feature adoption rates
    - API response times and error rates

    For example, we noticed drop-off in the onboarding flow, so I analyzed the data,
    identified the bottleneck, and we redesigned that step - which improved conversion by 25%.
    Data drives most of our technical and product decisions.
    """,

    "FRONTEND DEVELOPMENT": """
    I've primarily worked with React for the past 7 years, along with TypeScript and Next.js.
    React is my favorite because:
    - Large ecosystem with great libraries
    - Component reusability makes code maintainable
    - Strong typing with TypeScript catches bugs early
    - Great performance with proper optimization

    I've also used Vue.js on a smaller project, but prefer React for its flexibility
    and community support. I focus on writing clean, testable components and following
    best practices like hooks, context API, and performance optimization with React.memo.
    """,

    "MOBILE DEVELOPMENT": """
    I have about 2 years of mobile development experience with React Native at TechCo.
    I built a cross-platform app for iOS and Android from scratch, handling:
    - Navigation with React Navigation
    - State management with Redux
    - API integration
    - Push notifications
    - App store deployment

    I've also done some native iOS work using Xcode and Swift for performance-critical
    features. I prefer React Native for cross-platform projects because it allows code
    sharing and faster development, but I'd use native when performance is critical.
    """,

    "REACTIVE APPLICATIONS": """
    I've built several real-time features:

    1. Real-time notifications at Acme Corp using WebSockets and Redis pub/sub
       - Users get instant updates when events occur
       - Handled message routing to correct users
       - Implemented reconnection logic and offline queue

    2. Live dashboard with Server-Sent Events (SSE) for streaming analytics

    Technologies used: Socket.io, WebSockets, Redis pub/sub, and SSE. I chose
    WebSockets for bidirectional communication and SSE for one-way streaming.
    """,

    "DATA CONFLICTS": """
    In our real-time system, we handled conflicts using:
    - Timestamp-based versioning for concurrent updates
    - Optimistic updates with rollback on conflict
    - Idempotency keys for duplicate message handling
    - Last-write-wins strategy with conflict warnings to users

    For example, when two users edit the same document, we use operational transformation
    to merge changes and show conflict markers when automatic merge fails. We also
    implemented event sourcing for audit trails.
    """,

    "BACKEND DEVELOPMENT": """
    I've worked extensively with Node.js/Express (5+ years) and Python/FastAPI (2 years).
    Also dabbled in Go for a high-performance service.

    Node.js is my favorite because:
    - JavaScript/TypeScript across full stack
    - Great async performance with event loop
    - Huge npm ecosystem
    - Easy to hire developers

    Python is excellent for data processing and ML integrations. I've built RESTful APIs,
    GraphQL endpoints, and microservices with both languages.
    """,

    "SYSTEM DESIGN": """
    Yes, I've architected microservices from scratch at Acme Corp:
    - Split monolith into 8 services (user, auth, billing, notifications, etc.)
    - Services communicate via REST APIs and RabbitMQ message queue
    - Each service has its own database (polyglot persistence)
    - API gateway for routing and rate limiting
    - Service discovery with Kubernetes

    I also implemented event-driven architecture using RabbitMQ at StartupXYZ for
    background jobs like email sending, report generation, and data sync. We used
    dead-letter queues for error handling.
    """,

    "DATABASE EXPERIENCE": """
    SQL: PostgreSQL (expert level - 7 years). I've worked with complex queries, indexing,
    replication (master-slave), partitioning, and query optimization.

    NoSQL: MongoDB for document storage, Redis for caching and pub/sub.

    Graph databases: Limited experience with Neo4j for a recommendation engine prototype.

    Cassandra/ClickHouse: No production experience, but familiar with concepts.

    I choose databases based on use case: PostgreSQL for transactional data, MongoDB
    for flexible schemas, Redis for caching, and would use Cassandra for time-series data.
    """,

    "MESSAGING": """
    Kafka: Basic experience as consumer, reading events from stream. Haven't set up
    producers yet but understand the architecture.

    RabbitMQ: Extensive experience (2+ years) as both producer and consumer. Built
    background job systems with work queues, topic exchanges, and dead-letter queues.
    """,

    "DATABASE TOPOLOGY": """
    I've worked with various setups:
    - Docker containers for local development
    - Kubernetes StatefulSets for production databases
    - AWS RDS with multi-AZ deployment (master-slave replication)
    - Redis cluster with 3 master nodes and replicas
    - PostgreSQL with streaming replication for read replicas

    I've worked with both single-node (dev/staging) and multi-node clusters (production).
    Master-slave replication is standard for us - writes go to master, reads distributed
    across replicas.
    """,

    "API DESIGN": """
    Beyond REST and GraphQL, I've worked with:
    - gRPC for internal service-to-service communication (better performance)
    - WebSocket APIs for real-time bidirectional communication
    - Server-Sent Events for server-to-client streaming

    GraphQL: I've built GraphQL APIs using Apollo Server and consumed them from React
    frontends. I like GraphQL for reducing over-fetching and giving clients flexibility,
    but REST is simpler for straightforward CRUD operations.
    """,

    "PRODUCTION SCALE": """
    My biggest project is the current SaaS platform at Acme Corp:
    - 150k+ daily active users (DAU)
    - 10M+ API requests per day
    - Team of 5 engineers
    - Built over 2 years
    - Microservices architecture with 8 services
    - Deployed on Kubernetes (AWS EKS)

    Challenges included: scaling WebSocket connections, optimizing database queries
    (reduced p95 latency from 800ms to 150ms), handling traffic spikes, and maintaining
    99.9% uptime. We use horizontal scaling, caching, and CDN for static assets.
    """,

    "DEPLOYMENT PROCESS": """
    I've set up complete CI/CD pipelines using:
    - GitHub Actions for automated testing and deployment
    - Docker for containerization
    - Kubernetes for orchestration
    - Terraform for infrastructure as code
    - ArgoCD for GitOps deployments

    Our pipeline: PR triggers tests -> merge triggers staging deploy -> manual approval
    for production -> automated rollout with canary deployment -> automated rollback
    if error rate spikes.
    """,

    "TESTING PRACTICES": """
    Testing tools I use regularly:
    - Jest for unit tests
    - React Testing Library for component tests
    - Cypress for E2E tests
    - Postman for API testing
    - k6 for load testing

    TDD: I practice TDD for critical business logic - write failing test, implement
    feature, refactor. About 60% of my code.

    BDD: We use BDD with Cucumber for acceptance tests on some projects, writing
    scenarios with product team. It helps ensure we're building the right thing.

    Trade-offs: TDD slows initial development but catches bugs early. E2E tests are
    slow to run but give confidence. We balance unit, integration, and E2E tests.
    """,

    "HIRING": """
    Yes, I've hired 3 engineers in the past year. My assessment approach:
    1. Resume screen for relevant experience
    2. Phone screen (30 min) - discuss past projects, technical depth
    3. Take-home project (3-4 hours) - realistic feature they'd build on the job
    4. Technical deep-dive (1 hour) - review take-home code, discuss decisions
    5. Team fit interview (30 min) - collaboration, communication

    I focus on real-world signal, not leetcode puzzles. Take-home tests are similar
    to actual work: "build a REST API with these requirements" or "implement this
    React component with tests". I value clean code, testing, and good decision-making.
    """,

    "PERFORMANCE MANAGEMENT": """
    I have experience with engineer performance management and goal-setting:
    - Quarterly OKRs aligned with team goals
    - Monthly 1-on-1s to discuss progress, blockers, career growth
    - 360-degree feedback collection
    - Performance reviews twice a year
    - Individual development plans (IDPs) for skill growth

    I focus on outcomes over hours worked. We measure impact (features shipped, bugs
    fixed, system improvements) balanced with code quality and team collaboration.
    I help engineers set achievable stretch goals and provide regular feedback rather
    than waiting for formal reviews.
    """,
}


def get_answer_for_category(category: str) -> str:
    """Get a predefined answer for a question category."""
    # Try exact match first
    if category in PREDEFINED_ANSWERS:
        return PREDEFINED_ANSWERS[category].strip()

    # Try partial match
    for key in PREDEFINED_ANSWERS:
        if key.lower() in category.lower() or category.lower() in key.lower():
            return PREDEFINED_ANSWERS[key].strip()

    # Default fallback
    return """I have some experience with that area. I've worked on related projects
    in the past and have delivered production systems. I'm comfortable with the technical
    aspects and have collaborated with teams on similar challenges."""


def test_predefined_mode_complete_flow():
    """
    Test complete predefined questions mode flow end-to-end.

    Simulates a real interview:
    1. Start interview with predefined question set
    2. Answer questions until completion
    3. Verify skills extracted
    """
    print("\n" + "=" * 80)
    print("END-TO-END TEST: PREDEFINED QUESTIONS MODE")
    print("=" * 80)

    # Initialize database
    engine = create_engine(settings.DATABASE_URL)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as db_session:
        # Initialize services
        llm_service = LLMService()
        prompt_loader = PromptLoader()
        service = ConversationalInterviewService(llm_service, prompt_loader, db_session)

        # Create test candidate
        candidate_id = "test_e2e_predefined"
        candidate = db_session.get(Candidate, candidate_id)
        if not candidate:
            candidate = Candidate(id=candidate_id, name="Test E2E Candidate")
            db_session.add(candidate)
            db_session.commit()

        print("\n" + "-" * 80)
        print("STEP 1: START INTERVIEW")
        print("-" * 80)

        # Start interview in PREDEFINED_QUESTIONS mode
        print("\n[TEST] Starting interview with comprehensive resume...")
        result = service.start_interview(
            candidate_id=candidate_id,
            resume_text=SAMPLE_RESUME,
            mode="predefined_questions",
            question_set_id="03b84681-2c75-4bbd-89ee-307861ec7b6b"
        )

        session_id = result["session_id"]
        thread_id = result["thread_id"]
        question = result["question"]

        print(f"\n[OK] Session ID: {session_id}")
        print(f"[OK] Thread ID: {thread_id}")
        print(f"\nFirst Question: {question}")

        print("\n" + "-" * 80)
        print("STEP 2: ANSWER QUESTIONS (INTERACTIVE FLOW)")
        print("-" * 80)

        questions_answered = 0
        max_questions = 15  # Limit to prevent infinite loops in testing

        # Track categories asked to provide varied answers
        last_category = None

        while questions_answered < max_questions:
            questions_answered += 1

            # Determine category from question context (simple heuristic)
            # In real scenario, we'd track current_gap category from state
            category = _infer_category_from_question(question)

            # Get predefined answer for this category
            answer = get_answer_for_category(category)

            print(f"\n--- Question {questions_answered} ---")
            print(f"Category: {category}")
            print(f"Q: {question[:100]}...")
            print(f"A: {answer[:150]}...")

            # Continue interview with answer
            result = service.continue_interview(thread_id, answer)

            if result["completed"]:
                print(f"\n[OK] Interview completed after {questions_answered} questions")
                print(f"Reason: {result['termination_reason']}")
                print(f"Message: {result['completion_message']}")
                break
            else:
                question = result["question"]

        print("\n" + "-" * 80)
        print("STEP 3: VERIFY EXTRACTED SKILLS")
        print("-" * 80)

        skills = service.get_extracted_skills(session_id)

        if skills:
            print(f"\n[OK] Extracted {len(skills)} skills:")
            for i, skill in enumerate(skills[:10], 1):  # Show first 10
                print(f"\n{i}. {skill['name']} (confidence: {skill['confidence_score']:.2f})")
                if skill['duration']:
                    print(f"   Duration: {skill['duration']}")
                if skill['depth']:
                    print(f"   Depth: {skill['depth'][:80]}...")
                if skill['autonomy']:
                    print(f"   Autonomy: {skill['autonomy'][:60]}...")

            if len(skills) > 10:
                print(f"\n... and {len(skills) - 10} more skills")
        else:
            print("\n[WARNING] No skills extracted - interview may not have completed properly")

        print("\n" + "-" * 80)
        print("STEP 4: VERIFY SESSION METADATA")
        print("-" * 80)

        # Get session details
        from models.interview_session import InterviewSession
        session = db_session.get(InterviewSession, session_id)

        print(f"\nSession Status: {session.status}")
        print(f"Mode: {session.mode}")
        print(f"Questions Asked: {session.questions_asked}")
        print(f"Completeness Score: {session.completeness_score:.1%}")
        print(f"Termination Reason: {session.termination_reason}")

        # Assertions
        assert session.status == "completed", "Interview should be completed"
        assert session.mode == "predefined_questions", "Mode should be predefined_questions"
        assert session.questions_asked > 0, "Should have asked at least one question"
        assert session.completeness_score > 0, "Should have some completeness"

        print("\n" + "=" * 80)
        print("✅ END-TO-END TEST PASSED")
        print("=" * 80)


def _infer_category_from_question(question: str) -> str:
    """
    Infer category from question text using keywords.

    This is a simple heuristic for testing. In production, we'd use
    the actual category from current_gap in state.
    """
    question_lower = question.lower()

    # Order matters - check more specific categories first to avoid mismatches
    keyword_map = {
        "MOBILE DEVELOPMENT": ["mobile", "ios", "android", "flutter", "react native", "cross-platform"],
        "REACTIVE APPLICATIONS": ["reactive", "real-time", "websocket", "sse", "live", "streaming"],
        "DATA CONFLICTS": ["conflict", "consistency", "concurrent", "race condition"],
        "PRODUCT ANALYTICS EXPERIENCE": ["analytics", "metrics", "data", "dau", "conversion", "funnel"],
        "FRONTEND DEVELOPMENT": ["frontend", "react", "javascript", "typescript", "vue", "angular"],
        "BACKEND DEVELOPMENT": ["backend", "server", "node", "python", "go", "java"],
        "SYSTEM DESIGN": ["microservices", "architecture", "event-driven", "design pattern"],
        "DATABASE EXPERIENCE": ["database", "sql", "nosql", "postgres", "mongodb", "cassandra", "neo4j", "clickhouse"],
        "MESSAGING": ["kafka", "rabbitmq", "message queue", "producer", "consumer", "broker"],
        "DATABASE TOPOLOGY": ["topology", "cluster", "replication", "master-slave", "master-master"],
        "API DESIGN": ["api", "rest", "graphql", "grpc", "rpc"],
        "PRODUCTION SCALE": ["scale", "production", "users", "dau", "traffic", "load"],
        "DEPLOYMENT PROCESS": ["deployment", "ci/cd", "pipeline", "devops", "github actions"],
        "TESTING PRACTICES": ["testing", "test", "tdd", "bdd", "unit test", "integration test"],
        "LEADERSHIP EXPERIENCE": ["leadership", "led", "mentor", "team", "manage", "coach"],
        "HIRING": ["hiring", "interview", "recruit", "assessment", "candidate"],
        "PERFORMANCE MANAGEMENT": ["performance", "kpi", "management", "feedback", "goal"],
        "GENERAL INFORMATION": ["role", "responsibilities", "current position", "products", "experience"],
    }

    # Check each category in order
    for category, keywords in keyword_map.items():
        if any(keyword in question_lower for keyword in keywords):
            return category

    return "GENERAL"


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("PREDEFINED MODE - END-TO-END INTEGRATION TEST")
    print("=" * 80)

    # Import all models for SQLAlchemy relationships
    import importlib
    import pkgutil
    import models

    for _, name, _ in pkgutil.iter_modules(models.__path__):
        importlib.import_module(f"models.{name}")

    # Run test
    try:
        test_predefined_mode_complete_flow()
        print("\n✅ All tests completed successfully!\n")
    except Exception as e:
        print(f"\n❌ Test failed: {e}\n")
        import traceback
        traceback.print_exc()
