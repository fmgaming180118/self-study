from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr
from datetime import datetime

from app.database import get_db
from app.models import User, Skill, MasteryRecord, MasteryLevel
from app.services.skill_graph import SkillGraphService
from app.services.knowledge_tracing import KnowledgeTracingService
from app.services.tutor_orchestrator import TutorOrchestrator
from app.services.simulation_lab import SimulationService
from app.services.research_ingestion import ResearchIngestionService

router = APIRouter()


# ==================== Pydantic Models ====================
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SkillResponse(BaseModel):
    id: UUID
    skill_id: str
    name: str
    description: Optional[str]
    category: str
    subcategory: Optional[str]
    difficulty: int
    estimated_hours: float

    class Config:
        from_attributes = True


class MasteryResponse(BaseModel):
    skill_id: str
    skill_name: str
    mastery: float
    confidence: float
    level: str
    evidence_count: int
    last_review: Optional[datetime]
    next_review: Optional[datetime]
    review_count: int


class LearningSessionCreate(BaseModel):
    skill_id: str
    session_type: str
    metadata: Optional[dict] = {}


class AssessmentCreate(BaseModel):
    skill_id: str
    assessment_type: str = "formative"
    num_questions: int = 5
    difficulty: Optional[int] = None


class AssessmentAnswer(BaseModel):
    question_id: str
    answer: str


class SimulationRun(BaseModel):
    simulation_id: str
    config: dict = {}
    user_input: Optional[dict] = None


class ProjectCreate(BaseModel):
    skill_id: str
    title: str
    description: str = ""
    project_type: str = "coding"
    requirements: List[dict] = []
    deliverables: List[dict] = []


class ProjectComplete(BaseModel):
    deliverables: List[dict]
    grade: str = "pass"


class NextSkillRequest(BaseModel):
    limit: int = 5


