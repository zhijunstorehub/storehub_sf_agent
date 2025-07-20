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
    <div className="bg-white border-2 border-purple-400 rounded-lg p-4 min-w-[280px] max-w-[320px] shadow-lg backdrop-blur-sm bg-purple-50">
      <Handle type="target" position={Position.Top} className="!bg-gray-400" />
      <Handle type="target" position={Position.Left} className="!bg-gray-400" />
      
      {/* Header */}
      <div className="flex items-center space-x-2 mb-4">
        <Code className="w-5 h-5 text-purple-700" />
        <h3 className="text-lg font-bold text-gray-900">{data.title}</h3>
      </div>
      
      {/* Technologies */}
      <div className="space-y-3">
        {Object.entries(data.technologies).map(([category, tech]) => {
          const IconComponent = techIcons[category] || Code;
          return (
            <div key={category} className="flex items-center justify-between p-2 bg-purple-100 border border-purple-300 rounded">
              <div className="flex items-center space-x-2">
                <IconComponent className="w-4 h-4 text-purple-700" />
                <span className="text-sm font-semibold text-purple-800">{category}</span>
              </div>
              <span className="text-xs text-gray-800 font-mono font-semibold">{tech}</span>
            </div>
          );
        })}
      </div>
      
      <Handle type="source" position={Position.Right} className="!bg-gray-400" />
      <Handle type="source" position={Position.Bottom} className="!bg-gray-400" />
    </div>
  );
}); 