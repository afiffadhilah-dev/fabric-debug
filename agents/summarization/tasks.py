"""Celery tasks for background job processing."""
import logging
import traceback
from config.celery_config import celery_app
from sqlalchemy.exc import OperationalError
from requests.exceptions import Timeout, ConnectionError as RequestsConnectionError

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def summarize_session_task(self, session_id: str, mode: str = "SELF_REPORT"):
    """
    Celery task to summarize an interview session asynchronously.

    Args:
        session_id: The interview session ID
        mode: Interview mode (SELF_REPORT, RECRUITER_REPORT, etc.)

    Returns:
        Dictionary with task result information
    """
    try:
        logger.info(f"Starting summarize_session task for session {session_id}")

        # Import here to avoid circular imports
        from services.summarization_service import SummarizationService

        service = SummarizationService()

        # Execute the synchronous summarization
        result = service.analyze_session(session_id=session_id, mode=mode)

        logger.info(f"Successfully completed summarize_session task for session {session_id}")

        return {
            "status": "completed",
            "session_id": session_id,
            "result": result,
        }
    
    # Retryable (transient) errors
    except (OperationalError, Timeout, RequestsConnectionError) as exc:
        logger.warning(
            f"Retryable error in summarize_session_task (attempt {self.request.retries + 1}): {exc}"
        )
        retry_delay = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=retry_delay)
    
    # Unrecoverable errors → fail fast
    except ValueError as exc:
        logger.error(f"Invalid input for summarize_session_task: {exc}")
        raise

    except Exception as exc:
        # Unknown error → don't blindly retry
        logger.error(f"Unexpected error in summarize_session_task: {exc}")
        logger.error(traceback.format_exc())
        raise


@celery_app.task(bind=True, max_retries=3)
def summarize_profile_task(self, candidate_id: str):
    """
    Celery task to summarize a candidate profile asynchronously.

    Args:
        candidate_id: The candidate ID

    Returns:
        Dictionary with task result information
    """
    try:
        logger.info(f"Starting summarize_profile task for candidate {candidate_id}")

        # Import here to avoid circular imports
        from services.summarization_service import SummarizationService

        service = SummarizationService()

        # Execute the synchronous profile summarization
        result = service.summarize_candidate_profile(candidate_id=candidate_id)

        logger.info(f"Successfully completed summarize_profile task for candidate {candidate_id}")

        return {
            "status": "completed",
            "candidate_id": candidate_id,
            "result": result,
        }

    # Retryable (transient) errors
    except (OperationalError, Timeout, RequestsConnectionError) as exc:
        logger.warning(
            f"Retryable error in summarize_profile_task (attempt {self.request.retries + 1}): {exc}"
        )
        retry_delay = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=retry_delay)

    # Unrecoverable errors → fail fast
    except ValueError as exc:
        logger.error(f"Invalid input for summarize_profile_task: {exc}")
        raise

    except Exception as exc:
        logger.error(f"Unexpected error in summarize_profile_task: {exc}")
        logger.error(traceback.format_exc())
        raise
