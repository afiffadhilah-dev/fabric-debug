"""
Streamlit UI for AI Interview Agent.

A simple chatbot interface for conducting technical skill interviews.
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import from the root
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import streamlit as st
from sqlmodel import Session, create_engine, SQLModel, select
from services import InterviewService
from models.candidate import Candidate
from models.predefined_question_set import PredefinedQuestionSet
from config.settings import settings
from utils.document_extractor import DocumentExtractor
from utils.language_config import SUPPORTED_LANGUAGES
import json

# Page configuration
st.set_page_config(
    page_title="Interview",
    page_icon="🤖",
    layout="wide"
)

# Initialize database connection (cached)
@st.cache_resource
def get_database_engine():
    """Create and cache database engine."""
    engine = create_engine(settings.DATABASE_URL)
    SQLModel.metadata.create_all(engine)
    return engine


# Initialize service (cached)
@st.cache_resource
def get_service(_db_session):
    """Create and cache interview service."""
    return InterviewService(_db_session)


def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "interview_started" not in st.session_state:
        st.session_state.interview_started = False
    if "interview_completed" not in st.session_state:
        st.session_state.interview_completed = False
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = None
    if "candidate_id" not in st.session_state:
        st.session_state.candidate_id = None
    if "interview_mode" not in st.session_state:
        st.session_state.interview_mode = None
    if "question_set_id" not in st.session_state:
        st.session_state.question_set_id = None
    if "starting_interview" not in st.session_state:
        st.session_state.starting_interview = False


def get_available_question_sets(db_session):
    """Fetch all active question sets from database."""
    statement = select(PredefinedQuestionSet).where(
        PredefinedQuestionSet.is_active == True
    ).order_by(PredefinedQuestionSet.name)

    question_sets = db_session.exec(statement).all()
    return question_sets


def display_chat_messages():
    """Display all chat messages in the conversation."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def start_interview(service, db_session, resume_text, mode="dynamic_gap", question_set_id=None, language=None):
    """Start a new interview session."""
    # Create or get candidate
    candidate = db_session.get(Candidate, "streamlit_user")
    if not candidate:
        candidate = Candidate(id="streamlit_user", name="streamlit_user")
        db_session.add(candidate)
        db_session.commit()

    st.session_state.candidate_id = candidate.id

    # Start interview
    try:
        result = service.start_interview(
            candidate_id=candidate.id,
            resume_text=resume_text,
            mode=mode,
            question_set_id=question_set_id,
            language=language
        )

        st.session_state.session_id = result["session_id"]
        st.session_state.thread_id = result["thread_id"]
        st.session_state.interview_started = True
        st.session_state.interview_mode = mode
        st.session_state.question_set_id = question_set_id
        st.session_state.language = language

        # Add first question to messages
        st.session_state.messages.append({
            "role": "assistant",
            "content": result["question"]
        })

        return True
    except Exception as e:
        st.error(f"Error starting interview: {str(e)}")
        return False


def continue_interview(service, user_answer):
    """Continue the interview with user's answer."""
    try:
        result = service.continue_interview(
            st.session_state.session_id,
            user_answer
        )

        print(f"Interview service returned: {result}")

        if(result["consecutive_low_quality"] == 2):
            st.session_state.messages.append({
                "role": "assistant",
                "content": "⚠️ Warning: We've noticed that your recent answers have been brief or off-topic. To continue the interview, please provide clear and detailed responses. One more low-quality answer may result in the interview being terminated."
            })

        if result["completed"]:
            # Interview completed
            st.session_state.interview_completed = True
            st.session_state.messages.append({
                "role": "assistant",
                "content": result["completion_message"]
            })

            # Trigger summarization API call
            try:
                import requests
                api_url = f"{settings.API_BASE_URL}/summarization/analyze-session"
                payload = {"session_id": st.session_state.session_id}
                resp = requests.post(api_url, json=payload)
                if resp.status_code == 202:
                    st.info("Session summarization task queued.")
                else:
                    st.warning(f"Summarization API call failed: {resp.status_code} {resp.text}")
            except Exception as e:
                st.warning(f"Error calling summarization API: {e}")

            return True
        else:
            # Continue with next question
            st.session_state.messages.append({
                "role": "assistant",
                "content": result["question"]
            })
            return False
    except Exception as e:
        st.error(f"Error processing answer: {str(e)}")
        return False


