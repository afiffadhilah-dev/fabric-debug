from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from sqlmodel import SQLModel
from models.candidate import Candidate
from models.candidate_chunk import CandidateChunk
from models.interview_session import InterviewSession
from models.extracted_skill import ExtractedSkill
from models.message import Message
from models.api_key import APIKey
from models.organization import Organization
from models.skill import Skill
from models.skill_dimension import SkillDimension
from models.behavioral_observation import BehavioralObservation
from models.aspiration import Aspiration
from models.confirmed_gap import ConfirmedGap
from models.constraint import Constraint
from models.evidence import Evidence
from models.followup_flag import FollowupFlag
from models.potential_Indicator import PotentialIndicator
from models.present_state import PresentState
from models.risk_note import RiskNote
from models.predefined_role import PredefinedRole
from models.predefined_question_set import PredefinedQuestionSet
from models.predefined_question import PredefinedQuestion
from models.domain_context import DomainContext
from models.infrastructure_context import InfrastructureContext
from models.candidate_profile_summary import CandidateProfileSummary
from models.background_task import BackgroundTask
from config.settings import Settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Load settings from .env
settings = Settings()

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# LangGraph checkpoint tables - managed by PostgresSaver.setup(), not Alembic
LANGGRAPH_TABLES = {
    "checkpoint_writes",
    "checkpoints",
    "checkpoint_blobs",
    "checkpoint_migrations",
}


def include_object(object, name, type_, reflected, compare_to):
    """Filter objects for autogenerate.

    Excludes LangGraph checkpoint tables which are managed by PostgresSaver.setup().
    """
    if type_ == "table" and name in LANGGRAPH_TABLES:
        return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = settings.DATABASE_URL or config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Use DATABASE_URL from .env if available, otherwise fallback to alembic.ini
    url = settings.DATABASE_URL or config.get_main_option("sqlalchemy.url")
    
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
