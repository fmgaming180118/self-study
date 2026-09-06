"""
Skill Graph Service - Manages the knowledge graph of skills and prerequisites.
"""
from typing import List, Dict, Set, Optional, Tuple
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import Skill, MasteryRecord, MasteryLevel
import logging

logger = logging.getLogger(__name__)


class SkillGraphService:
    """Service for managing skill graph operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_skill_by_id(self, skill_id: str) -> Optional[Skill]:
        """Get skill by skill_id string (e.g., 'electronics.ohms_law')."""
        result = await self.db.execute(
            select(Skill).where(Skill.skill_id == skill_id)
        )
        return result.scalar_one_or_none()
    
    async def get_skill_by_uuid(self, skill_uuid: UUID) -> Optional[Skill]:
        """Get skill by UUID."""
        result = await self.db.execute(
            select(Skill).where(Skill.id == skill_uuid)
        )
        return result.scalar_one_or_none()
    
    async def get_all_skills(self) -> List[Skill]:
        """Get all skills ordered by category and difficulty."""
        result = await self.db.execute(
            select(Skill).order_by(Skill.category, Skill.difficulty, Skill.name)
        )
        return list(result.scalars().all())
    
    async def get_skills_by_category(self, category: str) -> List[Skill]:
        """Get all skills in a category."""
        result = await self.db.execute(
            select(Skill).where(Skill.category == category).order_by(Skill.difficulty)
        )
        return list(result.scalars().all())
    
    async def get_prerequisites(self, skill_id: UUID) -> List[Skill]:
        """Get direct prerequisites for a skill."""
        skill = await self.get_skill_by_uuid(skill_id)
        if not skill:
            return []
        
        # Load prerequisites
        await self.db.refresh(skill, ["prerequisites"])
        return skill.prerequisites
    
    async def get_all_prerequisites(self, skill_id: UUID, visited: Set[UUID] = None) -> Set[UUID]:
        """Get all prerequisites recursively (transitive closure)."""
        if visited is None:
            visited = set()
        
        if skill_id in visited:
            return visited
        
        visited.add(skill_id)
        prereqs = await self.get_prerequisites(skill_id)
        
        for prereq in prereqs:
            await self.get_all_prerequisites(prereq.id, visited)
        
        return visited
    
    async def get_dependents(self, skill_id: UUID) -> List[Skill]:
        """Get skills that depend on this skill."""
        skill = await self.get_skill_by_uuid(skill_id)
        if not skill:
            return []
        
        await self.db.refresh(skill, ["dependents"])
        return skill.dependents
    
    async def get_learning_path(self, target_skill_id: UUID, user_id: UUID) -> List[Skill]:
        """
        Get optimal learning path to reach target skill based on user's current mastery.
        Returns skills in topological order (prerequisites first).
        """
        # Get all prerequisites needed
        all_prereqs = await self.get_all_prerequisites(target_skill_id)
        
        # Get user's mastery for these skills
        mastery_records = await self.db.execute(
            select(MasteryRecord).where(
                MasteryRecord.user_id == user_id,
                MasteryRecord.skill_id.in_(all_prereqs)
            )
        )
        mastery_map = {mr.skill_id: mr for mr in mastery_records.scalars().all()}
        
        # Get all skills in the prerequisite chain
        skills_result = await self.db.execute(
            select(Skill).where(Skill.id.in_(all_prereqs))
        )
        skills = {s.id: s for s in skills_result.scalars().all()}
        
        # Topological sort based on prerequisites
        return self._topological_sort(skills, target_skill_id)
    
    def _topological_sort(self, skills: Dict[UUID, Skill], target_id: UUID) -> List[Skill]:
        """Topological sort of skills based on prerequisites."""
        # Build adjacency list
        graph = {sid: [] for sid in skills}
        in_degree = {sid: 0 for sid in skills}
        
        for sid, skill in skills.items():
            for prereq in skill.prerequisites:
                if prereq.id in skills:
                    graph[prereq.id].append(sid)
                    in_degree[sid] += 1
        
        # Kahn's algorithm
        queue = [sid for sid in skills if in_degree[sid] == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(skills[current])
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return result
    
    async def get_next_skills(self, user_id: UUID, limit: int = 5) -> List[Skill]:
        """
        Get recommended next skills for a user based on their current mastery.
        Prioritizes skills where all prerequisites are mastered.
        """
        # Get user's mastered skills (mastery >= 0.7)
        mastered_result = await self.db.execute(
            select(MasteryRecord.skill_id).where(
                MasteryRecord.user_id == user_id,
                MasteryRecord.mastery >= 0.7
            )
        )
        mastered_skills = set(mastered_result.scalars().all())
        
        # Get all skills not yet mastered
        all_skills_result = await self.db.execute(
            select(Skill).where(~Skill.id.in_(mastered_skills)) if mastered_skills else select(Skill)
        )
        all_skills = list(all_skills_result.scalars().all())
        
        # Score each skill based on prerequisite readiness
        scored_skills = []
        for skill in all_skills:
            prereqs = await self.get_prerequisites(skill.id)
            prereq_ids = {p.id for p in prereqs}
            
            if not prereq_ids:
                # No prerequisites - always available
                score = 1.0
            else:
                # Check how many prerequisites are mastered
                mastered_prereqs = prereq_ids & mastered_skills
                score = len(mastered_prereqs) / len(prereq_ids)
            
            # Boost score for skills that unlock many others
            dependents = await self.get_dependents(skill.id)
            unlock_bonus = min(len(dependents) * 0.1, 0.5)
            score += unlock_bonus
            
            scored_skills.append((skill, score))
        
        # Sort by score descending
        scored_skills.sort(key=lambda x: x[1], reverse=True)
        
        return [skill for skill, score in scored_skills[:limit]]
    
    async def check_prerequisites_met(self, skill_id: UUID, user_id: UUID, threshold: float = 0.7) -> Tuple[bool, List[Skill]]:
        """Check if all prerequisites for a skill are met by user."""
        prereqs = await self.get_prerequisites(skill_id)
        unmet = []
        
        for prereq in prereqs:
            result = await self.db.execute(
                select(MasteryRecord).where(
                    MasteryRecord.user_id == user_id,
                    MasteryRecord.skill_id == prereq.id
                )
            )
            mastery = result.scalar_one_or_none()
            
            if not mastery or mastery.mastery < threshold:
                unmet.append(prereq)
        
        return len(unmet) == 0, unmet
    
    async def create_skill(self, skill_data: dict) -> Skill:
        """Create a new skill."""
        skill = Skill(**skill_data)
        self.db.add(skill)
        await self.db.commit()
        await self.db.refresh(skill)
        return skill
    
    async def add_prerequisite(self, skill_id: UUID, prereq_id: UUID) -> bool:
        """Add a prerequisite relationship."""
        skill = await self.get_skill_by_uuid(skill_id)
        prereq = await self.get_skill_by_uuid(prereq_id)
        
        if not skill or not prereq:
            return False
        
        if prereq not in skill.prerequisites:
            skill.prerequisites.append(prereq)
            await self.db.commit()
        
        return True
    
    async def remove_prerequisite(self, skill_id: UUID, prereq_id: UUID) -> bool:
        """Remove a prerequisite relationship."""
        skill = await self.get_skill_by_uuid(skill_id)
        prereq = await self.get_skill_by_uuid(prereq_id)
        
        if not skill or not prereq:
            return False
        
        if prereq in skill.prerequisites:
            skill.prerequisites.remove(prereq)
            await self.db.commit()
        
        return True