# ==================== Dependency ====================
async def get_current_user(
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user (placeholder - implement auth)."""
    # For MVP, return first user or create demo user
    result = await db.execute(
        select(User).where(User.is_active == True).limit(1)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Create demo user
        user = User(
            email="demo@selfstudy.os",
            hashed_password="demo",
            full_name="Demo User",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    return user


# ==================== User Routes ====================
@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new user."""
    # Check if email exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password (simplified for MVP)
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash(user_data.password)
    
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user


@router.get("/users/me", response_model=UserResponse)
async def get_current_user_info(
    user: User = Depends(get_current_user)
):
    """Get current user info."""
    return user


# ==================== Skill Routes ====================
@router.get("/skills", response_model=List[SkillResponse])
async def list_skills(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all skills, optionally filtered by category."""
    skill_graph = SkillGraphService(db)
    
    if category:
        skills = await skill_graph.get_skills_by_category(category)
    else:
        skills = await skill_graph.get_all_skills()
    
    return skills


@router.get("/skills/{skill_id}", response_model=SkillResponse)
async def get_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a skill by skill_id (e.g., 'electronics.ohms_law')."""
    skill_graph = SkillGraphService(db)
    skill = await skill_graph.get_skill_by_id(skill_id)
    
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    return skill


@router.get("/skills/{skill_id}/prerequisites", response_model=List[SkillResponse])
async def get_skill_prerequisites(
    skill_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get prerequisites for a skill."""
    skill_graph = SkillGraphService(db)
    skill = await skill_graph.get_skill_by_id(skill_id)
    
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    prereqs = await skill_graph.get_prerequisites(skill.id)
    return prereqs


@router.get("/skills/{skill_id}/learning-path", response_model=List[dict])
async def get_learning_path(
    skill_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get learning path to a target skill."""
    skill_graph = SkillGraphService(db)
    skill = await skill_graph.get_skill_by_id(skill_id)
    
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    tutor = TutorOrchestrator(db, user.id)
    path = await tutor.get_learning_path(skill.id)
    return path


# ==================== Mastery/Progress Routes ====================
@router.get("/progress", response_model=dict)
async def get_progress(
    skill_id: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's learning progress."""
    tutor = TutorOrchestrator(db, user.id)
    
    if skill_id:
        skill_graph = SkillGraphService(db)
        skill = await skill_graph.get_skill_by_id(skill_id)
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        return await tutor.read_progress(skill.id)
    else:
        return await tutor.read_progress()


@router.get("/mastery", response_model=List[MasteryResponse])
async def get_all_mastery(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get mastery records for all skills."""
    kt = KnowledgeTracingService(db)
    summary = await kt.get_user_mastery_summary(user.id)
    
    # Get detailed records
    result = await db.execute(
        select(MasteryRecord, Skill)
        .join(Skill)
        .where(MasteryRecord.user_id == user.id)
        .order_by(MasteryRecord.mastery.desc())
    )
    
    records = []
    for mastery, skill in result.all():
        records.append(MasteryResponse(
            skill_id=skill.skill_id,
            skill_name=skill.name,
            mastery=mastery.mastery,
            confidence=mastery.confidence,
            level=mastery.level.value,
            evidence_count=len(mastery.evidence),
            last_review=mastery.last_review,
            next_review=mastery.next_review,
            review_count=mastery.review_count,
        ))
    
    return records


@router.get("/mastery/{skill_id}", response_model=dict)
async def get_skill_mastery(
    skill_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed mastery for a specific skill."""
    skill_graph = SkillGraphService(db)
    skill = await skill_graph.get_skill_by_id(skill_id)
    
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    kt = KnowledgeTracingService(db)
    return await kt.get_skill_mastery_details(user.id, skill.id)


# ==================== Tutor Routes ====================
@router.post("/tutor/lesson")
async def generate_lesson(
    skill_id: str,
    session_type: str = "lesson",
    context: Optional[dict] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate a personalized lesson for a skill."""
    skill_graph = SkillGraphService(db)
    skill = await skill_graph.get_skill_by_id(skill_id)
    
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    tutor = TutorOrchestrator(db, user.id)
    return await tutor.generate_lesson(skill.id, session_type, context)


@router.get("/tutor/resources/{skill_id}")
async def search_resources(
    skill_id: str,
    resource_type: Optional[str] = None,
    level: Optional[str] = None,
    limit: int = 10,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Search for learning resources for a skill."""
    skill_graph = SkillGraphService(db)
    skill = await skill_graph.get_skill_by_id(skill_id)
    
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    tutor = TutorOrchestrator(db, user.id)
    return await tutor.search_resources(skill.id, resource_type, level, limit)


@router.post("/tutor/assessment")
async def create_assessment(
    assessment_data: AssessmentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create an assessment for a skill."""
    skill_graph = SkillGraphService(db)
    skill = await skill_graph.get_skill_by_id(assessment_data.skill_id)
    
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    tutor = TutorOrchestrator(db, user.id)
    return await tutor.create_assessment(
        skill.id,
        assessment_data.assessment_type,
        assessment_data.num_questions,
        assessment_data.difficulty
    )


@router.post("/tutor/assessment/{attempt_id}/answer")
async def answer_question(
    attempt_id: UUID,
    answer_data: AssessmentAnswer,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit an answer for an assessment question."""
    tutor = TutorOrchestrator(db, user.id)
    return await tutor.evaluate_answer(attempt_id, answer_data.question_id, answer_data.answer)


@router.post("/tutor/assessment/{attempt_id}/complete")
async def complete_assessment(
    attempt_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Complete an assessment and update mastery."""
    tutor = TutorOrchestrator(db, user.id)
    return await tutor.complete_assessment(attempt_id)


@router.post("/tutor/next-skills")
async def get_next_skills(
    request: NextSkillRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get recommended next skills to learn."""
    tutor = TutorOrchestrator(db, user.id)
    return await tutor.choose_next_skill(request.limit)


@router.post("/tutor/evidence")
async def save_evidence(
    skill_id: str,
    evidence_type: str,
    content: dict,
    mastery_boost: float = 0.0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Save evidence of learning."""
    skill_graph = SkillGraphService(db)
    skill = await skill_graph.get_skill_by_id(skill_id)
    
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    tutor = TutorOrchestrator(db, user.id)
    return await tutor.save_evidence(skill.id, evidence_type, content, mastery_boost)


# ==================== Simulation Routes ====================
@router.get("/simulations/{skill_id}")
async def get_simulations_for_skill(
    skill_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all simulations for a skill."""
    skill_graph = SkillGraphService(db)
    skill = await skill_graph.get_skill_by_id(skill_id)
    
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    sim_service = SimulationService(db)
    simulations = await sim_service.get_simulations_for_skill(skill.id)
    
    return [
        {
            "id": str(s.id),
            "name": s.name,
            "description": s.description,
            "simulation_type": s.simulation_type,
            "engine": s.engine,
            "difficulty": s.difficulty,
            "estimated_minutes": s.estimated_minutes,
            "learning_objectives": s.learning_objectives,
        }
        for s in simulations
    ]


@router.post("/simulations/run")
async def run_simulation(
    sim_data: SimulationRun,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Run a simulation."""
    sim_service = SimulationService(db)
    return await sim_service.run_simulation(
        UUID(sim_data.simulation_id),
        sim_data.config,
        sim_data.user_input
    )


# ==================== Project Routes ====================
@router.post("/projects")
async def create_project(
    project_data: ProjectCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new project."""
    skill_graph = SkillGraphService(db)
    skill = await skill_graph.get_skill_by_id(project_data.skill_id)
    
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    tutor = TutorOrchestrator(db, user.id)
    return await tutor.start_project(skill.id, project_data.model_dump())


@router.post("/projects/{project_id}/complete")
async def complete_project(
    project_id: UUID,
    completion: ProjectComplete,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Complete a project."""
    tutor = TutorOrchestrator(db, user.id)
    return await tutor.complete_project(project_id, completion.deliverables, completion.grade)


# ==================== Research Routes ====================
@router.post("/research/ingest")
async def ingest_research(
    query: str,
    max_results: int = 20,
    categories: Optional[List[str]] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Search and ingest papers from arXiv."""
    research = ResearchIngestionService(db)
    papers = await research.search_arxiv(query, max_results, categories)
    ingested = await research.ingest_arxiv_papers(papers)
    
    return {
        "ingested_count": len(ingested),
        "papers": [
            {
                "id": str(p.id),
                "arxiv_id": p.arxiv_id,
                "title": p.title,
                "authors": p.authors,
            }
            for p in ingested
        ]
    }


@router.get("/research/skill/{skill_id}")
async def get_research_for_skill(
    skill_id: str,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get research papers mapped to a skill."""
    skill_graph = SkillGraphService(db)
    skill = await skill_graph.get_skill_by_id(skill_id)
    
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    research = ResearchIngestionService(db)
    return await research.get_papers_for_skill(skill.id, limit)


# ==================== Review Routes ====================
@router.get("/reviews/due")
async def get_due_reviews(
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get skills due for review."""
    kt = KnowledgeTracingService(db)
    reviews = await kt.get_due_reviews(user.id, limit)
    
    return [
        {
            "id": str(r.id),
            "skill_id": str(r.skill_id),
            "scheduled_for": r.scheduled_for,
            "priority": r.priority,
            "review_type": r.review_type,
        }
        for r in reviews
    ]


@router.post("/reviews/{review_id}/complete")
async def complete_review(
    review_id: UUID,
    mastery_delta: float = 0.0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Complete a review."""
    kt = KnowledgeTracingService(db)
    return await kt.complete_review(review_id, mastery_delta)


# Import select for queries
from sqlalchemy import select
