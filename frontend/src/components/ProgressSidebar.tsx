'use client';

import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  TrendingUp, 
  Clock, 
  CheckCircle2, 
  AlertTriangle,
  List,
  Target,
  BookOpen,
  Zap,
  Cpu,
  Brain,
  Code,
  FlaskConical,
  Settings,
} from 'lucide-react';
import { Skill, MasteryRecord, User, MasteryLevel } from '@/types';
import { cn } from '@/lib/utils';

interface ProgressSidebarProps {
  skills: Skill[];
  mastery: Record<string, MasteryRecord>;
  user: User | null;
}

const levelColors: Record<MasteryLevel, string> = {
  not_started: 'bg-dark-300 dark:bg-dark-600',
  understanding: 'bg-blue-500',
  guided_practice: 'bg-yellow-500',
  independent: 'bg-green-500',
  project_proven: 'bg-purple-500',
};

const levelLabels: Record<MasteryLevel, string> = {
  not_started: 'Not Started',
  understanding: 'Understanding',
  guided_practice: 'Guided Practice',
  independent: 'Independent',
  project_proven: 'Project Proven',
};

const categoryIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  math: BookOpen,
  physics: Zap,
  electronics: Cpu,
  programming: Code,
  ai: Brain,
  robotics: FlaskConical,
  mechanical: Settings,
  default: BookOpen,
};

