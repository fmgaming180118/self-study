# Self Study OS

A Personal Learning Operating System designed to help you become an autodidact and multidisciplinary systems engineer through structured, mastery-based self-study.

## Overview

This system combines:
- An adaptive curriculum based on a knowledge graph of skills and prerequisites
- An AI tutor that generates personalized lessons, assessments, and projects
- Simulation laboratories for hands-on practice in electronics, physics, coding, and robotics
- Research ingestion from arXiv and OpenAlex to keep content up-to-date
- Knowledge tracking with spaced repetition and mastery-based progression
- Project-based learning to build real-world artifacts

## Architecture

### Backend (Python/FastAPI)
- **Database**: PostgreSQL with pgvector for semantic search
- **Services**:
  - Skill Graph: Manages the knowledge graph of skills and prerequisites
  - Knowledge Tracing: Tracks user mastery and confidence levels
  - Tutor Orchestrator: Main coordinator for learning activities
  - Simulation Lab: Manages various types of simulations (circuit, physics, math, coding, robotics)
  - Research Ingestion: Fetches and processes papers from arXiv and OpenAlex
- **API**: RESTful API for all functionality

### Frontend (React/Next.js)
- **Skill Map**: Interactive visualization of the knowledge graph
- **Progress Dashboard**: Tracks mastery, confidence, and learning streaks
- **Tutor Panel**: Contextual interface for lessons, resources, simulations, assessments, and projects
- **Responsive Design**: Works on desktop and tablet

## Features

### Knowledge Graph
- Skills organized by domain (math, physics, electronics, programming, AI, robotics)
- Prerequisite relationships ensure proper learning sequence
- Skill metadata includes difficulty, estimated time, and category

### Learning System
- Diagnostic assessments to determine starting point
- Personalized lessons following a 10-step learning cycle
- Mastery-based progression (Not Started → Understanding → Guided Practice → Independent → Project Proven)
- Spaced repetition for long-term retention
- Evidence-based assessment (quizzes, projects, simulations)

### Simulation Laboratory
- Circuit simulations (using ngspice)
- Physics simulations (mechanics, electromagnetics)
- Math visualizations (2D/3D functions, vector fields, complex functions)
- Code execution sandbox (Dockerized, language-agnostic)
- Robotics simulations (kinematics, path planning, dynamics)

### Research Integration
- Automatic ingestion of recent papers from arXiv
- Mapping of research to skills in the knowledge graph
- Resource creation from peer-reviewed papers
- Optional Consensus API integration for filtered research

### Project-Based Learning
- Milestone projects for each major skill area
- Capstone integrated project combining multiple domains
- Artifact collection (code, schematics, reports, models)
- Peer and self-assessment capabilities

## Getting Started

### Prerequisites
- Docker Engine and Docker Compose (Docker Desktop is not required)
- Git
- (Optional) API keys for enhanced features:
  - OpenAI API Key (for LLM-powered features)
  - Anthropic API Key (alternative LLM)
  - OpenAlex API Key (for enhanced research data)
  - Consensus API Key (for research filtering)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd self-study-os
   ```

2. Optionally create a project-level `.env` file for external API keys. The core application works without them:
   ```bash
   cp .env.example .env
   # Edit .env to add your API keys
   ```

3. Navigate to the project directory:
   ```bash
   cd self-study-os
   ```

4. Start the production containers:
   ```bash
   docker compose up --build
   ```

   To run in the background while still watching the logs:
   ```bash
   docker compose up -d --build
   docker compose logs -f
   ```

5. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

6. Stop the stack:
   ```bash
   docker compose down
   ```

The PostgreSQL data is stored in the `postgres_data` Docker volume and is preserved by `docker compose down`.

### Development

To run the frontend and backend separately for development:

#### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Learning Path (MVP)

The initial version focuses on a core pathway:
1. **Mathematical Foundations** → Algebra, Functions, Vectors, Linear Algebra
2. **Programming Fundamentals** → Python, Data Structures, Algorithms
3. **Electronics & Computer Systems** → Circuit Theory, Digital Logic, Computer Architecture
4. **Embedded Systems** → Microcontrollers, Sensors, Real-Time Systems
5. **AI Mathematics** → Linear Algebra, Calculus, Probability, Optimization
6. **AI & Robotics** → Machine Learning, Computer Vision, Control Systems
7. **Integrated Project** → AI-powered robotic sensor system

Each milestone includes:
- Conceptual lessons
- Interactive simulations
- Practice assessments
- Hands-on projects
- Research connections

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Inspired by autodidactic mastery and modern systems engineering principles
- Based on research in Intelligent Tutoring Systems and Knowledge Tracing
- Built with modern web technologies and AI/ML techniques
