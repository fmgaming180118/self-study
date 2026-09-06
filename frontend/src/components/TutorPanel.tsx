'use client';

import React, { useState, useEffect } from 'react';
import { 
  Play, 
  RefreshCw, 
  Search, 
  BookOpen, 
  Zap, 
  Cpu, 
  Brain, 
  Code, 
  FlaskConical, 
  Settings,
  TrendingUp,
  CheckCircle2,
  AlertTriangle,
  List,
  Target,
  Layers,
  ChevronRight,
  X,
  Menu,
  Clock,
  Upload,
  FileText,
} from 'lucide-react';
import { Skill, MasteryRecord, User } from '@/types';
import { cn } from '@/lib/utils';

interface TutorPanelProps {
  skill: Skill;
  mastery: MasteryRecord;
  onClose: () => void;
}

const categoryIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  math: BookOpen,
  physics: Zap,
  electronics: Cpu,
  programming: Code,
  ai: Brain,
  robotics: FlaskConical,
  mechanical: Settings,
  default: Layers,
};

const levelColors: Record<MasteryRecord['level'], string> = {
  not_started: 'bg-dark-300 dark:bg-dark-600',
  understanding: 'bg-blue-500',
  guided_practice: 'bg-yellow-500',
  independent: 'bg-green-500',
  project_proven: 'bg-purple-500',
};

const levelLabels: Record<MasteryRecord['level'], string> = {
  not_started: 'Not Started',
  understanding: 'Understanding',
  guided_practice: 'Guided Practice',
  independent: 'Independent',
  project_proven: 'Project Proven',
};

