export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface Skill {
  id: string;
  skill_id: string;
  name: string;
  description: string | null;
  category: string;
  subcategory: string | null;
  difficulty: number;
  estimated_hours: number;
  default_mastery: number;
  default_confidence: number;
  prerequisites: Skill[];
  dependents: Skill[];
  created_at: string;
  updated_at: string | null;
}

export interface MasteryRecord {
  skill_id: string;
  skill_name: string;
  mastery: number;
  confidence: number;
  level: MasteryLevel;
  evidence_count: number;
  last_review: string | null;
  next_review: string | null;
  review_count: number;
}

export type MasteryLevel = 
  | 'not_started'
  | 'understanding'
  | 'guided_practice'
  | 'independent'
  | 'project_proven';

export interface LearningResource {
  id: string;
  skill_id: string;
  title: string;
  description: string | null;
  url: string | null;
  resource_type: string;
  level: ResourceLevel;
  source: string;
  source_id: string | null;
  authors: string[] | null;
  published_date: string | null;
  quality_score: number;
  difficulty: number;
  estimated_minutes: number;
  tags: string[] | null;
  created_at: string;
  updated_at: string | null;
}

export type ResourceLevel = 
  | 'level_1_basic'
  | 'level_2_tutorial'
  | 'level_3_university'
  | 'level_4_review'
  | 'level_5_peer_reviewed'
  | 'level_6_preprint';

export interface LearningSession {
  id: string;
  user_id: string;
  skill_id: string;
  session_type: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  duration_minutes: number;
  mastery_before: number;
  mastery_after: number;
  confidence_before: number;
  confidence_after: number;
  notes: string | null;
  metadata: Record<string, any>;
}

export interface Assessment {
  id: string;
  skill_id: string;
  title: string;
  description: string | null;
  assessment_type: string;
  questions: AssessmentQuestion[];
  passing_score: number;
  time_limit_minutes: number;
  difficulty: number;
  created_at: string;
  updated_at: string | null;
}

export interface AssessmentQuestion {
  id: string;
  type: 'multiple_choice' | 'true_false' | 'short_answer' | 'explanation' | 'problem_solving' | 'project_rubric';
  difficulty: number;
  question: string;
  options?: string[];
  correct_answer?: string;
  points: number;
  skill_concepts: string[];
}

export interface AssessmentAttempt {
  id: string;
  user_id: string;
  assessment_id: string;
  skill_id: string;
  answers: AssessmentAnswer[];
  score: number;
  passed: boolean;
  feedback: string | null;
  mastery_delta: number;
  started_at: string;
  completed_at: string | null;
  duration_minutes: number;
  metadata: Record<string, any>;
}

export interface AssessmentAnswer {
  question_id: string;
  answer: any;
  correct: boolean;
  partial_credit: number;
  feedback: string;
  timestamp: string;
}

export interface Project {
  id: string;
  user_id: string;
  skill_id: string;
  title: string;
  description: string | null;
  project_type: string;
  status: string;
  requirements: any[];
  deliverables: any[];
  actual_deliverables: any[];
  grade: string | null;
  feedback: string | null;
  mastery_evidence: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface ProjectArtifact {
  id: string;
  project_id: string;
  name: string;
  artifact_type: string;
  content: string | null;
  file_path: string | null;
  url: string | null;
  metadata: Record<string, any>;
  created_at: string;
}

export interface Simulation {
  id: string;
  skill_id: string;
  name: string;
  description: string | null;
  simulation_type: string;
  engine: string;
  config: Record<string, any>;
  scenario_template: Record<string, any>;
  difficulty: number;
  estimated_minutes: number;
  learning_objectives: string[];
  assessment_criteria: Record<string, any>;
  created_at: string;
  updated_at: string | null;
}

export interface SimulationResult {
  success: boolean;
  type: string;
  data?: any;
  error?: string;
  measurements?: any;
  trajectory?: any[];
}

export interface ReviewQueue {
  id: string;
  user_id: string;
  skill_id: string;
  mastery_record_id: string;
  scheduled_for: string;
  priority: number;
  review_type: string;
  status: string;
  completed_at: string | null;
  metadata: Record<string, any>;
  created_at: string;
}

export interface ResearchPaper {
  id: string;
  arxiv_id: string;
  title: string;
  abstract: string | null;
  authors: string[];
  categories: string[];
  primary_category: string | null;
  published_date: string | null;
  updated_date: string | null;
  pdf_url: string | null;
  doi: string | null;
  journal_ref: string | null;
  comment: string | null;
  created_at: string;
}

export interface PaperSkillMapping {
  id: string;
  paper_id: string;
  skill_id: string;
  relevance_score: number;
  mapping_type: string;
  created_at: string;
}

export interface NextSkillRecommendation {
  skill: Skill;
  prerequisites_met: boolean;
  unmet_prerequisites: Skill[];
  current_mastery: number;
  current_level: MasteryLevel;
  recommendation_reason: string;
}

export interface LearningPathStep {
  skill: Skill;
  mastery: number;
  level: MasteryLevel;
  prerequisites_met: boolean;
}

export interface LessonPlan {
  skill_id: string;
  skill_name: string;
  current_mastery: number;
  target_mastery: number;
  start_step: number;
  steps: LessonStep[];
  estimated_total_minutes: number;
}

export interface LessonStep {
  step: number;
  name: string;
  description: string;
  type: string;
  required: boolean;
}

export interface ProgressSummary {
  total_skills: number;
  by_level: Record<MasteryLevel, number>;
  average_mastery: number;
  average_confidence: number;
  skills_needing_review: number;
  total_evidence_count: number;
}
