import React, { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { Code, Database, Cpu, Globe, Terminal } from 'lucide-react';

interface TechStackNodeData {
  title: string;
  technologies: Record<string, string>;
}

const techIcons: Record<string, any> = {
  'LLM': Cpu,
  'Database': Database,
  'Backend': Code,
  'Architecture': Globe,
  'Interface': Terminal,
};

export const TechStackNode = memo(({ data }: NodeProps<TechStackNodeData>) => {
  return (
    <div className="bg-gradient-to-br from-violet-900/50 to-indigo-900/50 border-2 border-violet-500 rounded-lg p-4 min-w-[280px] max-w-[320px] shadow-xl backdrop-blur-sm">
      <Handle type="target" position={Position.Top} className="!bg-slate-600" />
      <Handle type="target" position={Position.Left} className="!bg-slate-600" />
      
      {/* Header */}
      <div className="flex items-center space-x-2 mb-4">
        <Code className="w-5 h-5 text-violet-400" />
        <h3 className="text-lg font-bold text-white">{data.title}</h3>
      </div>
      
      {/* Technologies */}
      <div className="space-y-3">
        {Object.entries(data.technologies).map(([category, tech]) => {
          const IconComponent = techIcons[category] || Code;
          return (
            <div key={category} className="flex items-center justify-between p-2 bg-violet-500/10 border border-violet-500/30 rounded">
              <div className="flex items-center space-x-2">
                <IconComponent className="w-4 h-4 text-violet-400" />
                <span className="text-sm font-medium text-violet-200">{category}</span>
              </div>
              <span className="text-xs text-slate-300 font-mono">{tech}</span>
            </div>
          );
        })}
      </div>
      
      <Handle type="source" position={Position.Right} className="!bg-slate-600" />
      <Handle type="source" position={Position.Bottom} className="!bg-slate-600" />
    </div>
  );
}); 