export const TutorPanel = ({ skill, mastery, onClose }: TutorPanelProps) => {
  const CategoryIcon = categoryIcons[skill.category] || categoryIcons.default;
  const [activeTab, setActiveTab] = useState<'overview' | 'lesson' | 'resources' | 'simulation' | 'assessment' | 'project'>('overview');
  const [loading, setLoading] = useState(false);
  const [lessonData, setLessonData] = useState<any>(null);
  const [resources, setResources] = useState<any[]>([]);
  const [simulations, setSimulations] = useState<any[]>([]);
  const [assessment, setAssessment] = useState<any>(null);
  const [project, setProject] = useState<any>(null);

  useEffect(() => {
    fetchTutorData();
  }, [skill.skill_id]);

  const fetchTutorData = async () => {
    setLoading(true);
    try {
      // Fetch lesson data
      const lessonRes = await fetch(`/api/backend/tutor/lesson?skill_id=${skill.skill_id}`, {
        method: 'POST',
      });
      if (lessonRes.ok) {
        setLessonData(await lessonRes.json());
      }
      
      // Fetch resources
      const resourcesRes = await fetch(`/api/backend/tutor/resources/${skill.skill_id}?limit=10`);
      if (resourcesRes.ok) {
        setResources(await resourcesRes.json());
      }
      
      // Fetch simulations
      const simRes = await fetch(`/api/backend/simulations/${skill.skill_id}`);
      if (simRes.ok) {
        setSimulations(await simRes.json());
      }
      
      // Fetch assessment
      const assessRes = await fetch('/api/backend/tutor/assessment', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skill_id: skill.skill_id, num_questions: 5 }),
      });
      if (assessRes.ok) {
        setAssessment(await assessRes.json());
      }
    } catch (error) {
      console.error('Failed to fetch tutor data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getMasteryPercent = () => Math.round(mastery.mastery * 100);
  const getConfidencePercent = () => Math.round(mastery.confidence * 100);

  const startLesson = async () => {
    // In a real implementation, this would navigate to a lesson view
    alert('Starting lesson...');
  };

  const startSimulation = async (simId: string) => {
    alert(`Starting simulation: ${simId}`);
  };

  const takeAssessment = async () => {
    alert('Starting assessment...');
  };

  const startProject = async () => {
    alert('Starting project...');
  };

  return (
    <aside className="w-96 border-l border-dark-200 dark:border-dark-700 bg-white dark:bg-dark-900 overflow-auto">
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-dark-200 dark:border-dark-700">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg flex items-center justify-center">
              <CategoryIcon className="w-5 h-5 text-primary-600" />
            </div>
            <div>
              <h2 className="font-semibold text-dark-900 dark:text-dark-100">{skill.name}</h2>
              <p className="text-xs text-dark-500 dark:text-dark-400 font-mono">{skill.skill_id}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded hover:bg-dark-100 dark:hover:bg-dark-800">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex-1 overflow-hidden">
          <div className="flex border-b border-dark-200 dark:border-dark-700">
            {[['overview', 'Overview'], ['lesson', 'Lesson'], ['resources', 'Resources'], ['simulation', 'Simulation'], ['assessment', 'Assessment'], ['project', 'Project']].map(([tabId, tabLabel]) => (
              <button
                key={tabId}
                onClick={() => setActiveTab(tabId as any)}
                className={cn(
                  'flex-1 px-4 py-3 text-sm font-medium transition-all duration-200',
                  activeTab === tabId ? 'bg-primary-600 text-white' : 'bg-transparent text-dark-600 dark:text-dark-400 hover:bg-dark-50 dark:hover:bg-dark-800 hover:text-white'
                )}
              >
                {tabLabel}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="flex-1 p-4 overflow-auto">
            {activeTab === 'overview' && (
              <OverviewTab skill={skill} mastery={mastery} />
            )}
            
            {activeTab === 'lesson' && (
              <LessonTab 
                skill={skill} 
                mastery={mastery} 
                lessonData={lessonData} 
                loading={loading}
                onStartLesson={startLesson}
              />
            )}
            
            {activeTab === 'resources' && (
              <ResourcesTab 
                skill={skill} 
                resources={resources} 
                loading={loading}
              />
            )}
            
            {activeTab === 'simulation' && (
              <SimulationTab 
                skill={skill} 
                simulations={simulations} 
                loading={loading}
                onStartSimulation={startSimulation}
              />
            )}
            
            {activeTab === 'assessment' && (
              <AssessmentTab 
                skill={skill} 
                assessment={assessment} 
                loading={loading}
                onTakeAssessment={takeAssessment}
              />
            )}
            
            {activeTab === 'project' && (
              <ProjectTab 
                skill={skill} 
                project={project} 
                loading={loading}
                onStartProject={startProject}
              />
            )}
          </div>
        </div>

        {/* Action Bar */}
        <div className="px-4 py-3 border-t border-dark-200 dark:border-dark-700 bg-dark-50 dark:bg-dark-800">
          <div className="flex items-center justify-between space-x-3">
            <div className="flex items-center space-x-2">
              <div className="w-6 h-6 rounded-full flex items-center justify-center">
                {levelColors[mastery.level]}
              </div>
              <span className="text-sm font-medium text-dark-900 dark:text-dark-100 capitalize">
                {mastery.level.replace('_', ' ')}
              </span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-6 h-6 rounded-full flex items-center justify-center bg-primary-600">
                <TrendingUp className="w-3 h-3 text-white" />
              </div>
              <span className="text-sm font-medium text-dark-900 dark:text-dark-100">
                {getMasteryPercent()}% mastery
              </span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};

const OverviewTab = ({ skill, mastery }: { skill: Skill; mastery: MasteryRecord }) => {
  const getMasteryPercent = () => Math.round(mastery.mastery * 100);
  const getConfidencePercent = () => Math.round(mastery.confidence * 100);

  return (
    <div className="space-y-4">
      {/* Skill Info */}
      <div className="p-3 bg-dark-50 dark:bg-dark-800 rounded-lg">
        <h3 className="font-medium text-dark-900 dark:text-dark-100 mb-2">Skill Information</h3>
        <div className="space-y-2">
          <div className="flex items-center space-x-3 text-sm">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center">
              <Brain className="w-4 h-4 text-primary-600" />
            </div>
            <div>
              <p className="font-medium">Category</p>
              <p className="text-dark-500 dark:text-dark-400">{skill.category}</p>
            </div>
          </div>
          <div className="flex items-center space-x-3 text-sm">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center">
              <Target className="w-4 h-4 text-primary-600" />
            </div>
            <div>
              <p className="font-medium">Difficulty</p>
              <p className="text-dark-500 dark:text-dark-400">{skill.difficulty}/10</p>
            </div>
          </div>
          <div className="flex items-center space-x-3 text-sm">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center">
              <Clock className="w-4 h-4 text-primary-600" />
            </div>
            <div>
              <p className="font-medium">Est. Time</p>
              <p className="text-dark-500 dark:text-dark-400">{skill.estimated_hours} hours</p>
            </div>
          </div>
        </div>
      </div>

      {/* Mastery Progress */}
      <div className="p-3 bg-dark-50 dark:bg-dark-800 rounded-lg">
        <h3 className="font-medium text-dark-900 dark:text-dark-100 mb-2">Mastery Progress</h3>
        <div className="space-y-3">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4 text-primary-600" />
            </div>
            <div>
              <p className="font-medium">Current Mastery</p>
              <p className="text-2xl font-bold text-dark-900 dark:text-dark-100">
                {getMasteryPercent()}%
              </p>
            </div>
          </div>
          <div className="w-full h-2 bg-dark-200 dark:bg-dark-700 rounded-full overflow-hidden">
            <div
              className={cn('h-full rounded-full transition-all duration-500', levelColors[mastery.level])}
              style={{ width: `${getMasteryPercent()}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-dark-500 dark:text-dark-400 mt-1">
            <span>{levelLabels[mastery.level]}</span>
            <span>{mastery.evidence_count} evidence items</span>
          </div>
        </div>
      </div>

      {/* Confidence */}
      <div className="p-3 bg-dark-50 dark:bg-dark-800 rounded-lg">
        <h3 className="font-medium text-dark-900 dark:text-dark-100 mb-2">Confidence Level</h3>
        <div className="space-y-2">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center">
              <Zap className="w-4 h-4 text-primary-600" />
            </div>
            <div>
              <p className="font-medium">Confidence</p>
              <p className="text-2xl font-bold text-dark-900 dark:text-dark-100">
                {getConfidencePercent()}%
              </p>
            </div>
          </div>
          <div className="w-full h-2 bg-dark-200 dark:bg-dark-700 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full bg-primary-500 transition-all duration-500"
              style={{ width: `${getConfidencePercent()}%` }}
            />
          </div>
        </div>
      </div>

      {/* Prerequisites */}
      {skill.prerequisites && skill.prerequisites.length > 0 && (
        <div className="p-3 bg-dark-50 dark:bg-dark-800 rounded-lg">
          <h3 className="font-medium text-dark-900 dark:text-dark-100 mb-2">Prerequisites ({skill.prerequisites.length})</h3>
          <div className="space-y-2">
            {skill.prerequisites.map(prereq => {
              const PrerequisiteIcon = categoryIcons[prereq.category] || categoryIcons.default;
              return (
                <div key={prereq.id} className="flex items-center space-x-3 p-2 bg-dark-50 dark:bg-dark-800 rounded">
                  <div className="w-6 h-6 rounded-full flex items-center justify-center">
                    <PrerequisiteIcon className="w-3 h-3 text-primary-600" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-dark-900 dark:text-dark-100">{prereq.name}</p>
                    <p className="text-xs text-dark-500 dark:text-dark-400 font-mono">{prereq.skill_id}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Next Skills Preview */}
      <div className="p-3 bg-dark-50 dark:bg-dark-800 rounded-lg">
        <h3 className="font-medium text-dark-900 dark:text-dark-100 mb-2">Recommended Next</h3>
        <div className="space-y-2">
          {/* This would come from API in real implementation */}
          <div className="p-2 bg-dark-50 dark:bg-dark-800 rounded-lg">
            <div className="flex items-center space-x-3">
              <div className="w-6 h-6 rounded-full flex items-center justify-center bg-green-500">
                <Play className="w-3 h-3 text-white" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-dark-900 dark:text-dark-100">Vector Calculus</p>
                <p className="text-xs text-dark-500 dark:text-dark-400 font-mono">math.vector_calculus</p>
              </div>
            </div>
          </div>
          <div className="p-2 bg-dark-50 dark:bg-dark-800 rounded-lg">
            <div className="flex items-center space-x-3">
              <div className="w-6 h-6 rounded-full flex items-center justify-center bg-blue-500">
                <Code className="w-3 h-3 text-white" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-dark-900 dark:text-dark-100">Python Basics</p>
                <p className="text-xs text-dark-500 dark:text-dark-400 font-mono">programming.python_basics</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const LessonTab = ({ 
  skill, 
  mastery, 
  lessonData, 
  loading, 
  onStartLesson 
}: { 
  skill: Skill; 
  mastery: MasteryRecord; 
  lessonData: any; 
  loading: boolean; 
  onStartLesson: () => void 
}) => {
  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-4 border-primary-600 border-t-transparent mx-auto mb-4"></div>
        <p className="text-dark-500 dark:text-dark-400">Loading lesson...</p>
      </div>
    );
  }

  if (!lessonData) {
    return (
      <div className="text-center py-8">
        <p className="text-dark-500 dark:text-dark-400">No lesson data available</p>
        <button 
          onClick={onStartLesson} 
          className="btn-primary mt-4 px-4 py-2"
        >
          Generate Lesson
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Lesson Info */}
      <div className="p-3 bg-dark-50 dark:bg-dark-800 rounded-lg">
        <h3 className="font-medium text-dark-900 dark:text-dark-100 mb-2">Lesson Plan</h3>
        <div className="space-y-2">
          <div className="flex items-center space-x-3 text-sm">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center">
              <BookOpen className="w-4 h-4 text-primary-600" />
            </div>
            <div>
              <p className="font-medium">Skill</p>
              <p className="text-dark-500 dark:text-dark-400">{skill.name}</p>
            </div>
          </div>
          <div className="flex items-center space-x-3 text-sm">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-4 h-4 text-primary-600" />
            </div>
            <div>
              <p className="font-medium">Target Mastery</p>
              <p className="text-dark-500 dark:text-dark-400">
                {Math.round(lessonData.target_mastery * 100)}%
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-3 text-sm">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center">
              <Clock className="w-4 h-4 text-primary-600" />
            </div>
            <div>
              <p className="font-medium">Est. Time</p>
              <p className="text-dark-500 dark:text-dark-400">
                {Math.ceil(lessonData.estimated_total_minutes / 60)} hours
                {lessonData.estimated_total_minutes % 60 !== 0 && (
                  <span className="ml-1 text-xs">{lessonData.estimated_total_minutes % 60} min</span>
                )}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Lesson Steps */}
      <div className="p-3 bg-dark-50 dark:bg-dark-800 rounded-lg">
        <h3 className="font-medium text-dark-900 dark:text-dark-100 mb-2">Learning Steps</h3>
        <div className="space-y-2">
          {lessonData.steps.map((step: any, index: number) => (
            <div key={index} className="p-3 bg-dark-50 dark:bg-dark-800 rounded-lg border-l-2">
              <div className="flex items-start space-x-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center">
                  <div className="text-xs font-medium text-white bg-primary-600 rounded-full flex items-center justify-center">
                    {step.step}
                  </div>
                </div>
                <div className="flex-1 space-y-1">
                  <p className="font-medium text-dark-900 dark:text-dark-100">{step.name}</p>
                  <p className="text-sm text-dark-500 dark:text-dark-400">{step.description}</p>
                  {step.required && (
                    <span className="px-2 py-0.5 bg-primary-500/20 text-primary-600 text-xs rounded">
                      Required
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Start Lesson Button */}
      <div className="pt-4">
        <button 
          onClick={onStartLesson} 
          className="w-full btn-primary px-4 py-3"
        >
          Start Lesson
        </button>
      </div>
    </div>
  );
};

const ResourcesTab = ({ 
  skill, 
  resources, 
  loading 
}: { 
  skill: Skill; 
  resources: any[]; 
  loading: boolean 
}) => {
  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-4 border-primary-600 border-t-transparent mx-auto mb-4"></div>
        <p className="text-dark-500 dark:text-dark-400">Loading resources...</p>
      </div>
    );
  }

  if (resources.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-dark-500 dark:text-dark-400">No resources available</p>
        <p className="text-sm text-dark-500 dark:text-dark-400 mt-2">
          Try searching for resources or check back later
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="p-3 bg-dark-50 dark:bg-dark-800 rounded-lg">
        <h3 className="font-medium text-dark-900 dark:text-dark-100 mb-2">Learning Resources</h3>
        <div className="space-y-3">
          {resources.map((resource: any, index: number) => (
            <div key={index} className="p-3 bg-dark-50 dark:bg-dark-800 rounded-lg border-l-2">
              <div className="flex items-start space-x-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center">
                  <div className="text-xs font-medium text-white bg-primary-600 rounded-full flex items-center justify-center">
                    {index + 1}
                  </div>
                </div>
                <div className="flex-1 space-y-1">
                  <p className="font-medium text-dark-900 dark:text-dark-100">{resource.title}</p>
                  <div className="flex items-center space-x-2 text-sm mt-1">
                    <div className="w-6 h-6 rounded-full flex items-center justify-center">
                      {resource.resource_type === 'video' && (
                        <Play className="w-3 h-3 text-white" />
                      )}
                      {resource.resource_type === 'article' && (
                        <BookOpen className="w-3 h-3 text-white" />
                      )}
                      {resource.resource_type === 'paper' && (
                        <FileText className="w-3 h-3 text-white" />
                      )}
                      {resource.resource_type === 'tutorial' && (
                        <Code className="w-3 h-3 text-white" />
                      )}
                      {resource.resource_type === 'simulation' && (
                        <Zap className="w-3 h-3 text-white" />
                      )}
                    </div>
                    <div className="flex-1">
                      <p className="text-xs text-dark-500 dark:text-dark-400">
                        {resource.resource_type} • {resource.level?.replace('_', ' ').toUpperCase()}
                      </p>
                    </div>
                  </div>
                  <p className="text-sm text-dark-500 dark:text-dark-400 line-clamp-2">
                    {resource.description}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {resource.tags?.slice(0, 3).map((tag: string) => (
                      <span key={tag} className="px-2 py-0.5 bg-dark-200 dark:bg-dark-700 rounded text-xs">
                        #{tag}
                      </span>
                    ))}
                  </div>
                  <div className="mt-2 flex items-center space-x-2 text-xs">
                    <span className="mr-2">Quality:</span>
                    <div className="w-12 h-1 bg-dark-200 dark:bg-dark-700 rounded overflow-hidden">
                      <div
                        className="h-full bg-primary-500"
                        style={{ width: `${resource.quality_score * 100}%` }}
                      />
                    </div>
                    <span className="ml-2">{Math.round(resource.quality_score * 100)}%</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const SimulationTab = ({ 
  skill, 
  simulations, 
  loading, 
  onStartSimulation 
}: { 
  skill: Skill; 
  simulations: any[]; 
  loading: boolean; 
  onStartSimulation: (simId: string) => void 
}) => {
  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-4 border-primary-600 border-t-transparent mx-auto mb-4"></div>
        <p className="text-dark-500 dark:text-dark-400">Loading simulations...</p>
      </div>
    );
  }

  if (simulations.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-dark-500 dark:text-dark-400">No simulations available</p>
        <p className="text-sm text-dark-500 dark:text-dark-400 mt-2">
          Simulations coming soon for this skill
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="p-3 bg-dark-50 dark:bg-dark-800 rounded-lg">
        <h3 className="font-medium text-dark-900 dark:text-dark-100 mb-2">Available Simulations</h3>
        <div className="space-y-3">
          {simulations.map((sim: any, index: number) => (
            <div key={index} className="p-3 bg-dark-50 dark:bg-dark-800 rounded-lg border-l-2">
              <div className="flex items-start space-x-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center">
                  <div className="text-xs font-medium text-white bg-primary-600 rounded-full flex items-center justify-center">
                    {index + 1}
                  </div>
                </div>
                <div className="flex-1 space-y-1">
                  <p className="font-medium text-dark-900 dark:text-dark-100">{sim.name}</p>
                  <p className="text-sm text-dark-500 dark:text-dark-400">{sim.description}</p>
                  <div className="mt-2 flex items-center space-x-2">
                    <div className="w-6 h-6 rounded-full flex items-center justify-center">
                      {sim.simulation_type === 'circuit' && (
                        <Zap className="w-3 h-3 text-white" />
                      )}
                      {sim.simulation_type === 'physics' && (
                        <FlaskConical className="w-3 h-3 text-white" />
                      )}
                      {sim.simulation_type === 'math' && (
                        <Brain className="w-3 h-3 text-white" />
                      )}
                      {sim.simulation_type === 'coding' && (
                        <Code className="w-3 h-3 text-white" />
                      )}
                      {sim.simulation_type === 'robotics' && (
                        <Settings className="w-3 h-3 text-white" />
                      )}
                    </div>
                    <div className="flex-1">
                      <p className="text-xs text-dark-500 dark:text-dark-400">
                        {sim.simulation_type} • Difficulty: {sim.difficulty}/10
                      </p>
                    </div>
                  </div>
                  <div className="mt-2 flex justify-between">
                    <button 
                      onClick={() => onStartSimulation(sim.id)} 
                      className="btn-secondary px-3 py-1 text-sm"
                    >
                      <Play className="w-3 h-3 mr-1" />
                      Start
                    </button>
                    <span className="text-xs text-dark-500 dark:text-dark-400">
                      {sim.estimated_minutes} min
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const AssessmentTab = ({ 
  skill, 
  assessment, 
  loading, 
  onTakeAssessment 
}: { 
  skill: Skill; 
  assessment: any; 
  loading: boolean; 
  onTakeAssessment: () => void 
}) => {
  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-4 border-primary-600 border-t-transparent mx-auto mb-4"></div>
        <p className="text-dark-500 dark:text-dark-400">Loading assessment...</p>
      </div>
    );
  }

  if (!assessment) {
    return (
      <div className="text-center py-8">
        <p className="text-dark-500 dark:text-dark-400">No assessment available</p>
        <button 
          onClick={onTakeAssessment} 
          className="btn-primary mt-4 px-4 py-2"
        >
          Generate Assessment
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="p-3 bg-dark-50 dark:bg-dark-800 rounded-lg">
        <h3 className="font-medium text-dark-900 dark:text-dark-100 mb-2">Assessment Overview</h3>
        <div className="space-y-2">
          <div className="flex items-center space-x-3 text-sm">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center">
              <List className="w-4 h-4 text-primary-600" />
            </div>
            <div>
              <p className="font-medium text-dark-900 dark:text-dark-100">Questions</p>
              <p className="text-dark-500 dark:text-dark-400">{assessment.num_questions}</p>
            </div>
          </div>
          <div className="flex items-center space-x-3 text-sm">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-4 h-4 text-primary-600" />
            </div>
            <div>
              <p className="font-medium">Passing Score</p>
              <p className="text-dark-500 dark:text-dark-400">
                {Math.round(assessment.passing_score * 100)}%
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-3 text-sm">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center">
              <Clock className="w-4 h-4 text-primary-600" />
            </div>
            <div>
              <p className="font-medium">Time Limit</p>
              <p className="text-dark-500 dark:text-dark-400">
                {assessment.time_limit_minutes} min
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Assessment Questions Preview */}
      <div className="p-3 bg-dark-50 dark:bg-dark-800 rounded-lg">
        <h3 className="font-medium text-dark-900 dark:text-dark-100 mb-2">Sample Questions</h3>
        <div className="space-y-2">
          {assessment.questions?.slice(0, 3).map((q: any, index: number) => (
            <div key={index} className="p-3 bg-dark-50 dark:bg-dark-800 rounded-lg border-l-2">
              <div className="flex items-start space-x-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center">
                  <div className="text-xs font-medium text-white bg-primary-600 rounded-full flex items-center justify-center">
                    Q{index + 1}
                  </div>
                </div>
                <div className="flex-1 space-y-1">
                  <p className="font-medium text-dark-900 dark:text-dark-100">{q.question}</p>
                  {q.options && q.options.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {q.options.map((opt: string, optIndex: number) => (
                        <div key={optIndex} className="flex items-center space-x-2 p-1 bg-dark-50 dark:bg-dark-800 rounded">
                          <input 
                            type="radio" 
                            name={`q${index}`} 
                            value={opt} 
                            className="w-4 h-4 text-primary-600" 
                          />
                          <span className="text-sm text-dark-900 dark:text-dark-100">{opt}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {q.type === 'explanation' && (
                    <div className="mt-2">
                      <p className="text-xs text-dark-500 dark:text-dark-400 italic">
                        (Explain your answer in your own words)
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Take Assessment Button */}
      <div className="pt-4">
        <button 
          onClick={onTakeAssessment} 
          className="w-full btn-primary px-4 py-3"
        >
          Take Assessment
        </button>
      </div>
    </div>
  );
};

const ProjectTab = ({ 
  skill, 
  project, 
  loading, 
  onStartProject 
}: { 
  skill: Skill; 
  project: any; 
  loading: boolean; 
  onStartProject: () => void 
}) => {
  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-4 border-primary-600 border-t-transparent mx-auto mb-4"></div>
        <p className="text-dark-500 dark:text-dark-400">Loading project info...</p>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="text-center py-8">
        <p className="text-dark-500 dark:text-dark-400">No project available</p>
        <button 
          onClick={onStartProject} 
          className="btn-primary mt-4 px-4 py-2"
        >
          Start Project
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="p-3 bg-dark-50 dark:bg-dark-800 rounded-lg">
        <h3 className="font-medium text-dark-900 dark:text-dark-100 mb-2">Project Overview</h3>
        <div className="space-y-2">
          <div className="flex items-center space-x-3 text-sm">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center">
              <Layers className="w-4 h-4 text-primary-600" />
            </div>
            <div>
              <p className="font-medium">Project Type</p>
              <p className="text-dark-500 dark:text-dark-400 capitalize">
                {project.project_type}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-3 text-sm">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center">
              <Target className="w-4 h-4 text-primary-600" />
            </div>
            <div>
              <p className="font-medium">Status</p>
              <p className="text-dark-500 dark:text-dark-400 capitalize">
                {project.status}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-3 text-sm">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4 text-primary-600" />
            </div>
            <div>
              <p className="font-medium">Grade</p>
              <p className="text-dark-500 dark:text-dark-400">
                {project.grade || 'Not graded'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Project Details */}
      <div className="p-3 bg-dark-50 dark:bg-dark-800 rounded-lg">
        <h3 className="font-medium text-dark-900 dark:text-dark-100 mb-2">Project Details</h3>
        <div className="space-y-2">
          <p className="text-sm text-dark-500 dark:text-dark-400">
            {project.description}
          </p>
          <div className="mt-3 space-y-1">
            <p className="font-medium text-dark-900 dark:text-dark-100">Requirements</p>
            <div className="space-y-1">
              {project.requirements?.map((req: any, index: number) => (
                <div key={index} className="flex items-start space-x-2 p-1 bg-dark-50 dark:bg-dark-800 rounded">
                  <div className="w-4 h-4 rounded-full flex items-center justify-center">
                    <CheckCircle2 className="w-2 h-2 text-white" />
                  </div>
                  <span className="text-sm">{req}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="mt-3 space-y-1">
            <p className="font-medium text-dark-900 dark:text-dark-100">Expected Deliverables</p>
            <div className="space-y-1">
              {project.deliverables?.map((deliv: any, index: number) => (
                <div key={index} className="flex items-start space-x-2 p-1 bg-dark-50 dark:bg-dark-800 rounded">
                  <div className="w-4 h-4 rounded-full flex items-center justify-center">
                    <Upload className="w-2 h-2 text-white" />
                  </div>
                  <span className="text-sm">{deliv}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Start Project Button */}
      <div className="pt-4">
        <button 
          onClick={onStartProject} 
          className="w-full btn-primary px-4 py-3"
        >
          Start Project
        </button>
      </div>
    </div>
  );
};
