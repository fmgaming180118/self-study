from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Table, Integer, Float, Boolean, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import uuid
import enum
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class MasteryLevel(str, enum.Enum):
    NOT_STARTED = "not_started"           # 0-20%
    UNDERSTANDING = "understanding"       # 21-50%
    GUIDED_PRACTICE = "guided_practice"   # 51-70%
    INDEPENDENT = "independent"           # 71-85%
    PROJECT_PROVEN = "project_proven"     # 86-100%


class ResourceLevel(str, enum.Enum):
    BASIC = "level_1_basic"           # Penjelasan dasar dan buku teks
    TUTORIAL = "level_2_tutorial"     # Course notes dan tutorial terverifikasi
    UNIVERSITY = "level_3_university" # Buku tingkat universitas
    REVIEW = "level_4_review"         # Review paper dan systematic review
    PEER_REVIEWED = "level_5_peer_reviewed"  # Peer-reviewed research
    PREPRINT = "level_6_preprint"     # Preprint dan penelitian frontier


# Association tables
skill_prerequisites = Table(
    "skill_prerequisites",
    Base.metadata,
    Column("skill_id", UUID(as_uuid=True), ForeignKey("skills.id"), primary_key=True),
    Column("prerequisite_id", UUID(as_uuid=True), ForeignKey("skills.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    mastery_records = relationship("MasteryRecord", back_populates="user", cascade="all, delete-orphan")
    learning_sessions = relationship("LearningSession", back_populates="user", cascade="all, delete-orphan")
    assessment_attempts = relationship("AssessmentAttempt", back_populates="user", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    review_queue = relationship("ReviewQueue", back_populates="user", cascade="all, delete-orphan")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_id = Column(String(100), unique=True, nullable=False, index=True)  # e.g., "electronics.ohms_law"
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100), index=True)  # math, physics, electronics, programming, ai, etc.
    subcategory = Column(String(100), index=True)
    difficulty = Column(Integer, default=1)  # 1-10
    estimated_hours = Column(Float, default=0.0)

    # Mastery tracking (default values for new users)
    default_mastery = Column(Float, default=0.0)
    default_confidence = Column(Float, default=0.0)

    # Prerequisites (many-to-many self-referential)
    prerequisites = relationship(
        "Skill",
        secondary=skill_prerequisites,
        primaryjoin=id == skill_prerequisites.c.skill_id,
        secondaryjoin=id == skill_prerequisites.c.prerequisite_id,
        backref="dependents"
    )

    # Relationships
    resources = relationship("LearningResource", back_populates="skill", cascade="all, delete-orphan")
    assessments = relationship("Assessment", back_populates="skill", cascade="all, delete-orphan")
    simulations = relationship("Simulation", back_populates="skill", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="skill", cascade="all, delete-orphan")
    mastery_records = relationship("MasteryRecord", back_populates="skill", cascade="all, delete-orphan")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class LearningResource(Base):
    __tablename__ = "learning_resources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    url = Column(String(1000))
    resource_type = Column(String(50))  # video, article, book, tutorial, simulation, paper
    level = Column(SQLEnum(ResourceLevel), default=ResourceLevel.BASIC, index=True)
    source = Column(String(100))  # arxiv, openalex, consensus, manual, youtube, etc.
    source_id = Column(String(200))  # arXiv ID, DOI, etc.
    authors = Column(ARRAY(String))
    published_date = Column(DateTime(timezone=True))
    quality_score = Column(Float, default=0.0)  # 0-1
    difficulty = Column(Integer, default=1)  # 1-10
    estimated_minutes = Column(Integer, default=0)
    tags = Column(ARRAY(String))
    embedding = Column(Vector(1536))  # For semantic search
    resource_metadata = Column(JSON, default={})

    # Relationships
    skill = relationship("Skill", back_populates="resources")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class LearningSession(Base):
    __tablename__ = "learning_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id"), nullable=False, index=True)
    session_type = Column(String(50))  # diagnostic, lesson, practice, assessment, project, review
    status = Column(String(20), default="in_progress")  # in_progress, completed, abandoned
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Integer, default=0)
    mastery_before = Column(Float, default=0.0)
    mastery_after = Column(Float, default=0.0)
    confidence_before = Column(Float, default=0.0)
    confidence_after = Column(Float, default=0.0)
    notes = Column(Text)
    session_metadata = Column(JSON, default={})

    # Relationships
    user = relationship("User", back_populates="learning_sessions")
    skill = relationship("Skill")


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    assessment_type = Column(String(50))  # diagnostic, formative, summative, project
    questions = Column(JSON, default=[])  # List of question objects
    passing_score = Column(Float, default=0.7)  # 0-1
    time_limit_minutes = Column(Integer, default=0)
    difficulty = Column(Integer, default=1)
    assessment_metadata = Column(JSON, default={})

    # Relationships
    skill = relationship("Skill", back_populates="assessments")
    attempts = relationship("AssessmentAttempt", back_populates="assessment", cascade="all, delete-orphan")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("assessments.id"), nullable=False, index=True)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id"), nullable=False, index=True)
    answers = Column(JSON, default=[])  # User's answers
    score = Column(Float, default=0.0)  # 0-1
    passed = Column(Boolean, default=False)
    feedback = Column(Text)
    mastery_delta = Column(Float, default=0.0)  # Change in mastery
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Integer, default=0)
    attempt_metadata = Column(JSON, default={})

    # Relationships
    user = relationship("User", back_populates="assessment_attempts")
    assessment = relationship("Assessment", back_populates="attempts")
    skill = relationship("Skill")


