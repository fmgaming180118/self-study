"""
Initial data population script for the Self Study OS.
Creates the foundational skills for the MVP learning path.
"""
import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models import Base, Skill
from app.config import settings
from app.database import init_db as db_init_db

# Sample skills for the MVP learning path: Math → Python → Electronics → Embedded → AI
SAMPLE_SKILLS = [
    # Mathematics Foundation
    {
        "skill_id": "math.arithmetic",
        "name": "Arithmetic",
        "description": "Basic arithmetic operations, fractions, decimals, and percentages",
        "category": "math",
        "subcategory": "arithmetic",
        "difficulty": 1,
        "estimated_hours": 10,
        "default_mastery": 0.0,
        "default_confidence": 0.0
    },
    {
        "skill_id": "math.basic_algebra",
        "name": "Basic Algebra",
        "description": "Variables, equations, inequalities, and basic functions",
        "category": "math",
        "subcategory": "algebra",
        "difficulty": 2,
        "estimated_hours": 15,
        "default_mastery": 0.0,
        "default_confidence": 0.0
    },
    {
        "skill_id": "math.functions",
        "name": "Functions and Graphs",
        "description": "Understanding functions, domain/range, transformations, and basic graphing",
        "category": "math",
        "subcategory": "algebra",
        "difficulty": 3,
        "estimated_hours": 20,
        "default_mastery": 0.0,
        "default_confidence": 0.0
    },
    {
        "skill_id": "math.vectors",
        "name": "Vectors",
        "description": "Vector operations, dot product, cross product, and applications",
        "category": "math",
        "subcategory": "linear_algebra",
        "difficulty": 3,
        "estimated_hours": 15,
        "default_mastery": 0.0,
        "default_confidence": 0.0
    },
    {
        "skill_id": "math.linear_algebra",
        "name": "Linear Algebra",
        "description": "Matrices, determinants, eigenvalues, and linear transformations",
        "category": "math",
        "subcategory": "linear_algebra",
        "difficulty": 4,
        "estimated_hours": 25,
        "default_mastery": 0.0,
        "default_confidence": 0.0
    },
    
    # Programming Foundation
    {
        "skill_id": "programming.python_basics",
        "name": "Python Basics",
        "description": "Python syntax, data types, control flow, and basic data structures",
        "category": "programming",
        "subcategory": "python",
        "difficulty": 2,
        "estimated_hours": 20,
        "default_mastery": 0.0,
        "default_confidence": 0.0
    },
    {
        "skill_id": "programming.data_structures",
        "name": "Data Structures",
        "description": "Arrays, lists, stacks, queues, trees, and hash tables",
        "category": "programming",
        "subcategory": "algorithms",
        "difficulty": 3,
        "estimated_hours": 25,
        "default_mastery": 0.0,
        "default_confidence": 0.0
    },
    {
        "skill_id": "programming.algorithms",
        "name": "Algorithms",
        "description": "Sorting, searching, recursion, and algorithmic complexity",
        "category": "programming",
        "subcategory": "algorithms",
        "difficulty": 4,
        "estimated_hours": 30,
        "default_mastery": 0.0,
        "default_confidence": 0.0
    },
    
    # Electronics Foundation
    {
        "skill_id": "electronics.ohms_law",
        "name": "Ohm's Law",
        "description": "Relationship between voltage, current, and resistance",
        "category": "electronics",
        "subcategory": "basics",
        "difficulty": 2,
        "estimated_hours": 5,
        "default_mastery": 0.0,
        "default_confidence": 0.0
    },
    {
        "skill_id": "electronics.basic_circuits",
        "name": "Basic Circuits",
        "description": "Series and parallel circuits, Kirchhoff's laws, and circuit analysis",
        "category": "electronics",
        "subcategory": "basics",
        "difficulty": 3,
        "estimated_hours": 15,
        "default_mastery": 0.0,
        "default_confidence": 0.0
    },
    {
        "skill_id": "electronics.digital_logic",
        "name": "Digital Logic",
        "description": "Boolean algebra, logic gates, combinational and sequential logic",
        "category": "electronics",
        "subcategory": "digital",
        "difficulty": 3,
        "estimated_hours": 20,
        "default_mastery": 0.0,
        "default_confidence": 0.0
    },
    {
        "skill_id": "electronics.semiconductors",
        "name": "Semiconductors",
        "description": "Diodes, transistors, and basic semiconductor physics",
        "category": "electronics",
        "subcategory": "components",
        "difficulty": 4,
        "estimated_hours": 20,
        "default_mastery": 0.0,
        "default_confidence": 0.0
    },
    
    # Embedded Systems
    {
        "skill_id": "embedded.microcontrollers",
        "name": "Microcontrollers",
        "description": "Architecture, programming, and interfacing of microcontrollers",
        "category": "embedded",
        "subcategory": "hardware",
        "difficulty": 4,
        "estimated_hours": 25,
        "default_mastery": 0.0,
        "default_confidence": 0.0
    },
    {
        "skill_id": "embedded.sensors",
        "name": "Sensors and Actuators",
        "description": "Types of sensors, interfacing, and basic control systems",
        "category": "embedded",
        "subcategory": "hardware",
        "difficulty": 4,
        "estimated_hours": 20,
        "default_mastery": 0.0,
        "default_confidence": 0.0
    },
    {
        "skill_id": "embedded.rtos",
        "name": "Real-Time Systems",
        "description": "Real-time operating systems, task scheduling, and timing constraints",
        "category": "embedded",
        "subcategory": "software",
        "difficulty": 5,
        "estimated_hours": 30,
        "default_mastery": 0.0,
        "default_confidence": 0.0
    },
    
    # AI Mathematics
    {
        "skill_id": "ai.probability",
        "name": "Probability Theory",
        "description": "Probability distributions, expectation, variance, and common distributions",
        "category": "ai",
        "subcategory": "mathematics",
        "difficulty": 4,
        "estimated_hours": 20,
        "default_mastery": 0.0,
        "default_confidence": 0.0
    },
    {
        "skill_id": "ai.statistics",
        "name": "Statistics",
        "description": "Descriptive statistics, inference, hypothesis testing, and regression",
        "category": "ai",
        "subcategory": "mathematics",
        "difficulty": 4,
        "estimated_hours": 25,
        "default_mastery": 0.0,
        "default_confidence": 0.0
    },
    {
        "skill_id": "ai.optimization",
        "name": "Optimization",
        "description": "Gradient descent, convex optimization, and numerical methods",
        "category": "ai",
        "subcategory": "mathematics",
        "difficulty": 5,
        "estimated_hours": 25,
        "default_mastery": 0.0,
        "default_confidence": 0.0
    },
    
    # AI & Robotics
    {
        "skill_id": "ai.machine_learning",
        "name": "Machine Learning Fundamentals",
        "description": "Supervised/unsupervised learning, model evaluation, and overfitting",
        "category": "ai",
        "subcategory": "ml",
        "difficulty": 4,
        "estimated_hours": 30,
        "default_mastery": 0.0,
        "default_confidence": 0.0
    },
    {
        "skill_id": "ai.neural_networks",
        "name": "Neural Networks",
        "description": "Perceptrons, feedforward networks, backpropagation, and deep learning basics",
        "category": "ai",
        "subcategory": "ml",
        "difficulty": 5,
        "estimated_hours": 35,
        "default_mastery": 0.0,
        "default_confidence": 0.0
    },
    {
        "skill_id": "robotics.control",
        "name": "Control Systems",
        "description": "Feedback control, PID controllers, and system stability",
        "category": "robotics",
        "subcategory": "control",
        "difficulty": 5,
        "estimated_hours": 30,
        "default_mastery": 0.0,
        "default_confidence": 0.0
    },
    {
        "skill_id": "robotics.sensor_fusion",
        "name": "Sensor Fusion",
        "description": "Combining data from multiple sensors for improved accuracy",
        "category": "robotics",
        "subcategory": "perception",
        "difficulty": 5,
        "estimated_hours": 25,
        "default_mastery": 0.0,
        "default_confidence": 0.0
    },
    
    # Capstone Project
    {
        "skill_id": "project.capstone",
        "name": "Capstone Project: AI-Powered Robotic System",
        "description": "Integrate sensors, microcontrollers, AI models, and control systems",
        "category": "project",
        "subcategory": "capstone",
        "difficulty": 6,
        "estimated_hours": 50,
        "default_mastery": 0.0,
        "default_confidence": 0.0
    }
]