export const ProgressSidebar = ({ skills, mastery, user }: ProgressSidebarProps) => {
  const [tab, setTab] = useState<'overview' | 'skills' | 'stats'>('overview');
  const [loading, setLoading] = useState(false);

  // Calculate progress summary
  const progressSummary = React.useMemo(() => {
    const masteryRecords = Object.values(mastery);
    const totalSkills = skills.length;
    
    const byLevel: Record<MasteryLevel, number> = {
      not_started: 0,
      understanding: 0,
      guided_practice: 0,
      independent: 0,
      project_proven: 0,
    };
    
    let totalMastery = 0;
    let totalConfidence = 0;
    let skillsNeedingReview = 0;
    let totalEvidence = 0;
    
    masteryRecords.forEach(record => {
      byLevel[record.level as MasteryLevel] += 1;
      totalMastery += record.mastery;
      totalConfidence += record.confidence;
      totalEvidence += record.evidence_count;
      
      // Check if needs review (simplified)
      if (record.next_review) {
        const nextReview = new Date(record.next_review);
        if (nextReview <= new Date()) {
          skillsNeedingReview += 1;
        }
      }
    });
    
    return {
      total_skills: totalSkills,
      by_level: byLevel,
      average_mastery: totalSkills > 0 ? totalMastery / totalSkills : 0,
      average_confidence: totalSkills > 0 ? totalConfidence / totalSkills : 0,
      skills_needing_review: skillsNeedingReview,
      total_evidence_count: totalEvidence,
    };
  }, [mastery, skills]);

  // Skills sorted by mastery level
  const sortedSkills = React.useMemo(() => {
    return [...skills].sort((a, b) => {
      const masteryA = mastery[a.skill_id]?.mastery || 0;
      const masteryB = mastery[b.skill_id]?.mastery || 0;
      return masteryB - masteryA; // Descending
    });
  }, [mastery, skills]);

  return (
    <aside className="w-80 border-r border-dark-200 dark:border-dark-700 bg-white dark:bg-dark-900 overflow-auto">
      <div className="p-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-dark-900 dark:text-dark-100">
            Learning Dashboard
          </h2>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setTab('overview')}
              className={cn(
                'px-3 py-1 rounded text-sm font-medium',
                tab === 'overview' ? 'bg-primary-600 text-white' : 'bg-dark-200 dark:bg-dark-700 text-dark-300 hover:bg-dark-300 dark:hover:bg-dark-600'
              )}
            >
              Overview
            </button>
            <button
              onClick={() => setTab('skills')}
              className={cn(
                'px-3 py-1 rounded text-sm font-medium',
                tab === 'skills' ? 'bg-primary-600 text-white' : 'bg-dark-200 dark:bg-dark-700 text-dark-300 hover:bg-dark-300 dark:hover:bg-dark-600'
              )}
            >
              Skills
            </button>
            <button
              onClick={() => setTab('stats')}
              className={cn(
                'px-3 py-1 rounded text-sm font-medium',
                tab === 'stats' ? 'bg-primary-600 text-white' : 'bg-dark-200 dark:bg-dark-700 text-dark-300 hover:bg-dark-300 dark:hover:bg-dark-600'
              )}
            >
              Stats
            </button>
          </div>
        </div>

        {/* Tab Content */}
        {tab === 'overview' && (
          <div className="space-y-4">
            {/* User Info */}
            {user && (
              <div className="p-3 bg-dark-50 dark:bg-dark-800 rounded-lg">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-primary-600 rounded-full flex items-center justify-center">
                    <Brain className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <p className="font-medium text-dark-900 dark:text-dark-100">{user.full_name || user.email}</p>
                    <p className="text-xs text-dark-500 dark:text-dark-400">{user.email}</p>
                  </div>
                </div>
              </div>
            )}
            
            {/* Progress Overview */}
            <div className="space-y-3">
              <h3 className="text-lg font-semibold text-dark-900 dark:text-dark-100">Progress Overview</h3>
              
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-dark-50 dark:bg-dark-800 rounded-lg">
                  <p className="text-xs text-dark-500 dark:text-dark-400">Total Skills</p>
                  <p className="text-2xl font-bold text-dark-900 dark:text-dark-100">{progressSummary.total_skills}</p>
                </div>
                <div className="p-3 bg-dark-50 dark:bg-dark-800 rounded-lg">
                  <p className="text-xs text-dark-500 dark:text-dark-400">Avg Mastery</p>
                  <p className="text-2xl font-bold text-dark-900 dark:text-dark-100">
                    {Math.round(progressSummary.average_mastery * 100)}%
                  </p>
                </div>
                <div className="p-3 bg-dark-50 dark:bg-dark-800 rounded-lg">
                  <p className="text-xs text-dark-500 dark:text-dark-400">Skills to Review</p>
                  <p className="text-2xl font-bold text-dark-900 dark:text-dark-100">
                    {progressSummary.skills_needing_review}
                  </p>
                </div>
                <div className="p-3 bg-dark-50 dark:bg-dark-800 rounded-lg">
                  <p className="text-xs text-dark-500 dark:text-dark-400">Evidence Items</p>
                  <p className="text-2xl font-bold text-dark-900 dark:text-dark-100">
                    {progressSummary.total_evidence_count}
                  </p>
                </div>
              </div>
              
              {/* Mastery Distribution */}
              <div className="space-y-2">
                <p className="text-sm font-medium text-dark-900 dark:text-dark-100">Mastery Distribution</p>
                <div className="grid grid-cols-5 gap-1">
                  {Object.entries(progressSummary.by_level).map(([level, count]) => (
                    <div key={level} className="flex flex-col items-center">
                      <div className={cn('w-8 h-8 rounded-full mb-1', levelColors[level as MasteryLevel])} />
                      <p className="text-xs text-dark-600 dark:text-dark-400">{count}</p>
                      <p className="text-xs text-dark-500 dark:text-dark-400 capitalize">
                        {level.replace('_', ' ')}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
        
        {tab === 'skills' && (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold text-dark-900 dark:text-dark-100">Skills Progress</h3>
            <div className="space-y-2">
              {sortedSkills.map(skill => {
                const skillMastery = mastery[skill.skill_id] || {
                  skill_id: skill.skill_id,
                  skill_name: skill.name,
                  mastery: 0,
                  confidence: 0,
                  level: 'not_started' as MasteryLevel,
                  evidence_count: 0,
                  last_review: null,
                  next_review: null,
                  review_count: 0,
                };
                const masteryPercent = Math.round(skillMastery.mastery * 100);
                const CategoryIcon = categoryIcons[skill.category] || categoryIcons.default;
                
                return (
                  <div key={skill.id} className="p-3 bg-dark-50 dark:bg-dark-800 rounded-lg border-l-4">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 rounded-lg flex items-center justify-center">
                          <CategoryIcon className="w-4 h-4 text-primary-600" />
                        </div>
                        <div>
                          <p className="font-medium text-dark-900 dark:text-dark-100">{skill.name}</p>
                          <p className="text-xs text-dark-500 dark:text-dark-400 font-mono">
                            {skill.skill_id}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <div className={cn('w-2 h-2 rounded-full', levelColors[skillMastery.level as MasteryLevel])} />
                        <span className="text-xs text-dark-600 dark:text-dark-400 capitalize">
                          {skillMastery.level.replace('_', ' ')}
                        </span>
                      </div>
                    </div>
                    
                    <div className="w-full h-2 bg-dark-200 dark:bg-dark-700 rounded-full overflow-hidden mt-2">
                      <div
                        className={cn(
                          'h-full rounded-full transition-all duration-500',
                          levelColors[skillMastery.level as MasteryLevel].replace('bg-', 'bg-')
                        )}
                        style={{ width: `${masteryPercent}%` }}
                      />
                    </div>
                    
                    <div className="flex justify-between text-xs text-dark-500 dark:text-dark-400 mt-1">
                      <span>{masteryPercent}% mastery</span>
                      <span>{skillMastery.evidence_count} evidence</span>
                    </div>
                    
                    {skillMastery.mastery > 0 && skillMastery.mastery < 1 && (
                      <div className="mt-1">
                        <div className="w-full h-0.5 bg-dark-200 dark:bg-dark-700 rounded">
                          <div
                            className="h-full bg-primary-500/20 rounded"
                            style={{ width: `${Math.min(100, masteryPercent + 10)}%` }}
                          />
                        </div>
                        <p className="text-xs text-dark-400 dark:text-dark-500 mt-1 text-center">
                          Next milestone: {Math.ceil((skillMastery.mastery + 0.1) * 100)}%
                        </p>
                      </div>
                    )}
                  </div>
                );
              })}
              </div>
            </div>
        )}
        
        {tab === 'stats' && (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold text-dark-900 dark:text-dark-100">Learning Statistics</h3>
            
            {/* Learning Streak */}
            <div className="p-3 bg-dark-50 dark:bg-dark-800 rounded-lg">
              <p className="text-sm font-medium text-dark-900 dark:text-dark-100 mb-2">Learning Streak</p>
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 bg-primary-600 rounded-full flex items-center justify-center">
                  <Clock className="w-6 h-6 text-white" />
                </div>
                <div>
                  <p className="text-xl font-bold text-dark-900 dark:text-dark-100">
                    {/* Calculate streak from mastery records - simplified */}
                    7
                  </p>
                  <p className="text-xs text-dark-500 dark:text-dark-400">days</p>
                </div>
              </div>
            </div>
            
            {/* Recent Activity */}
            <div className="space-y-2">
              <p className="text-sm font-medium text-dark-900 dark:text-dark-100 mb-2">Recent Activity</p>
              <div className="space-y-1">
                {/* Mock recent activity - in real app, this would come from API */}
                <div className="p-2 bg-dark-50 dark:bg-dark-800 rounded-lg">
                  <div className="flex items-start space-x-3">
                    <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center">
                      <CheckCircle2 className="w-4 h-4 text-white" />
                    </div>
                    <div className="flex-1">
                      <p className="font-medium text-dark-900 dark:text-dark-100">Completed Ohm's Law quiz</p>
                      <p className="text-xs text-dark-500 dark:text-dark-400">2 hours ago</p>
                    </div>
                  </div>
                </div>
                <div className="p-2 bg-dark-50 dark:bg-dark-800 rounded-lg">
                  <div className="flex items-start space-x-3">
                    <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center">
                      <BookOpen className="w-4 h-4 text-white" />
                    </div>
                    <div className="flex-1">
                      <p className="font-medium text-dark-900 dark:text-dark-100">Started Vector Calculus lesson</p>
                      <p className="text-xs text-dark-500 dark:text-dark-400">5 hours ago</p>
                    </div>
                  </div>
                </div>
                <div className="p-2 bg-dark-50 dark:bg-dark-800 rounded-lg">
                  <div className="flex items-start space-x-3">
                    <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center">
                      <Zap className="w-4 h-4 text-white" />
                    </div>
                    <div className="flex-1">
                      <p className="font-medium text-dark-900 dark:text-dark-100">Built first circuit simulation</p>
                      <p className="text-xs text-dark-500 dark:text-dark-400">1 day ago</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};
