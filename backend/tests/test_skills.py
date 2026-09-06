import pytest
import uuid
from app.models import Skill


def test_skill_model_instantiation():
    skill = Skill(
        id=uuid.uuid4(),
        skill_id="test.circuit_analysis",
        name="Circuit Analysis",
        description="Kirchhoff's Laws, Thevenin, Norton",
        category="electronics",
        subcategory="analog",
        difficulty=3,
        estimated_hours=15.0,
        default_mastery=0.0,
        default_confidence=0.0,
    )
    assert skill.skill_id == "test.circuit_analysis"
    assert skill.category == "electronics"
    assert skill.difficulty == 3
