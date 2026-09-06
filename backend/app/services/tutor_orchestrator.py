"""
Tutor Orchestrator - Main orchestrator that coordinates learning activities.
Tools:
- read_progress()
- search_resources()
- generate_lesson()
- start_simulation()
- create_assessment()
- evaluate_answer()
- save_evidence()
- choose_next_skill()
"""
from typing import List, Dict, Optional, Any, AsyncGenerator, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import json
import logging

from app.models import (
    Skill, LearningResource, LearningSession, Assessment, AssessmentAttempt,
    MasteryRecord, Project, ProjectArtifact, Simulation, User, MasteryLevel
)
from app.services.skill_graph import SkillGraphService
from app.services.knowledge_tracing import KnowledgeTracingService
from app.config import settings

logger = logging.getLogger(__name__)


class TutorOrchestrator:
    """Main orchestrator for the learning system."""
    
    def __init__(self, db: AsyncSession, user_id: UUID):
        self.db = db
        self.user_id = user_id
        self.skill_graph = SkillGraphService(db)
        self.knowledge_tracing = KnowledgeTracingService(db)
    
    # ==================== TOOL 1: read_progress ====================
    async def read_progress(self, skill_id: Optional[UUID] = None) -> Dict:
        """
        Read user's current progress.
        If skill_id provided, returns detailed progress for that skill.
        Otherwise returns overall progress summary.
        """
        if skill_id:
            return await self.knowledge_tracing.get_skill_mastery_details(self.user_id, skill_id)
        else:
            return await self.knowledge_tracing.get_user_mastery_summary(self.user_id)
    
    # ==================== TOOL 2: search_resources ====================
    async def search_resources(
        self,
        skill_id: UUID,
        resource_type: Optional[str] = None,
        level: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Search for learning resources for a skill.
        Can filter by resource_type (video, article, book, tutorial, simulation, paper)
        and level (level_1_basic through level_6_preprint).
        """
        query = select(LearningResource).where(LearningResource.skill_id == skill_id)
        
        if resource_type:
            query = query.where(LearningResource.resource_type == resource_type)
        if level:
            query = query.where(LearningResource.level == level)
        
        query = query.order_by(
            LearningResource.quality_score.desc(),
            LearningResource.difficulty
        ).limit(limit)
        
        result = await self.db.execute(query)
        resources = list(result.scalars().all())
        
        return [
            {
                "id": str(r.id),
                "title": r.title,
                "description": r.description,
                "url": r.url,
                "resource_type": r.resource_type,
                "level": r.level.value if r.level else None,
                "source": r.source,
                "authors": r.authors,
                "quality_score": r.quality_score,
                "difficulty": r.difficulty,
                "estimated_minutes": r.estimated_minutes,
                "tags": r.tags,
            }
            for r in resources
        ]
    
    async def search_resources_semantic(
        self,
        query_text: str,
        skill_id: Optional[UUID] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Semantic search for resources using pgvector."""
        # This would use the embedding column for vector similarity search
        # For now, fallback to keyword search
        return await self.search_resources(skill_id, limit=limit)
    
    # ==================== TOOL 3: generate_lesson ====================
    async def generate_lesson(
        self,
        skill_id: UUID,
        session_type: str = "lesson",
        context: Optional[Dict] = None
    ) -> Dict:
        """
        Generate a personalized lesson for a skill.
        Uses the skill's prerequisites, user's mastery, and available resources.
        """
        skill = await self.skill_graph.get_skill_by_uuid(skill_id)
        if not skill:
            raise ValueError("Skill not found")
        
        # Get user's mastery for this skill
        mastery = await self.knowledge_tracing.get_or_create_mastery(self.user_id, skill_id)
        
        # Get prerequisites status
        prereqs_met, unmet_prereqs = await self.skill_graph.check_prerequisites_met(
            skill_id, self.user_id
        )
        
        # Get relevant resources
        resources = await self.search_resources(skill_id, limit=5)
        
        # Get simulations for this skill
        sim_result = await self.db.execute(
            select(Simulation).where(Simulation.skill_id == skill_id)
            .order_by(Simulation.difficulty)
        )
        simulations = list(sim_result.scalars().all())
        
        # Build lesson plan based on mastery level
        lesson_plan = self._build_lesson_plan(skill, mastery, prereqs_met, unmet_prereqs, resources, simulations)
        
        # Create learning session
        session = LearningSession(
            user_id=self.user_id,
            skill_id=skill_id,
            session_type=session_type,
            status="in_progress",
            mastery_before=mastery.mastery,
            confidence_before=mastery.confidence,
            session_metadata={
                "lesson_plan": lesson_plan,
                "context": context or {},
            }
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        
        return {
            "session_id": str(session.id),
            "skill": {
                "id": str(skill.id),
                "skill_id": skill.skill_id,
                "name": skill.name,
                "description": skill.description,
            },
            "mastery": {
                "current": mastery.mastery,
                "level": mastery.level.value,
                "confidence": mastery.confidence,
            },
            "prerequisites_met": prereqs_met,
            "unmet_prerequisites": [
                {"id": str(p.id), "name": p.name, "skill_id": p.skill_id}
                for p in unmet_prereqs
            ],
            "lesson_plan": lesson_plan,
            "resources": resources,
            "simulations": [
                {
                    "id": str(s.id),
                    "name": s.name,
                    "description": s.description,
                    "simulation_type": s.simulation_type,
                    "difficulty": s.difficulty,
                }
                for s in simulations
            ],
        }
    
    def _build_lesson_plan(
        self,
        skill: Skill,
        mastery: MasteryRecord,
        prereqs_met: bool,
        unmet_prereqs: List[Skill],
        resources: List[Dict],
        simulations: List[Simulation]
    ) -> Dict:
        """Build a structured lesson plan based on the 10-step cycle."""
        
        # Determine starting step based on mastery level
        step_map = {
            MasteryLevel.NOT_STARTED: 1,      # Diagnostic
            MasteryLevel.UNDERSTANDING: 2,    # Explanation
            MasteryLevel.GUIDED_PRACTICE: 4,  # Worked example
            MasteryLevel.INDEPENDENT: 5,      # Independent practice
            MasteryLevel.PROJECT_PROVEN: 8,   # Project
        }
        start_step = step_map.get(mastery.level, 1)
        
        # The 10-step learning cycle
        steps = [
            {
                "step": 1,
                "name": "Diagnostic Assessment",
                "description": "Short quiz to assess current understanding",
                "type": "assessment",
                "required": start_step <= 1,
            },
            {
                "step": 2,
                "name": "Conceptual Explanation",
                "description": "Simple explanation with analogies and visualizations",
                "type": "explanation",
                "required": start_step <= 2,
            },
            {
                "step": 3,
                "name": "Visual/Interactive Demo",
                "description": "Interactive simulation or visualization",
                "type": "simulation",
                "required": start_step <= 3 and len(simulations) > 0,
            },
            {
                "step": 4,
                "name": "Worked Example",
                "description": "Step-by-step problem solving together",
                "type": "worked_example",
                "required": start_step <= 4,
            },
            {
                "step": 5,
                "name": "Guided Practice",
                "description": "Practice problems with hints and feedback",
                "type": "practice",
                "required": start_step <= 5,
            },
            {
                "step": 6,
                "name": "Explain in Your Own Words",
                "description": "Articulate the concept to verify understanding",
                "type": "explanation_check",
                "required": start_step <= 6,
            },
            {
                "step": 7,
                "name": "Novel Problem",
                "description": "Apply concept to a new, different problem",
                "type": "transfer",
                "required": start_step <= 7,
            },
            {
                "step": 8,
                "name": "Mini Project",
                "description": "Build something real using this skill",
                "type": "project",
                "required": start_step <= 8,
            },
            {
                "step": 9,
                "name": "Spaced Review",
                "description": "Review after a few days to strengthen memory",
                "type": "review",
                "required": True,
            },
            {
                "step": 10,
                "name": "Mastery Update",
                "description": "Update mastery level based on evidence",
                "type": "assessment",
                "required": True,
            },
        ]
        
        return {
            "skill_id": skill.skill_id,
            "skill_name": skill.name,
            "current_mastery": mastery.mastery,
            "target_mastery": min(1.0, mastery.mastery + 0.15),
            "start_step": start_step,
            "steps": steps,
            "estimated_total_minutes": sum(
                r.get("estimated_minutes", 15) for r in resources
            ) + len(simulations) * 20,
        }
    
    # ==================== TOOL 4: start_simulation ====================
    async def start_simulation(
        self,
        simulation_id: UUID,
        parameters: Optional[Dict] = None
    ) -> Dict:
        """
        Start a simulation for a skill.
        Returns simulation configuration and initial state.
        """
        result = await self.db.execute(
            select(Simulation).where(Simulation.id == simulation_id)
        )
        simulation = result.scalar_one_or_none()
        
        if not simulation:
            raise ValueError("Simulation not found")
        
        # Merge default config with provided parameters
        config = simulation.config.copy()
        if parameters:
            config.update(parameters)
        
        # Create session for simulation
        session = LearningSession(
            user_id=self.user_id,
            skill_id=simulation.skill_id,
            session_type="simulation",
            status="in_progress",
            session_metadata={
                "simulation_id": str(simulation_id),
                "config": config,
                "scenario": simulation.scenario_template,
            }
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        
        return {
            "session_id": str(session.id),
            "simulation": {
                "id": str(simulation.id),
                "name": simulation.name,
                "description": simulation.description,
                "simulation_type": simulation.simulation_type,
                "engine": simulation.engine,
                "config": config,
                "scenario_template": simulation.scenario_template,
                "learning_objectives": simulation.learning_objectives,
                "assessment_criteria": simulation.assessment_criteria,
            },
            "initial_state": self._get_initial_simulation_state(simulation, config),
        }
    
    def _get_initial_simulation_state(self, simulation: Simulation, config: Dict) -> Dict:
        """Get initial state for simulation based on type."""
        if simulation.simulation_type == "circuit":
            return {
                "components": config.get("components", []),
                "voltage_sources": config.get("voltage_sources", []),
                "measurements": {},
            }
        elif simulation.simulation_type == "physics":
            return {
                "objects": config.get("objects", []),
                "forces": config.get("forces", []),
                "time": 0,
                "dt": config.get("dt", 0.01),
            }
        elif simulation.simulation_type == "coding":
            return {
                "starter_code": config.get("starter_code", ""),
                "test_cases": config.get("test_cases", []),
                "language": config.get("language", "python"),
            }
        else:
            return config.get("initial_state", {})
    
    async def run_simulation_step(
        self,
        session_id: UUID,
        action: str,
        parameters: Dict
    ) -> Dict:
        """Run a step in the simulation."""
        result = await self.db.execute(
            select(LearningSession).where(LearningSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise ValueError("Session not found")
        
        # This would integrate with actual simulation engines
        # For now, return a mock response
        return {
            "session_id": str(session_id),
            "action": action,
            "result": {"status": "executed", "output": "Simulation step completed"},
            "new_state": {},
            "measurements": {},
        }
    
    # ==================== TOOL 5: create_assessment ====================
    async def create_assessment(
        self,
        skill_id: UUID,
        assessment_type: str = "formative",
        num_questions: int = 5,
        difficulty: Optional[int] = None
    ) -> Dict:
        """
        Create an assessment for a skill.
        Can be diagnostic, formative, summative, or project-based.
        """
        skill = await self.skill_graph.get_skill_by_uuid(skill_id)
        if not skill:
            raise ValueError("Skill not found")
        
        mastery = await self.knowledge_tracing.get_or_create_mastery(self.user_id, skill_id)
        
        # Determine difficulty based on mastery if not specified
        if difficulty is None:
            difficulty = max(1, min(10, int(mastery.mastery * 10) + 1))
        
        # Generate questions (in production, this would use LLM)
        questions = await self._generate_assessment_questions(
            skill, assessment_type, num_questions, difficulty
        )
        
        assessment = Assessment(
            skill_id=skill_id,
            title=f"{skill.name} - {assessment_type.title()} Assessment",
            description=f"Assessment for {skill.name}",
            assessment_type=assessment_type,
            questions=questions,
            passing_score=0.7,
            time_limit_minutes=num_questions * 3,
            difficulty=difficulty,
        )
        self.db.add(assessment)
        await self.db.commit()
        await self.db.refresh(assessment)
        
        # Create attempt
        attempt = AssessmentAttempt(
            user_id=self.user_id,
            assessment_id=assessment.id,
            skill_id=skill_id,
            answers=[],
            attempt_metadata={"generated_for_mastery": mastery.mastery},
        )
        self.db.add(attempt)
        await self.db.commit()
        await self.db.refresh(attempt)
        
        return {
            "assessment_id": str(assessment.id),
            "attempt_id": str(attempt.id),
            "skill": {"id": str(skill.id), "name": skill.name},
            "assessment_type": assessment_type,
            "num_questions": num_questions,
            "difficulty": difficulty,
            "time_limit_minutes": assessment.time_limit_minutes,
            "questions": questions,
        }
    
    async def _generate_assessment_questions(
        self,
        skill: Skill,
        assessment_type: str,
        num_questions: int,
        difficulty: int
    ) -> List[Dict]:
        """Generate assessment questions (placeholder for LLM integration)."""
        # In production, this would call an LLM to generate questions
        # based on skill description, prerequisites, and learning objectives
        
        question_templates = {
            "diagnostic": [
                {"type": "multiple_choice", "difficulty": 1},
                {"type": "multiple_choice", "difficulty": 2},
                {"type": "true_false", "difficulty": 1},
            ],
            "formative": [
                {"type": "multiple_choice", "difficulty": 2},
                {"type": "short_answer", "difficulty": 3},
                {"type": "multiple_choice", "difficulty": 2},
            ],
            "summative": [
                {"type": "short_answer", "difficulty": 4},
                {"type": "problem_solving", "difficulty": 5},
                {"type": "explanation", "difficulty": 4},
            ],
            "project": [
                {"type": "project_rubric", "difficulty": 5},
            ],
        }
        
        templates = question_templates.get(assessment_type, question_templates["formative"])
        questions = []
        
        for i in range(num_questions):
            template = templates[i % len(templates)]
            questions.append({
                "id": f"q_{i+1}",
                "type": template["type"],
                "difficulty": min(10, template["difficulty"] + difficulty - 3),
                "question": f"Question {i+1} for {skill.name} ({template['type']})",
                "options": ["A", "B", "C", "D"] if template["type"] == "multiple_choice" else None,
                "correct_answer": "A" if template["type"] == "multiple_choice" else None,
                "points": 1,
                "skill_concepts": [skill.skill_id],
            })
        
        return questions
    
    # ==================== TOOL 6: evaluate_answer ====================
    async def evaluate_answer(
        self,
        attempt_id: UUID,
        question_id: str,
        answer: Any
    ) -> Dict:
        """
        Evaluate a single answer in an assessment attempt.
        Returns correctness, feedback, and partial credit.
        """
        result = await self.db.execute(
            select(AssessmentAttempt).where(AssessmentAttempt.id == attempt_id)
        )
        attempt = result.scalar_one_or_none()
        
        if not attempt:
            raise ValueError("Attempt not found")
        
        assessment_result = await self.db.execute(
            select(Assessment).where(Assessment.id == attempt.assessment_id)
        )
        assessment = assessment_result.scalar_one_or_none()
        
        if not assessment:
            raise ValueError("Assessment not found")
        
        # Find the question
        question = next((q for q in assessment.questions if q["id"] == question_id), None)
        if not question:
            raise ValueError("Question not found")
        
        # Evaluate based on question type
        is_correct, feedback, partial_credit = self._evaluate_question(question, answer)
        
        # Update attempt
        attempt.answers.append({
            "question_id": question_id,
            "answer": answer,
            "correct": is_correct,
            "partial_credit": partial_credit,
            "feedback": feedback,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # Recalculate score
        total_points = sum(q.get("points", 1) for q in assessment.questions)
        earned_points = sum(
            a.get("partial_credit", 1.0 if a["correct"] else 0.0) * 
            next((q.get("points", 1) for q in assessment.questions if q["id"] == a["question_id"]), 1)
            for a in attempt.answers
        )
        attempt.score = earned_points / total_points if total_points > 0 else 0
        attempt.passed = attempt.score >= assessment.passing_score
        
        await self.db.commit()
        await self.db.refresh(attempt)
        
        return {
            "question_id": question_id,
            "correct": is_correct,
            "partial_credit": partial_credit,
            "feedback": feedback,
            "current_score": attempt.score,
            "passed_so_far": attempt.passed,
        }
    
    def _evaluate_question(self, question: Dict, answer: Any) -> Tuple[bool, str, float]:
        """Evaluate a single question."""
        q_type = question.get("type", "multiple_choice")
        correct = question.get("correct_answer")
        
        if q_type == "multiple_choice":
            is_correct = str(answer).strip().upper() == str(correct).strip().upper()
            return is_correct, "Correct!" if is_correct else f"Incorrect. The answer was {correct}.", 1.0 if is_correct else 0.0
        
        elif q_type == "true_false":
            is_correct = str(answer).strip().lower() == str(correct).strip().lower()
            return is_correct, "Correct!" if is_correct else "Incorrect.", 1.0 if is_correct else 0.0
        
        elif q_type == "short_answer":
            # In production, use LLM for semantic evaluation
            is_correct = str(answer).strip().lower() == str(correct).strip().lower()
            return is_correct, "Correct!" if is_correct else "Check your answer.", 1.0 if is_correct else 0.0
        
        elif q_type == "explanation":
            # Use LLM to evaluate explanation quality
            return True, "Explanation received. Will be evaluated.", 0.5
        
        elif q_type == "problem_solving":
            # Check steps and final answer
            return True, "Solution received. Will be evaluated.", 0.5
        
        else:
            return False, "Unknown question type", 0.0
    
    async def complete_assessment(self, attempt_id: UUID) -> Dict:
        """Complete an assessment attempt and update mastery."""
        result = await self.db.execute(
            select(AssessmentAttempt).where(AssessmentAttempt.id == attempt_id)
        )
        attempt = result.scalar_one_or_none()
        
        if not attempt:
            raise ValueError("Attempt not found")
        
        attempt.completed_at = datetime.utcnow()
        attempt.duration_minutes = int(
            (attempt.completed_at - attempt.started_at).total_seconds() / 60
        )
        
        # Update mastery
        mastery = await self.knowledge_tracing.update_mastery_from_assessment(
            self.user_id, attempt.skill_id, attempt
        )
        
        await self.db.commit()
        await self.db.refresh(attempt)
        
        return {
            "attempt_id": str(attempt.id),
            "final_score": attempt.score,
            "passed": attempt.passed,
            "mastery_before": mastery.mastery - (attempt.mastery_delta or 0),
            "mastery_after": mastery.mastery,
            "mastery_level": mastery.level.value,
            "confidence": mastery.confidence,
            "next_review": mastery.next_review.isoformat() if mastery.next_review else None,
        }
    
    # ==================== TOOL 7: save_evidence ====================
    async def save_evidence(
        self,
        skill_id: UUID,
        evidence_type: str,
        content: Dict,
        mastery_boost: float = 0.0
    ) -> Dict:
        """
        Save evidence of learning (code, circuit, report, etc.).
        Updates mastery based on evidence quality.
        """
        mastery = await self.knowledge_tracing.get_or_create_mastery(self.user_id, skill_id)
        
        evidence_id = f"{evidence_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        mastery.evidence.append(evidence_id)
        
        if mastery_boost > 0:
            old_mastery = mastery.mastery
            mastery.mastery = min(1.0, mastery.mastery + mastery_boost)
            mastery.level = self.knowledge_tracing._get_mastery_level(mastery.mastery)
            mastery.confidence = min(1.0, mastery.confidence + 0.05)
        
        mastery.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(mastery)
        
        return {
            "evidence_id": evidence_id,
            "skill_id": str(skill_id),
            "evidence_type": evidence_type,
            "mastery_before": old_mastery if mastery_boost > 0 else mastery.mastery,
            "mastery_after": mastery.mastery,
            "mastery_level": mastery.level.value,
        }
    
    # ==================== TOOL 8: choose_next_skill ====================
    async def choose_next_skill(self, limit: int = 5) -> List[Dict]:
        """
        Recommend next skills to learn based on current mastery and prerequisites.
        """
        next_skills = await self.skill_graph.get_next_skills(self.user_id, limit)
        
        recommendations = []
        for skill in next_skills:
            prereqs_met, unmet = await self.skill_graph.check_prerequisites_met(skill.id, self.user_id)
            mastery_result = await self.db.execute(
                select(MasteryRecord).where(
                    MasteryRecord.user_id == self.user_id,
                    MasteryRecord.skill_id == skill.id
                )
            )
            mastery = mastery_result.scalar_one_or_none()
            
            recommendations.append({
                "skill": {
                    "id": str(skill.id),
                    "skill_id": skill.skill_id,
                    "name": skill.name,
                    "description": skill.description,
                    "category": skill.category,
                    "difficulty": skill.difficulty,
                    "estimated_hours": skill.estimated_hours,
                },
                "prerequisites_met": prereqs_met,
                "unmet_prerequisites": [
                    {"id": str(p.id), "name": p.name, "skill_id": p.skill_id}
                    for p in unmet
                ],
                "current_mastery": mastery.mastery if mastery else 0.0,
                "current_level": mastery.level.value if mastery else MasteryLevel.NOT_STARTED.value,
                "recommendation_reason": self._get_recommendation_reason(skill, prereqs_met, mastery),
            })
        
        return recommendations
    
    def _get_recommendation_reason(self, skill: Skill, prereqs_met: bool, mastery: Optional[MasteryRecord]) -> str:
        """Generate human-readable recommendation reason."""
        if not prereqs_met:
            return "Prerequisites not yet mastered"
        if mastery and mastery.mastery >= 0.7:
            return "Ready for next level - prerequisites mastered"
        if mastery and mastery.mastery > 0:
            return "Continue building on existing knowledge"
        return "New skill - all prerequisites met"
    
    # ==================== Additional Helper Methods ====================
    async def get_learning_path(self, target_skill_id: UUID) -> List[Dict]:
        """Get the full learning path to a target skill."""
        path = await self.skill_graph.get_learning_path(target_skill_id, self.user_id)
        
        result = []
        for skill in path:
            mastery_result = await self.db.execute(
                select(MasteryRecord).where(
                    MasteryRecord.user_id == self.user_id,
                    MasteryRecord.skill_id == skill.id
                )
            )
            mastery = mastery_result.scalar_one_or_none()
            
            result.append({
                "skill": {
                    "id": str(skill.id),
                    "skill_id": skill.skill_id,
                    "name": skill.name,
                    "category": skill.category,
                    "difficulty": skill.difficulty,
                },
                "mastery": mastery.mastery if mastery else 0.0,
                "level": mastery.level.value if mastery else MasteryLevel.NOT_STARTED.value,
                "prerequisites_met": True,  # By definition in path
            })
        
        return result
    
    async def start_project(self, skill_id: UUID, project_data: Dict) -> Dict:
        """Start a new project for a skill."""
        skill = await self.skill_graph.get_skill_by_uuid(skill_id)
        if not skill:
            raise ValueError("Skill not found")
        
        project = Project(
            user_id=self.user_id,
            skill_id=skill_id,
            title=project_data.get("title", f"{skill.name} Project"),
            description=project_data.get("description", ""),
            project_type=project_data.get("project_type", "coding"),
            status="planning",
            requirements=project_data.get("requirements", []),
            deliverables=project_data.get("deliverables", []),
            project_metadata=project_data.get("metadata", {}),
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        
        return {
            "project_id": str(project.id),
            "skill": {"id": str(skill.id), "name": skill.name},
            "title": project.title,
            "status": project.status,
        }
    
    async def complete_project(self, project_id: UUID, deliverables: List[Dict], grade: str = "pass") -> Dict:
        """Complete a project and update mastery."""
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            raise ValueError("Project not found")
        
        project.status = "completed"
        project.completed_at = datetime.utcnow()
        project.actual_deliverables = deliverables
        project.grade = grade
        project.mastery_evidence = 0.3 if grade == "pass" else 0.1
        
        # Add artifacts
        for d in deliverables:
            artifact = ProjectArtifact(
                project_id=project_id,
                name=d.get("name", "Deliverable"),
                artifact_type=d.get("type", "report"),
                content=d.get("content"),
                file_path=d.get("file_path"),
                url=d.get("url"),
                artifact_metadata=d.get("metadata", {}),
            )
            self.db.add(artifact)
        
        # Update mastery
        mastery = await self.knowledge_tracing.update_mastery_from_project(
            self.user_id, project.skill_id, project
        )
        
        await self.db.commit()
        await self.db.refresh(project)
        
        return {
            "project_id": str(project.id),
            "skill_id": str(project.skill_id),
            "grade": project.grade,
            "mastery_evidence": project.mastery_evidence,
            "mastery_after": mastery.mastery,
            "mastery_level": mastery.level.value,
        }