class MasteryRecord(Base):
    __tablename__ = "mastery_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id"), nullable=False, index=True)
    mastery = Column(Float, default=0.0)  # 0-1
    confidence = Column(Float, default=0.0)  # 0-1
    level = Column(SQLEnum(MasteryLevel), default=MasteryLevel.NOT_STARTED, index=True)
    evidence = Column(ARRAY(String), default=[])  # IDs of assessments, projects, etc.
    last_review = Column(DateTime(timezone=True), nullable=True)
    next_review = Column(DateTime(timezone=True), nullable=True, index=True)
    review_count = Column(Integer, default=0)
    streak_days = Column(Integer, default=0)
    mastery_metadata = Column(JSON, default={})

    # Relationships
    user = relationship("User", back_populates="mastery_records")
    skill = relationship("Skill", back_populates="mastery_records")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    project_type = Column(String(50))  # simulation, hardware, coding, research, design
    status = Column(String(20), default="planning")  # planning, in_progress, review, completed, archived
    requirements = Column(JSON, default=[])  # List of requirements
    deliverables = Column(JSON, default=[])  # Expected deliverables
    actual_deliverables = Column(JSON, default=[])  # Actual deliverables
    grade = Column(String(20))  # A, B, C, D, F or pass/fail
    feedback = Column(Text)
    mastery_evidence = Column(Float, default=0.0)  # How much this proves mastery
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    project_metadata = Column(JSON, default={})

    # Relationships
    user = relationship("User", back_populates="projects")
    skill = relationship("Skill", back_populates="projects")
    artifacts = relationship("ProjectArtifact", back_populates="project", cascade="all, delete-orphan")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ProjectArtifact(Base):
    __tablename__ = "project_artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    artifact_type = Column(String(50))  # code, schematic, report, model, video, cad, data
    content = Column(Text)  # For text-based artifacts
    file_path = Column(String(500))  # For file-based artifacts
    url = Column(String(1000))
    artifact_metadata = Column(JSON, default={})

    # Relationships
    project = relationship("Project", back_populates="artifacts")

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ReviewQueue(Base):
    __tablename__ = "review_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id"), nullable=False, index=True)
    mastery_record_id = Column(UUID(as_uuid=True), ForeignKey("mastery_records.id"), nullable=False)
    scheduled_for = Column(DateTime(timezone=True), nullable=False, index=True)
    priority = Column(Integer, default=0)  # Higher = more urgent
    review_type = Column(String(50))  # spaced_repetition, weak_area, project_followup
    status = Column(String(20), default="pending")  # pending, in_progress, completed, skipped
    completed_at = Column(DateTime(timezone=True), nullable=True)
    review_metadata = Column(JSON, default={})

    # Relationships
    user = relationship("User", back_populates="review_queue")
    skill = relationship("Skill")
    mastery_record = relationship("MasteryRecord")

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ResearchPaper(Base):
    __tablename__ = "research_papers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    arxiv_id = Column(String(50), unique=True, index=True)
    title = Column(String(500), nullable=False)
    abstract = Column(Text)
    authors = Column(ARRAY(String))
    categories = Column(ARRAY(String))  # arXiv categories
    primary_category = Column(String(100))
    published_date = Column(DateTime(timezone=True))
    updated_date = Column(DateTime(timezone=True))
    pdf_url = Column(String(500))
    doi = Column(String(100))
    journal_ref = Column(String(200))
    comment = Column(Text)
    embedding = Column(Vector(1536))  # For semantic search
    paper_metadata = Column(JSON, default={})

    # Relationships
    citations = relationship("Citation", back_populates="paper", cascade="all, delete-orphan")
    skill_mappings = relationship("PaperSkillMapping", back_populates="paper", cascade="all, delete-orphan")

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Citation(Base):
    __tablename__ = "citations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("research_papers.id"), nullable=False, index=True)
    cited_arxiv_id = Column(String(50), index=True)
    cited_title = Column(String(500))
    citation_type = Column(String(50))  # references, cited_by
    citation_metadata = Column(JSON, default={})

    # Relationships
    paper = relationship("ResearchPaper", back_populates="citations")

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PaperSkillMapping(Base):
    __tablename__ = "paper_skill_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("research_papers.id"), nullable=False, index=True)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id"), nullable=False, index=True)
    relevance_score = Column(Float, default=0.0)  # 0-1
    mapping_type = Column(String(50))  # teaches, applies, extends, prerequisites
    mapping_metadata = Column(JSON, default={})

    # Relationships
    paper = relationship("ResearchPaper", back_populates="skill_mappings")
    skill = relationship("Skill")

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    simulation_type = Column(String(50))  # circuit, physics, math, coding, cad, robotics
    engine = Column(String(50))  # pspice, ltspice, python, javascript, webgl, custom
    config = Column(JSON, default={})  # Simulation parameters, initial conditions
    scenario_template = Column(JSON, default={})  # Template for generating scenarios
    difficulty = Column(Integer, default=1)
    estimated_minutes = Column(Integer, default=0)
    learning_objectives = Column(ARRAY(String))
    assessment_criteria = Column(JSON, default={})
    simulation_metadata = Column(JSON, default={})

    # Relationships
    skill = relationship("Skill", back_populates="simulations")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())