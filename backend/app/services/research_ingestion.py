"""
Research Ingestion Service - Fetches papers from arXiv and OpenAlex.
Maps papers to skills in the knowledge graph.
"""
from typing import List, Dict, Optional, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import arxiv
import httpx
import asyncio
import logging
import json

from app.models import ResearchPaper, Citation, PaperSkillMapping, Skill, LearningResource, ResourceLevel
from app.config import settings

logger = logging.getLogger(__name__)


class ResearchIngestionService:
    """Service for ingesting research papers from arXiv and OpenAlex."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.arxiv_client = arxiv.Client(
            page_size=100,
            delay_seconds=settings.ARXIV_API_DELAY,
            num_retries=3,
        )
    
    # ==================== arXiv Integration ====================
    async def search_arxiv(
        self,
        query: str,
        max_results: int = 50,
        categories: Optional[List[str]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Dict]:
        """Search arXiv for papers."""
        # Build search query
        search_query = query
        if categories:
            cat_query = " OR ".join([f"cat:{c}" for c in categories])
            search_query = f"({search_query}) AND ({cat_query})"
        
        if date_from:
            search_query += f" AND submittedDate:[{date_from.strftime('%Y%m%d')} TO *]"
        if date_to:
            search_query += f" AND submittedDate:[* TO {date_to.strftime('%Y%m%d')}]"
        
        search = arxiv.Search(
            query=search_query,
            max_results=max_results,
            sort_by=arxiv.SortBy.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )
        
        papers = []
        try:
            for paper in self.arxiv_client.results(search):
                papers.append({
                    "arxiv_id": paper.entry_id.split("/")[-1],
                    "title": paper.title,
                    "abstract": paper.summary,
                    "authors": [a.name for a in paper.authors],
                    "categories": paper.categories,
                    "primary_category": paper.primary_category,
                    "published_date": paper.published,
                    "updated_date": paper.updated,
                    "pdf_url": paper.pdf_url,
                    "doi": paper.doi,
                    "journal_ref": paper.journal_ref,
                    "comment": paper.comment,
                })
        except Exception as e:
            logger.error(f"arXiv search error: {e}")
        
        return papers
    
    async def ingest_arxiv_papers(
        self,
        papers: List[Dict],
        map_to_skills: bool = True
    ) -> List[ResearchPaper]:
        """Ingest papers into database."""
        ingested = []
        
        for paper_data in papers:
            # Check if already exists
            result = await self.db.execute(
                select(ResearchPaper).where(ResearchPaper.arxiv_id == paper_data["arxiv_id"])
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update if needed
                for key, value in paper_data.items():
                    if hasattr(existing, key) and key != "arxiv_id":
                        setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
                paper = existing
            else:
                paper = ResearchPaper(**paper_data)
                self.db.add(paper)
            
            ingested.append(paper)
        
        await self.db.commit()
        
        # Refresh to get IDs
        for paper in ingested:
            await self.db.refresh(paper)
        
        # Map to skills if requested
        if map_to_skills:
            await self._map_papers_to_skills(ingested)
        
        return ingested
    
    async def fetch_and_ingest_by_category(
        self,
        category: str,
        max_results: int = 100,
        days_back: int = 30
    ) -> List[ResearchPaper]:
        """Fetch and ingest recent papers from an arXiv category."""
        date_from = datetime.utcnow() - timedelta(days=days_back)
        papers = await self.search_arxiv(
            query="",
            max_results=max_results,
            categories=[category],
            date_from=date_from,
        )
        return await self.ingest_arxiv_papers(papers)
    
    # ==================== OpenAlex Integration ====================
    async def search_openalex(
        self,
        query: str,
        max_results: int = 50,
        filter_params: Optional[Dict] = None
    ) -> List[Dict]:
        """Search OpenAlex for works."""
        url = "https://api.openalex.org/works"
        
        params = {
            "search": query,
            "per_page": min(max_results, 200),
        }
        
        if filter_params:
            for key, value in filter_params.items():
                params[f"filter[{key}]"] = value
        
        if settings.OPENALEX_API_KEY:
            params["api_key"] = settings.OPENALEX_API_KEY
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        works = []
        for work in data.get("results", []):
            works.append({
                "openalex_id": work.get("id"),
                "title": work.get("title"),
                "abstract": self._reconstruct_abstract(work.get("abstract_inverted_index", {})),
                "authors": [a["author"]["display_name"] for a in work.get("authorships", [])],
                "published_date": work.get("publication_date"),
                "doi": work.get("doi"),
                "cited_by_count": work.get("cited_by_count", 0),
                "concepts": [c["display_name"] for c in work.get("concepts", [])],
                "topics": [t["display_name"] for t in work.get("topics", [])],
                "keywords": work.get("keywords", []),
                "referenced_works": work.get("referenced_works", []),
                "related_works": work.get("related_works", []),
                "open_access": work.get("open_access", {}),
                "metadata": work,
            })
        
        return works
    
    def _reconstruct_abstract(self, inverted_index: Dict) -> str:
        """Reconstruct abstract from OpenAlex inverted index."""
        if not inverted_index:
            return ""
        
        # Inverted index maps word -> list of positions
        max_pos = max(max(positions) for positions in inverted_index.values())
        words = [""] * (max_pos + 1)
        
        for word, positions in inverted_index.items():
            for pos in positions:
                words[pos] = word
        
        return " ".join(words)
    
    async def get_citation_graph(
        self,
        work_id: str,
        depth: int = 2
    ) -> Dict:
        """Get citation graph for a work from OpenAlex."""
        # This would recursively fetch references and citing works
        # For now, return basic structure
        return {
            "work_id": work_id,
            "references": [],
            "cited_by": [],
            "depth": depth,
        }
    
    # ==================== Skill Mapping ====================
    async def _map_papers_to_skills(self, papers: List[ResearchPaper]) -> None:
        """Map papers to relevant skills using keyword matching and LLM."""
        # Get all skills
        skills_result = await self.db.execute(select(Skill))
        skills = list(skills_result.scalars().all())
        
        # Build skill keyword index
        skill_keywords = {}
        for skill in skills:
            keywords = set()
            keywords.add(skill.skill_id.lower())
            keywords.add(skill.name.lower())
            keywords.update(skill.category.lower().split())
            keywords.update(skill.subcategory.lower().split() if skill.subcategory else [])
            if skill.description:
                # Extract key terms from description
                words = skill.description.lower().split()
                keywords.update([w for w in words if len(w) > 4])
            skill_keywords[skill.id] = keywords
        
        for paper in papers:
            # Combine searchable text
            search_text = " ".join([
                paper.title or "",
                paper.abstract or "",
                " ".join(paper.authors or []),
                " ".join(paper.categories or []),
            ]).lower()
            
            # Find matching skills
            for skill_id, keywords in skill_keywords.items():
                matches = sum(1 for kw in keywords if kw in search_text)
                if matches > 0:
                    relevance = min(1.0, matches / max(len(keywords), 1) * 5)
                    
                    if relevance > 0.1:  # Threshold
                        # Check if mapping exists
                        result = await self.db.execute(
                            select(PaperSkillMapping).where(
                                PaperSkillMapping.paper_id == paper.id,
                                PaperSkillMapping.skill_id == skill_id
                            )
                        )
                        existing = result.scalar_one_or_none()
                        
                        if not existing:
                            mapping = PaperSkillMapping(
                                paper_id=paper.id,
                                skill_id=skill_id,
                                relevance_score=relevance,
                                mapping_type="teaches" if relevance > 0.5 else "related",
                            )
                            self.db.add(mapping)
        
        await self.db.commit()
    
    async def get_papers_for_skill(
        self,
        skill_id: UUID,
        limit: int = 20,
        min_relevance: float = 0.3
    ) -> List[Dict]:
        """Get research papers mapped to a skill."""
        result = await self.db.execute(
            select(PaperSkillMapping, ResearchPaper)
            .join(ResearchPaper)
            .where(
                PaperSkillMapping.skill_id == skill_id,
                PaperSkillMapping.relevance_score >= min_relevance
            )
            .order_by(PaperSkillMapping.relevance_score.desc())
            .limit(limit)
        )
        
        papers = []
        for mapping, paper in result.all():
            papers.append({
                "paper": {
                    "id": str(paper.id),
                    "arxiv_id": paper.arxiv_id,
                    "title": paper.title,
                    "abstract": paper.abstract,
                    "authors": paper.authors,
                    "categories": paper.categories,
                    "published_date": paper.published_date.isoformat() if paper.published_date else None,
                    "pdf_url": paper.pdf_url,
                    "doi": paper.doi,
                },
                "mapping": {
                    "relevance_score": mapping.relevance_score,
                    "mapping_type": mapping.mapping_type,
                }
            })
        
        return papers
    
    # ==================== Resource Creation ====================
    async def create_resources_from_papers(
        self,
        skill_id: UUID,
        papers: List[ResearchPaper],
        resource_level: ResourceLevel = ResourceLevel.PEER_REVIEWED
    ) -> List[LearningResource]:
        """Create learning resources from research papers."""
        resources = []
        
        for paper in papers:
            # Check if resource already exists
            result = await self.db.execute(
                select(LearningResource).where(
                    LearningResource.skill_id == skill_id,
                    LearningResource.source == "arxiv",
                    LearningResource.source_id == paper.arxiv_id
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                continue
            
            resource = LearningResource(
                skill_id=skill_id,
                title=paper.title,
                description=paper.abstract[:500] if paper.abstract else "",
                url=paper.pdf_url,
                resource_type="paper",
                level=resource_level,
                source="arxiv",
                source_id=paper.arxiv_id,
                authors=paper.authors,
                published_date=paper.published_date,
                quality_score=0.7,  # Default for peer-reviewed
                difficulty=7,  # Papers are generally advanced
                estimated_minutes=30,
                tags=paper.categories or [],
                metadata={
                    "arxiv_id": paper.arxiv_id,
                    "doi": paper.doi,
                    "journal_ref": paper.journal_ref,
                }
            )
            self.db.add(resource)
            resources.append(resource)
        
        await self.db.commit()
        
        for r in resources:
            await self.db.refresh(r)
        
        return resources
    
    # ==================== Consensus Integration (Optional) ====================
    async def search_consensus(
        self,
        query: str,
        max_results: int = 10
    ) -> List[Dict]:
        """Search Consensus for research papers (requires API key)."""
        if not settings.CONSENSUS_API_KEY:
            logger.warning("Consensus API key not configured")
            return []
        
        url = "https://api.consensus.app/v1/search"
        headers = {"Authorization": f"Bearer {settings.CONSENSUS_API_KEY}"}
        params = {"query": query, "limit": max_results}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
            if response.status_code == 200:
                return response.json().get("results", [])
            else:
                logger.error(f"Consensus search error: {response.status_code}")
                return []
    
    # ==================== Scheduled Ingestion ====================
    async def scheduled_ingestion(self) -> Dict:
        """Run scheduled ingestion for all skill categories."""
        # Map skill categories to arXiv categories
        category_map = {
            "math": ["math.OC", "math.NA", "math.PR", "math.ST"],
            "physics": ["physics.class-ph", "physics.comp-ph", "physics.ed-ph"],
            "electronics": ["physics.app-ph", "eess.SP", "eess.SY"],
            "programming": ["cs.PL", "cs.SE", "cs.DS", "cs.AI"],
            "ai": ["cs.LG", "cs.CV", "cs.CL", "cs.RO", "stat.ML"],
            "robotics": ["cs.RO", "eess.SY", "cs.SY"],
            "control": ["eess.SY", "cs.SY", "math.OC"],
        }
        
        results = {}
        for skill_cat, arxiv_cats in category_map.items():
            for arxiv_cat in arxiv_cats:
                try:
                    papers = await self.fetch_and_ingest_by_category(
                        arxiv_cat, max_results=20, days_back=7
                    )
                    results[f"{skill_cat}:{arxiv_cat}"] = len(papers)
                    await asyncio.sleep(settings.ARXIV_API_DELAY)
                except Exception as e:
                    logger.error(f"Error ingesting {arxiv_cat}: {e}")
                    results[f"{skill_cat}:{arxiv_cat}"] = f"Error: {e}"
        
        return results