# Prerequisite relationships
PREREQUISITES = [
    # Math prerequisites
    ("math.basic_algebra", "math.arithmetic"),
    ("math.functions", "math.basic_algebra"),
    ("math.vectors", "math.basic_algebra"),
    ("math.linear_algebra", "math.vectors"),
    
    # Programming prerequisites
    ("programming.data_structures", "programming.python_basics"),
    ("programming.algorithms", "programming.data_structures"),
    
    # Electronics prerequisites
    ("electronics.basic_circuits", "electronics.ohms_law"),
    ("electronics.digital_logic", "electronics.basic_circuits"),
    ("electronics.semiconductors", "electronics.basic_circuits"),
    
    # Embedded prerequisites
    ("embedded.microcontrollers", "electronics.digital_logic"),
    ("embedded.microcontrollers", "programming.python_basics"),
    ("embedded.sensors", "embedded.microcontrollers"),
    ("embedded.rtos", "embedded.microcontrollers"),
    
    # AI Math prerequisites
    ("ai.probability", "math.linear_algebra"),
    ("ai.statistics", "ai.probability"),
    ("ai.optimization", "math.linear_algebra"),
    
    # AI/ML prerequisites
    ("ai.machine_learning", "ai.statistics"),
    ("ai.machine_learning", "ai.linear_algebra"),  # Will need to add linear algebra to AI section
    ("ai.neural_networks", "ai.machine_learning"),
    ("ai.neural_networks", "ai.optimization"),
    
    # Robotics prerequisites
    ("robotics.control", "math.linear_algebra"),
    ("robotics.control", "physics.mechanics"),  # Will need to add physics mechanics
    ("robotics.sensor_fusion", "ai.probability"),
    ("robotics.sensor_fusion", "embedded.sensors"),
    
    # Capstone prerequisites
    ("project.capstone", "embedded.microcontrollers"),
    ("project.capstone", "embedded.sensors"),
    ("project.capstone", "ai.neural_networks"),
    ("project.capstone", "robotics.control"),
    ("project.capstone", "robotics.sensor_fusion"),
]

