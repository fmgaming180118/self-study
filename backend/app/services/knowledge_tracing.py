"""
Knowledge Tracing Service - Tracks and updates user mastery levels.
Based on the mastery levels defined in the specification:
- Not Started: 0-20%
- Understanding: 21-50%
- Guided Practice: 51-70%
- Independent: 71-85%
- Project Proven: 86-100%
"""
from typing import List, Dict, Optional, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import (
    MasteryRecord, MasteryLevel, AssessmentAttempt, LearningSession,
    Skill, Project, ReviewQueue
)
import logging
import math

logger = logging.getLogger(__name__)


class KnowledgeTracingService:
    """Service for tracking and updating user knowledge mastery."""
    
    # Mastery level thresholds
    MASTERY_THRESHOLDS = {
        MasteryLevel.NOT_STARTED: (0.0, 0.20),
        MasteryLevel.UNDERSTANDING: (0.21, 0.50),
        MasteryLevel.GUIDED_PRACTICE: (0.51, 0.70),
        MasteryLevel.INDEPENDENT: (0.71, 0.85),
        MasteryLevel.PROJECT_PROVEN: (0.86, 1.0),
    }
    
    # Spaced repetition intervals (in days) based on review count
    SPACED_INTERVALS = [1, 3, 7, 14, 30, 60, 120, 240]
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _get_mastery_level(self, mastery: float) -> MasteryLevel:
        """Determine mastery level from mastery score."""
        for level, (min_val, max_val) in self.MASTERY_THRESHOLDS.items():
            if min_val <= mastery <= max_val:
                return level
        return MasteryLevel.NOT_STARTED
    
    def _calculate_next_review(self, mastery_record: MasteryRecord) -> datetime:
        """Calculate next review date based on spaced repetition."""
        review_count = mastery_record.review_count
        if review_count >= len(self.SPACED_INTERVALS):
            interval = self.SPACED_INTERVALS[-1]
        else:
            interval = self.SPACED_INTERVALS[review_count]
        
        # Adjust interval based on mastery and confidence
        mastery_factor = 1.0 + (mastery_record.mastery * 0.5)  # 1.0 to 1.5
        confidence_factor = 1.0 + (mastery_record.confidence * 0.3)  # 1.0 to 1.3
        
        adjusted_interval = int(interval * mastery_factor * confidence_factor)
        return datetime.utcnow() + timedelta(days=adjusted_interval)
    
    async def get_or_create_mastery(self, user_id: UUID, skill_id: UUID) -> MasteryRecord:
        """Get existing mastery record or create new one."""
        result = await self.db.execute(
            select(MasteryRecord).where(
                MasteryRecord.user_id == user_id,
                MasteryRecord.skill_id == skill_id
            )
        )
        mastery = result.scalar_one_or_none()
        
        if not mastery:
            mastery = MasteryRecord(
                user_id=user_id,
                skill_id=skill_id,
                mastery=0.0,
                confidence=0.0,
                level=MasteryLevel.NOT_STARTED,
                evidence=[],
                review_count=0,
            )
            self.db.add(mastery)
            await self.db.commit()
            await self.db.refresh(mastery)
        
        return mastery
    
    async def update_mastery_from_assessment(
        self,
        user_id: UUID,
        skill_id: UUID,
        attempt: AssessmentAttempt
    ) -> MasteryRecord:
        """Update mastery based on assessment attempt."""
        mastery = await self.get_or_create_mastery(user_id, skill_id)
        
        # Calculate mastery delta based on score and assessment type
        score = attempt.score
        assessment = attempt.assessment
        
        # Weight based on assessment type
        type_weights = {
            "diagnostic": 0.1,
            "formative": 0.2,
            "summative": 0.3,
            "project": 0.5,
        }
        weight = type_weights.get(assessment.assessment_type, 0.2)
        
        # Calculate new mastery (weighted average with recency bias)
        old_mastery = mastery.mastery
        mastery_delta = (score - old_mastery) * weight
        
        # Apply confidence factor
        confidence_factor = 0.5 + (mastery.confidence * 0.5)  # 0.5 to 1.0
        mastery_delta *= confidence_factor
        
        new_mastery = max(0.0, min(1.0, old_mastery + mastery_delta))
        
        # Update confidence based on consistency
        if attempt.passed:
            mastery.confidence = min(1.0, mastery.confidence + 0.05)
        else:
            mastery.confidence = max(0.0, mastery.confidence - 0.1)
        
        mastery.mastery = new_mastery
        mastery.level = self._get_mastery_level(new_mastery)
        mastery.evidence.append(str(attempt.id))
        mastery.last_review = datetime.utcnow()
        mastery.next_review = self._calculate_next_review(mastery)
        mastery.review_count += 1
        mastery.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(mastery)
        
        logger.info(f"Updated mastery for user {user_id}, skill {skill_id}: {old_mastery:.2f} -> {new_mastery:.2f}")
        
        return mastery
    
    async def update_mastery_from_session(
        self,
        user_id: UUID,
        skill_id: UUID,
        session: LearningSession
    ) -> MasteryRecord:
        """Update mastery based on learning session."""
        mastery = await self.get_or_create_mastery(user_id, skill_id)
        
        # Small mastery gain for completing sessions
        session_gains = {
            "diagnostic": 0.02,
            "lesson": 0.03,
            "practice": 0.05,
            "assessment": 0.0,  # Handled separately
            "project": 0.1,
            "review": 0.02,
        }
        gain = session_gains.get(session.session_type, 0.01)
        
        # Boost gain if session was effective (mastery increased during session)
        if session.mastery_after > session.mastery_before:
            gain += (session.mastery_after - session.mastery_before) * 0.5
        
        old_mastery = mastery.mastery
        mastery.mastery = min(1.0, mastery.mastery + gain)
        mastery.level = self._get_mastery_level(mastery.mastery)
        mastery.last_review = datetime.utcnow()
        mastery.next_review = self._calculate_next_review(mastery)
        mastery.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(mastery)
        
        return mastery
    
    async def update_mastery_from_project(
        self,
        user_id: UUID,
        skill_id: UUID,
        project: Project
    ) -> MasteryRecord:
        """Update mastery based on project completion."""
        mastery = await self.get_or_create_mastery(user_id, skill_id)
        
        # Project provides significant mastery boost
        project_boost = project.mastery_evidence * 0.3  # Up to 30% boost
        
        old_mastery = mastery.mastery
        mastery.mastery = min(1.0, mastery.mastery + project_boost)
        
        # Projects significantly increase confidence
        mastery.confidence = min(1.0, mastery.confidence + 0.15)
        mastery.level = self._get_mastery_level(mastery.mastery)
        mastery.evidence.append(f"project:{project.id}")
        mastery.last_review = datetime.utcnow()
        mastery.next_review = self._calculate_next_review(mastery)
        mastery.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(mastery)
        
        return mastery
    
    async def decay_mastery(self, user_id: UUID, days_inactive: int = 30) -> List[MasteryRecord]:
        """
        Apply mastery decay for skills not reviewed recently.
        Called periodically by scheduler.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_inactive)
        
        result = await self.db.execute(
            select(MasteryRecord).where(
                MasteryRecord.user_id == user_id,
                MasteryRecord.last_review < cutoff_date,
                MasteryRecord.mastery > 0.2  # Don't decay below 20%
            )
        )
        records = list(result.scalars().all())
        
        decayed = []
        for record in records:
            days_since_review = (datetime.utcnow() - record.last_review).days
            # Decay rate: 1% per day after 30 days, max 5% per period
            decay_rate = min(0.05, max(0.0, (days_since_review - 30) * 0.01))
            
            old_mastery = record.mastery
            record.mastery = max(0.2, record.mastery - decay_rate)
            record.level = self._get_mastery_level(record.mastery)
            record.confidence = max(0.0, record.confidence - decay_rate * 0.5)
            record.updated_at = datetime.utcnow()
            
            decayed.append(record)
            logger.info(f"Decayed mastery for user {user_id}, skill {record.skill_id}: {old_mastery:.2f} -> {record.mastery:.2f}")
        
        if decayed:
            await self.db.commit()
        
        return decayed
    
    async def get_due_reviews(self, user_id: UUID, limit: int = 20) -> List[ReviewQueue]:
        """Get skills due for review."""
        now = datetime.utcnow()
        
        result = await self.db.execute(
            select(ReviewQueue).where(
                ReviewQueue.user_id == user_id,
                ReviewQueue.scheduled_for <= now,
                ReviewQueue.status == "pending"
            ).order_by(ReviewQueue.priority.desc(), ReviewQueue.scheduled_for)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def schedule_review(
        self,
        user_id: UUID,
        skill_id: UUID,
        mastery_record: MasteryRecord,
        review_type: str = "spaced_repetition"
    ) -> ReviewQueue:
        """Schedule a review for a skill."""
        next_review = self._calculate_next_review(mastery_record)
        
        # Priority based on mastery level (lower mastery = higher priority)
        priority_map = {
            MasteryLevel.NOT_STARTED: 10,
            MasteryLevel.UNDERSTANDING: 8,
            MasteryLevel.GUIDED_PRACTICE: 6,
            MasteryLevel.INDEPENDENT: 4,
            MasteryLevel.PROJECT_PROVEN: 2,
        }
        priority = priority_map.get(mastery_record.level, 5)
        
        # Boost priority for weak areas
        if mastery_record.mastery < 0.5:
            priority += 3
        
        review = ReviewQueue(
            user_id=user_id,
            skill_id=skill_id,
            mastery_record_id=mastery_record.id,
            scheduled_for=next_review,
            priority=priority,
            review_type=review_type,
            status="pending",
        )
        
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)
        
        return review
    
    async def complete_review(self, review_id: UUID, mastery_delta: float = 0.0) -> ReviewQueue:
        """Mark a review as completed."""
        result = await self.db.execute(
            select(ReviewQueue).where(ReviewQueue.id == review_id)
        )
        review = result.scalar_one_or_none()
        
        if not review:
            raise ValueError("Review not found")
        
        review.status = "completed"
        review.completed_at = datetime.utcnow()
        
        # Update mastery record
        mastery_result = await self.db.execute(
            select(MasteryRecord).where(MasteryRecord.id == review.mastery_record_id)
        )
        mastery = mastery_result.scalar_one_or_none()
        
        if mastery:
            mastery.last_review = datetime.utcnow()
            mastery.review_count += 1
            mastery.mastery = min(1.0, max(0.0, mastery.mastery + mastery_delta))
            mastery.level = self._get_mastery_level(mastery.mastery)
            mastery.next_review = self._calculate_next_review(mastery)
            mastery.updated_at = datetime.utcnow()
            
            # Schedule next review
            await self.schedule_review(
                review.user_id,
                review.skill_id,
                mastery,
                "spaced_repetition"
            )
        
        await self.db.commit()
        await self.db.refresh(review)
        
        return review
    
    async def get_user_mastery_summary(self, user_id: UUID) -> Dict:
        """Get summary of user's mastery across all skills."""
        result = await self.db.execute(
            select(MasteryRecord).where(MasteryRecord.user_id == user_id)
        )
        records = list(result.scalars().all())
        
        summary = {
            "total_skills": len(records),
            "by_level": {level.value: 0 for level in MasteryLevel},
            "average_mastery": 0.0,
            "average_confidence": 0.0,
            "skills_needing_review": 0,
            "total_evidence_count": 0,
        }
        
        if records:
            summary["average_mastery"] = sum(r.mastery for r in records) / len(records)
            summary["average_confidence"] = sum(r.confidence for r in records) / len(records)
            
            for record in records:
                summary["by_level"][record.level.value] += 1
                summary["total_evidence_count"] += len(record.evidence)
                
                if record.next_review and record.next_review <= datetime.utcnow():
                    summary["skills_needing_review"] += 1
        
        return summary
    
    async def get_skill_mastery_details(self, user_id: UUID, skill_id: UUID) -> Dict:
        """Get detailed mastery information for a specific skill."""
        mastery = await self.get_or_create_mastery(user_id, skill_id)
        skill_result = await self.db.execute(
            select(Skill).where(Skill.id == skill_id)
        )
        skill = skill_result.scalar_one_or_none()
        
        # Get recent attempts
        attempts_result = await self.db.execute(
            select(AssessmentAttempt).where(
                AssessmentAttempt.user_id == user_id,
                AssessmentAttempt.skill_id == skill_id
            ).order_by(AssessmentAttempt.completed_at.desc()).limit(10)
        )
        attempts = list(attempts_result.scalars().all())
        
        # Get recent sessions
        sessions_result = await self.db.execute(
            select(LearningSession).where(
                LearningSession.user_id == user_id,
                LearningSession.skill_id == skill_id
            ).order_by(LearningSession.started_at.desc()).limit(10)
        )
        sessions = list(sessions_result.scalars().all())
        
        # Get projects
        projects_result = await self.db.execute(
            select(Project).where(
                Project.user_id == user_id,
                Project.skill_id == skill_id
            ).order_by(Project.created_at.desc())
        )
        projects = list(projects_result.scalars().all())
        
        return {
            "skill": {
                "id": str(skill.id),
                "skill_id": skill.skill_id,
                "name": skill.name,
                "category": skill.category,
            } if skill else None,
            "mastery": {
                "value": mastery.mastery,
                "confidence": mastery.confidence,
                "level": mastery.level.value,
                "evidence_count": len(mastery.evidence),
                "last_review": mastery.last_review.isoformat() if mastery.last_review else None,
                "next_review": mastery.next_review.isoformat() if mastery.next_review else None,
                "review_count": mastery.review_count,
                "streak_days": mastery.streak_days,
            },
            "recent_attempts": [
                {
                    "id": str(a.id),
                    "score": a.score,
                    "passed": a.passed,
                    "completed_at": a.completed_at.isoformat() if a.completed_at else None,
                }
                for a in attempts
            ],
            "recent_sessions": [
                {
                    "id": str(s.id),
                    "type": s.session_type,
                    "duration_minutes": s.duration_minutes,
                    "mastery_before": s.mastery_before,
                    "mastery_after": s.mastery_after,
                    "started_at": s.started_at.isoformat(),
                }
                for s in sessions
            ],
            "projects": [
                {
                    "id": str(p.id),
                    "title": p.title,
                    "status": p.status,
                    "grade": p.grade,
                    "mastery_evidence": p.mastery_evidence,
                }
                for p in projects
            ],
        }