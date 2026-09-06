'use client';

import { useState, useEffect } from 'react';
import { SkillMap } from '@/components/SkillMap';
import { ProgressSidebar } from '@/components/ProgressSidebar';
import { TutorPanel } from '@/components/TutorPanel';
import { Header } from '@/components/Header';
import { Skill, MasteryRecord, User } from '@/types';

export default function Dashboard() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [mastery, setMastery] = useState<Record<string, MasteryRecord>>({});
  const [user, setUser] = useState<User | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);
  const [view, setView] = useState<'map' | 'tutor' | 'progress'>('map');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [skillsRes, masteryRes, userRes] = await Promise.all([
        fetch('/api/backend/skills').then(r => r.json()),
        fetch('/api/backend/mastery').then(r => r.json()),
        fetch('/api/backend/users/me').then(r => r.json()),
      ]);
      
      setSkills(skillsRes);
      setUser(userRes);
      
      const masteryMap: Record<string, MasteryRecord> = {};
      masteryRes.forEach((m: MasteryRecord) => {
        masteryMap[m.skill_id] = m;
      });
      setMastery(masteryMap);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getMasteryForSkill = (skillId: string) => {
    return mastery[skillId] || {
      skill_id: skillId,
      skill_name: skills.find(skill => skill.skill_id === skillId)?.name || skillId,
      mastery: 0,
      confidence: 0,
      level: 'not_started' as const,
      evidence_count: 0,
      last_review: null,
      next_review: null,
      review_count: 0,
    };
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary-600 border-t-transparent mx-auto mb-4"></div>
          <p className="text-dark-600 dark:text-dark-400">Loading Self Study OS...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Header user={user} onViewChange={setView} currentView={view} />
      
      <div className="flex-1 flex overflow-hidden">
        {/* Main Content */}
        <main className="flex-1 overflow-auto p-4 md:p-6">
          {view === 'map' && (
            <SkillMap
              skills={skills}
              mastery={mastery}
              onSkillSelect={setSelectedSkill}
            />
          )}
          
          {view === 'tutor' && selectedSkill && (
            <TutorPanel
              skill={selectedSkill}
              mastery={getMasteryForSkill(selectedSkill.skill_id)}
              onClose={() => setSelectedSkill(null)}
            />
          )}
          
          {view === 'progress' && (
            <ProgressSidebar
              skills={skills}
              mastery={mastery}
              user={user}
            />
          )}
        </main>

        {/* Right Sidebar - Skill Details / Tutor */}
        {(view === 'map' || view === 'progress') && selectedSkill && (
          <aside className="w-96 border-l border-dark-200 dark:border-dark-700 bg-white dark:bg-dark-900 overflow-auto">
            <TutorPanel
              skill={selectedSkill}
              mastery={getMasteryForSkill(selectedSkill.skill_id)}
              onClose={() => setSelectedSkill(null)}
            />
          </aside>
        )}
      </div>
    </div>
  );
}