async def init_db():
    """Initialize database with sample data."""
    # Initialize database (creates tables and pgvector extension)
    await db_init_db()
    
    # Create engine for session
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Check if skills already exist
        result = await session.execute(select(Skill).limit(1))
        existing_skill = result.scalar_one_or_none()
        
        if existing_skill:
            print("Database already contains data. Skipping initialization.")
            await engine.dispose()
            return
        
        # Create skills
        skill_map = {}  # skill_id -> Skill object
        
        for skill_data in SAMPLE_SKILLS:
            skill = Skill(**skill_data)
            session.add(skill)
            await session.flush()  # Get the ID
            skill_map[skill_data["skill_id"]] = skill
            print(f"Created skill: {skill_data['name']}")
        
        # Refresh all skills to load relationships
        for skill in skill_map.values():
            await session.refresh(skill, ["prerequisites"])
        
        # Create prerequisite relationships
        for skill_id, prereq_id in PREREQUISITES:
            if skill_id in skill_map and prereq_id in skill_map:
                skill = skill_map[skill_id]
                prereq = skill_map[prereq_id]
                skill.prerequisites.append(prereq)
                print(f"Added prerequisite: {prereq.name} -> {skill.name}")
        
        # Commit all changes
        await session.commit()
        print(f"Successfully initialized database with {len(SAMPLE_SKILLS)} skills")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_db())