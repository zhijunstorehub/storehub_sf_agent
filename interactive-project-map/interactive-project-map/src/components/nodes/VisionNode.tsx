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
    <div className={`bg-white ${isPlanned ? 'border-purple-400 bg-purple-50' : 'border-orange-400 bg-orange-50'} border-2 rounded-lg p-4 min-w-[300px] max-w-[350px] shadow-lg backdrop-blur-sm`}>
      <Handle type="target" position={Position.Top} className="!bg-gray-400" />
      <Handle type="target" position={Position.Left} className="!bg-gray-400" />
      
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-bold text-gray-900">{data.title}</h3>
        <div className={`flex items-center space-x-1 px-2 py-1 rounded-full ${isPlanned ? 'bg-purple-500/20 border-purple-500' : 'bg-orange-500/20 border-orange-500'} border`}>
          <Zap className={`w-4 h-4 ${isPlanned ? 'text-purple-700' : 'text-orange-700'}`} />
          <span className={`text-xs font-semibold ${isPlanned ? 'text-purple-700' : 'text-orange-700'} capitalize`}>{data.status}</span>
        </div>
      </div>
      
      {/* Description */}
      <p className="text-sm text-gray-800 mb-4 leading-relaxed font-medium">{data.description}</p>
      
      {/* Timeline */}
      <div className="flex items-center space-x-2 mb-4">
        <Calendar className="w-4 h-4 text-gray-700" />
        <span className="text-sm text-gray-800 font-semibold">{data.timeline}</span>
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