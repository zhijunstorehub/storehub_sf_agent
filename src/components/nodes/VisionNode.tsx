import React, { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { Zap, Calendar, Layers } from 'lucide-react';

interface VisionNodeData {
  title: string;
  status: 'planned' | 'future';
  description: string;
  layers: string[];
  timeline: string;
}

export const VisionNode = memo(({ data }: NodeProps<VisionNodeData>) => {
  const isPlanned = data.status === 'planned';
  
  return (
    <div className={`bg-gradient-to-br ${isPlanned ? 'from-purple-900/50 to-blue-900/50 border-purple-500' : 'from-orange-900/50 to-red-900/50 border-orange-500'} border-2 rounded-lg p-4 min-w-[300px] max-w-[350px] shadow-xl backdrop-blur-sm`}>
      <Handle type="target" position={Position.Top} className="!bg-slate-600" />
      <Handle type="target" position={Position.Left} className="!bg-slate-600" />
      
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-bold text-white">{data.title}</h3>
        <div className={`flex items-center space-x-1 px-2 py-1 rounded-full ${isPlanned ? 'bg-purple-500/20 border-purple-500' : 'bg-orange-500/20 border-orange-500'} border`}>
          <Zap className={`w-4 h-4 ${isPlanned ? 'text-purple-400' : 'text-orange-400'}`} />
          <span className={`text-xs font-medium ${isPlanned ? 'text-purple-400' : 'text-orange-400'} capitalize`}>{data.status}</span>
        </div>
      </div>
      
      {/* Description */}
      <p className="text-sm text-slate-300 mb-4 leading-relaxed">{data.description}</p>
      
      {/* Timeline */}
      <div className="flex items-center space-x-2 mb-4">
        <Calendar className="w-4 h-4 text-slate-400" />
        <span className="text-sm text-slate-400">{data.timeline}</span>
      </div>
      
      {/* Layers/Components */}
      <div className="space-y-2">
        <div className="flex items-center space-x-2 mb-2">
          <Layers className="w-4 h-4 text-slate-400" />
          <span className="text-sm font-medium text-slate-300">Components</span>
        </div>
        {data.layers.map((layer, index) => (
          <div key={index} className={`text-xs p-2 rounded border ${isPlanned ? 'bg-purple-500/10 border-purple-500/30 text-purple-200' : 'bg-orange-500/10 border-orange-500/30 text-orange-200'} flex items-start`}>
            <span className="mr-2">•</span>
            <span>{layer}</span>
          </div>
        ))}
      </div>
      
      <Handle type="source" position={Position.Right} className="!bg-slate-600" />
      <Handle type="source" position={Position.Bottom} className="!bg-slate-600" />
    </div>
  );
}); 