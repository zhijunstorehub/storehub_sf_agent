import React, { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { CheckCircle, Clock, Archive, Settings } from 'lucide-react';

interface ProjectNodeData {
  title: string;
  status: 'production' | 'active' | 'expanding' | 'archived';
  description: string;
  features: string[];
  progress: number;
}

const statusConfig = {
  production: {
    color: 'bg-green-500',
    textColor: 'text-green-700',
    borderColor: 'border-green-500',
    icon: CheckCircle,
    bgColor: 'bg-green-50'
  },
  active: {
    color: 'bg-blue-500',
    textColor: 'text-blue-700',
    borderColor: 'border-blue-500',
    icon: Settings,
    bgColor: 'bg-blue-50'
  },
  expanding: {
    color: 'bg-orange-500',
    textColor: 'text-orange-700',
    borderColor: 'border-orange-500',
    icon: Clock,
    bgColor: 'bg-orange-50'
  },
  archived: {
    color: 'bg-gray-500',
    textColor: 'text-gray-700',
    borderColor: 'border-gray-500',
    icon: Archive,
    bgColor: 'bg-gray-50'
  }
};

export const ProjectNode = memo(({ data }: NodeProps<ProjectNodeData>) => {
  const config = statusConfig[data.status];
  const StatusIcon = config.icon;

  return (
    <div className={`bg-white border-2 ${config.borderColor} rounded-lg p-4 min-w-[280px] max-w-[320px] shadow-lg backdrop-blur-sm ${config.bgColor}`}>
      <Handle type="target" position={Position.Top} className="!bg-gray-400" />
      <Handle type="target" position={Position.Left} className="!bg-gray-400" />
      
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-bold text-gray-900 truncate">{data.title}</h3>
        <div className={`flex items-center space-x-1 px-2 py-1 rounded-full ${config.color}/20 border ${config.borderColor}`}>
          <StatusIcon className={`w-4 h-4 ${config.textColor}`} />
          <span className={`text-xs font-semibold ${config.textColor} capitalize`}>{data.status}</span>
        </div>
      </div>
      
      {/* Description */}
      <p className="text-sm text-gray-800 mb-4 leading-relaxed font-medium">{data.description}</p>
      
      {/* Progress Bar */}
      {data.progress && (
        <div className="mb-4">
          <div className="flex justify-between text-xs text-gray-700 mb-1 font-semibold">
            <span>Progress</span>
            <span>{data.progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className={`h-2 rounded-full transition-all duration-300 ${config.color}`}
              style={{ width: `${data.progress}%` }}
            />
          </div>
        </div>
      )}
      
      {/* Features */}
      <div className="space-y-1">
        {data.features.map((feature, index) => (
          <div key={index} className="text-xs text-gray-800 flex items-start font-medium">
            <span className="mr-2">•</span>
            <span>{feature}</span>
          </div>
        ))}
      </div>
      
      <Handle type="source" position={Position.Right} className="!bg-gray-400" />
      <Handle type="source" position={Position.Bottom} className="!bg-gray-400" />
    </div>
  );
}); 