def display_extracted_skills(service):
    """Display extracted skills at the end of interview."""
    if st.session_state.session_id:
        skills = service.get_extracted_skills(st.session_state.session_id)

        if skills:
            st.subheader("📊 Extracted Skills")

            for i, skill in enumerate(skills, 1):
                with st.expander(f"{i}. {skill['name']} (Confidence: {skill['confidence_score']:.0%})"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown(f"**Duration:** {skill['duration'] or 'unknown'}")
                        st.markdown(f"**Depth:** {skill['depth'] or 'unknown'}")
                        st.markdown(f"**Autonomy:** {skill['autonomy'] or 'unknown'}")

                    with col2:
                        st.markdown(f"**Scale:** {skill['scale'] or 'unknown'}")
                        st.markdown(f"**Constraints:** {skill['constraints'] or 'unknown'}")
                        st.markdown(f"**Production/Prototype:** {skill['production_vs_prototype'] or 'unknown'}")

                    if skill['evidence']:
                        st.markdown(f"**Evidence:** {skill['evidence']}")
        else:
            st.info("No skills extracted yet.")


def main():
    """Main Streamlit app."""
    # Initialize session state
    initialize_session_state()

    # Sidebar
    st.sidebar.title("🤖 AI Interview Agent")
    st.sidebar.markdown("---")

    # Database session
    engine = get_database_engine()
    db_session = Session(engine)

    # Initialize service
    service = get_service(db_session)

    # Main content
    st.title("Technical Skill Interview")

    # Show instructions if interview not started
    if not st.session_state.interview_started:
        st.markdown("""
        ### Welcome!

        This AI-powered interview agent will:
        - Ask targeted questions based on a predefined question set
        - Extract detailed skill attributes (duration, depth, autonomy, scale, etc.)
        - Adapt based on your engagement level

        **To get started:**
        1. Select a question set
        2. Optionally upload your resume
        3. Click "Start Interview"
        4. Answer the questions naturally

        The interview will conclude when all questions are answered or if engagement drops.
        """)

        # Question set selector
        mode_value = "predefined_questions"
        selected_question_set_id = None
        question_sets = get_available_question_sets(db_session)

        if question_sets:
            st.markdown("**Select Question Set:**")

            # Create options with name and version
            options = {
                f"{qs.name} (v{qs.version})": str(qs.id)
                for qs in question_sets
            }

            if options:
                selected_display = st.selectbox(
                    "Question Set",
                    options=list(options.keys()),
                    label_visibility="collapsed"
                )
                selected_question_set_id = options[selected_display]

                # Show question set description
                selected_qs = next((qs for qs in question_sets if str(qs.id) == selected_question_set_id), None)
                if selected_qs and selected_qs.description:
                    st.info(f"ℹ️ {selected_qs.description}")
            else:
                st.warning("No question sets available. Please create a question set first.")
        else:
            st.warning("⚠️ No active question sets found. Please create and activate a question set first.")

        st.markdown("---")

        # Language selector
        language_options = {f"{name} ({code})": code for code, name in SUPPORTED_LANGUAGES.items()}
        selected_language_display = st.selectbox(
            "Interview Language",
            options=list(language_options.keys()),
            index=0,  # English is first
        )
        selected_language = language_options[selected_language_display]

        st.markdown("---")

        # Resume upload input
        uploaded_file = st.file_uploader(
            "📄 Upload your resume (PDF, DOCX, TXT, MD):",
            type=["pdf", "docx", "txt", "md"]
        )

        resume_text = ""
        if uploaded_file is not None:
            try:
                file_bytes = uploaded_file.read()
                resume_text = DocumentExtractor.extract_text(file_bytes, uploaded_file.name)
                st.success(f"Extracted text from {uploaded_file.name}")
                with st.expander("Preview extracted resume text", expanded=False):
                    st.text_area("Extracted text preview", value=resume_text, height=300)
            except Exception as e:
                st.error(f"Error extracting text from file: {str(e)}")

        # Check if button was just clicked (using its key) to disable during processing
        if 'start_btn' in st.session_state and st.session_state.start_btn:
            st.session_state.starting_interview = True
        else:
            st.session_state.starting_interview = False

        # Validation for start button
        can_start = (
            selected_question_set_id is not None
            and not st.session_state.starting_interview
        )

        if st.button("🚀 Start Interview", type="primary", disabled=not can_start, key='start_btn'):
            with st.spinner("Starting interview..."):
                if start_interview(
                    service,
                    db_session,
                    resume_text,
                    mode=mode_value,
                    question_set_id=selected_question_set_id,
                    language=selected_language
                ):
                    st.rerun()

    else:
        # Interview in progress or completed
        st.sidebar.markdown(f"**Session ID:** `{st.session_state.session_id[:8]}...`")
        st.sidebar.markdown(f"**Questions Asked:** {len([m for m in st.session_state.messages if m['role'] == 'assistant'])}")

        # Show interview mode and language
        st.sidebar.markdown("**Mode:** Predefined Questions")
        if st.session_state.get("language"):
            lang_code = st.session_state.language
            lang_name = SUPPORTED_LANGUAGES.get(lang_code, lang_code)
            st.sidebar.markdown(f"**Language:** {lang_name}")

        # Show question set if in predefined mode
        if st.session_state.interview_mode == "predefined_questions" and st.session_state.question_set_id:
            st.sidebar.markdown(f"**Question Set ID:** `{st.session_state.question_set_id[:8]}...`")

        # Reset button
        if st.sidebar.button("🔄 Start New Interview"):
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        st.sidebar.markdown("---")

        # Display chat messages
        display_chat_messages()

        # Chat input (only if interview not completed)
        if not st.session_state.interview_completed:
            if prompt := st.chat_input("Your answer..."):
                # Add user message to chat
                st.session_state.messages.append({
                    "role": "user",
                    "content": prompt
                })

                # Display user message
                with st.chat_message("user"):
                    st.markdown(prompt)


                # Get agent response
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        completed = continue_interview(service, prompt)

                        # Display the new message
                        st.markdown(st.session_state.messages[-1]["content"])

                # Rerun to update UI
                st.rerun()

        else:
            # Interview completed - show results
            st.success("✅ Interview completed!")

            # Display extracted skills
            display_extracted_skills(service)

            # Download results button
            if st.session_state.session_id:
                skills = service.get_extracted_skills(st.session_state.session_id)
                if skills:
                    skills_json = json.dumps(skills, indent=2)
                    st.download_button(
                        label="📥 Download Skills as JSON",
                        data=skills_json,
                        file_name=f"skills_{st.session_state.session_id}.json",
                        mime="application/json"
                    )


if __name__ == "__main__":
    main()
