'use client';

import React, { useState, useEffect, useCallback } from 'react';
import ReactFlow, {
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  NodeTypes,
  EdgeTypes,
  MarkerType,
  Background,
  Controls,
  MiniMap,
} from 'react-flow-renderer';
import 'react-flow-renderer/dist/style.css';
import { Skill, MasteryRecord, MasteryLevel } from '@/types';
import { 
  BookOpen, 
  Zap, 
  Cpu, 
  Brain, 
  FlaskConical, 
  Code, 
  Settings,
  ChevronRight,
  CheckCircle,
  AlertCircle,
  Clock,
  Target,
  Layers,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface SkillMapProps {
  skills: Skill[];
  mastery: Record<string, MasteryRecord>;
  onSkillSelect: (skill: Skill) => void;
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

const categoryColors: Record<string, string> = {
  math: 'bg-blue-500',
  physics: 'bg-yellow-500',
  electronics: 'bg-orange-500',
  programming: 'bg-green-500',
  ai: 'bg-purple-500',
  robotics: 'bg-red-500',
  mechanical: 'bg-gray-500',
  default: 'bg-slate-500',
};

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

interface SkillNodeData {
  skill: Skill;
  mastery: MasteryRecord;
  onClick: () => void;
}

const SkillNode = ({ data }: { data: SkillNodeData }) => {
  const { skill, mastery, onClick } = data;
  const Icon = categoryIcons[skill.category] || categoryIcons.default;
  const categoryColor = categoryColors[skill.category] || categoryColors.default;
  const levelColor = levelColors[mastery.level as MasteryLevel] || levelColors.not_started;
  const masteryPercent = Math.round(mastery.mastery * 100);

  return (
    <div 
      className={cn(
        'skill-node group relative w-56 h-40 rounded-xl p-4 cursor-pointer transition-all duration-300',
        'bg-white dark:bg-dark-800 border-2',
        mastery.mastery > 0 ? 'border-primary-500/50' : 'border-dark-200 dark:border-dark-700',
        'hover:border-primary-500 hover:shadow-lg hover:shadow-primary-500/10',
        'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900'
      )}
      onClick={onClick}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}
      tabIndex={0}
      role="button"
      aria-label={`${skill.name}, ${levelLabels[mastery.level as MasteryLevel]}, ${masteryPercent}% mastery`}
    >
      {/* Category badge */}
      <div className="flex items-start justify-between mb-2">
        <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center', categoryColor)}>
          <Icon className="w-4 h-4 text-white" />
        </div>
        <div className={cn('w-2 h-2 rounded-full', levelColor)} title={levelLabels[mastery.level as MasteryLevel]} />
      </div>

      {/* Skill name */}
      <h3 className="font-semibold text-dark-900 dark:text-dark-100 text-sm mb-1 line-clamp-1">
        {skill.name}
      </h3>

      {/* Skill ID */}
      <p className="text-xs text-dark-500 dark:text-dark-400 font-mono mb-2">
        {skill.skill_id}
      </p>

      {/* Mastery bar */}
      <div className="w-full h-2 bg-dark-200 dark:bg-dark-700 rounded-full overflow-hidden">
        <div
          className={cn(
            'h-full rounded-full transition-all duration-500',
            levelColor.replace('bg-', 'bg-')
          )}
          style={{ width: `${masteryPercent}%` }}
        />
      </div>

      <div className="flex justify-between text-xs text-dark-500 dark:text-dark-400 mt-1">
        <span>{masteryPercent}% mastery</span>
        <span className="capitalize">{mastery.level.replace('_', ' ')}</span>
      </div>

      {/* Prerequisites indicator */}
      {skill.prerequisites && skill.prerequisites.length > 0 && (
        <div className="absolute bottom-2 right-2 flex items-center gap-1 text-xs text-dark-400">
          <Layers className="w-3 h-3" />
          <span>{skill.prerequisites.length}</span>
        </div>
      )}

      {/* Hover tooltip */}
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 bg-dark-900 dark:bg-dark-100 text-white dark:text-dark-900 rounded-lg shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none z-10">
        <p className="font-medium">{skill.name}</p>
        <p className="text-xs opacity-75 mt-1">{skill.description?.slice(0, 100)}...</p>
        <div className="flex gap-2 mt-2 text-xs">
          <span className="px-2 py-0.5 bg-dark-700 dark:bg-dark-300 rounded">{skill.category}</span>
          <span className="px-2 py-0.5 bg-dark-700 dark:bg-dark-300 rounded">Difficulty: {skill.difficulty}/10</span>
        </div>
        <div className="mt-2 pt-2 border-t border-dark-700 dark:border-dark-300">
          <p className="text-xs opacity-75">Click to start learning</p>
        </div>
      </div>
    </div>
  );
};

const nodeTypes: NodeTypes = {
  skill: SkillNode,
};

const CustomEdge = ({ 
  id, 
  sourceX, 
  sourceY, 
  targetX, 
  targetY, 
  sourcePosition, 
  targetPosition,
  markerEnd 
}: any) => {
  const path = `M${sourceX},${sourceY} C${sourceX + 50},${sourceY} ${targetX - 50},${targetY} ${targetX},${targetY}`;
  
  return (
    <g>
      <path
        id={id}
        d={path}
        stroke="currentColor"
        strokeWidth={1.5}
        fill="none"
        className="text-dark-300 dark:text-dark-600"
        markerEnd={markerEnd}
      />
    </g>
  );
};

const edgeTypes: EdgeTypes = {
  custom: CustomEdge,
};

export const SkillMap = ({ skills, mastery, onSkillSelect }: SkillMapProps) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [viewport, setViewport] = useState({ x: 0, y: 0, zoom: 1 });
  const [layout, setLayout] = useState<'hierarchical' | 'radial'>('hierarchical');

  // Build nodes and edges from skills
  useEffect(() => {
    const newNodes: Node[] = [];
    const newEdges: Edge[] = [];
    const skillMap = new Map<string, Skill>();

    skills.forEach(skill => skillMap.set(skill.skill_id, skill));

    // Position nodes using a simple hierarchical layout
    const categoryGroups = new Map<string, Skill[]>();
    skills.forEach(skill => {
      if (!categoryGroups.has(skill.category)) {
        categoryGroups.set(skill.category, []);
      }
      categoryGroups.get(skill.category)!.push(skill);
    });

    let yOffset = 0;
    const categoryOrder = ['math', 'physics', 'electronics', 'programming', 'ai', 'robotics', 'mechanical'];
    
    categoryOrder.forEach((cat, catIndex) => {
      const catSkills = categoryGroups.get(cat) || [];
      if (catSkills.length === 0) return;

      // Sort by difficulty
      catSkills.sort((a, b) => a.difficulty - b.difficulty);

      catSkills.forEach((skill, index) => {
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

        newNodes.push({
          id: skill.skill_id,
          type: 'skill',
          position: { x: catIndex * 320 + 100, y: yOffset + index * 140 + 100 },
          data: { skill, mastery: skillMastery, onClick: () => onSkillSelect(skill) },
        });

        // Add edges for prerequisites
        skill.prerequisites?.forEach(prereq => {
          newEdges.push({
            id: `${prereq.skill_id}-${skill.skill_id}`,
            source: prereq.skill_id,
            target: skill.skill_id,
            type: 'custom',
            animated: skillMastery.mastery > 0,
            style: { strokeWidth: 1.5 },
            markerEnd: {
              type: MarkerType.ArrowClosed,
              color: '#94a3b8',
              width: 16,
              height: 16,
            },
          });
        });
      });

      yOffset += Math.max(0, (catSkills.length - 1) * 140);
    });

    setNodes(newNodes);
    setEdges(newEdges);
  }, [skills, mastery, setNodes, setEdges]);

  const onConnect = useCallback((params: Connection) => {
    setEdges((eds) => addEdge({ ...params, type: 'custom', animated: true }, eds));
  }, [setEdges]);

  const fitView = () => {
    // This would trigger fitView in ReactFlow
  };

  return (
    <div className="flex-1 h-full relative bg-dark-50 dark:bg-dark-950 rounded-xl overflow-hidden">
      {/* Toolbar */}
      <div className="absolute top-4 left-4 right-4 z-10 flex items-center justify-between px-4 pointer-events-none">
        <div className="pointer-events-auto flex items-center gap-2">
          <h2 className="text-xl font-bold text-dark-900 dark:text-dark-100">Skill Map</h2>
          <div className="flex items-center gap-2 ml-4 border-l border-dark-200 dark:border-dark-700 pl-4">
            <select
              value={layout}
              onChange={(e) => setLayout(e.target.value as 'hierarchical' | 'radial')}
              className="input py-1 px-2 text-sm w-auto"
            >
              <option value="hierarchical">Hierarchical</option>
              <option value="radial">Radial</option>
            </select>
            <button
              onClick={fitView}
              className="btn-secondary px-3 py-1 text-sm"
              title="Fit View"
            >
              <Target className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Legend */}
        <div className="pointer-events-auto flex items-center gap-4 bg-white/80 dark:bg-dark-900/80 backdrop-blur-sm rounded-lg px-3 py-2 shadow-lg border border-dark-200 dark:border-dark-700">
          {Object.entries(levelLabels).map(([level, label]) => (
            <div key={level} className="flex items-center gap-1.5">
              <div className={cn('w-3 h-3 rounded-full', levelColors[level as MasteryLevel])} />
              <span className="text-xs text-dark-600 dark:text-dark-400">{label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* React Flow */}
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView={true}
        attributionPosition="bottom-right"
        className="h-full w-full"
      >
        <Background 
          color="#e2e8f0" 
          gap={16} 
          size={1} 
          className="dark:opacity-30"
        />
        <Controls className="bottom-4 right-4" />
        <MiniMap 
          className="bottom-4 left-4 w-64 h-48 rounded-lg border border-dark-200 dark:border-dark-700"
          nodeColor={(node) => {
            const masteryData = node.data?.mastery;
            if (masteryData) {
              return levelColors[masteryData.level as MasteryLevel] || '#94a3b8';
            }
            return '#94a3b8';
          }}
        />
      </ReactFlow>

      {/* Empty state */}
      {nodes.length === 0 && (
        <div className="absolute inset-0 flex flex-col items-center justify-center text-dark-500 dark:text-dark-400 p-8">
          <Layers className="w-16 h-16 mb-4 opacity-50" />
          <h3 className="text-lg font-medium mb-2">No skills loaded</h3>
          <p className="text-sm">Add skills to your knowledge graph to get started</p>
        </div>
      )}
    </div>
  );
};
