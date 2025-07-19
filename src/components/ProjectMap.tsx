'use client';

import React, { useCallback, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Node,
  Edge,
  Connection,
  ConnectionLineType,
  Panel,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { ProjectNode } from './nodes/ProjectNode';
import { VisionNode } from './nodes/VisionNode';
import { TechStackNode } from './nodes/TechStackNode';

const nodeTypes = {
  project: ProjectNode,
  vision: VisionNode,
  techStack: TechStackNode,
};

const initialNodes: Node[] = [
  // Current AI Colleague V1 - Center of the map
  {
    id: 'ai-colleague-v1',
    type: 'project',
    position: { x: 400, y: 300 },
    data: {
      title: 'AI Colleague V1.0',
      status: 'production',
      description: 'LLM-powered semantic flow analysis with Neo4j GraphRAG',
      features: [
        '✅ Semantic Understanding',
        '✅ Neo4j Knowledge Graph', 
        '✅ GraphRAG Queries',
        '✅ CLI Interface'
      ],
      progress: 100
    },
  },
  
  // POC Archive - Historical context
  {
    id: 'poc-archive',
    type: 'project',
    position: { x: 100, y: 300 },
    data: {
      title: 'POC Archive',
      status: 'archived',
      description: 'Complete development journey and experimentation',
      features: [
        '📚 All experimental approaches',
        '📚 10,000+ Salesforce metadata files',
        '📚 Multiple parsing attempts',
        '📚 Learning documentation'
      ],
      progress: 100
    },
  },
  
  // Future Vision - Storehub Intelligence Orchestration
  {
    id: 'storehub-orchestration',
    type: 'vision',
    position: { x: 750, y: 150 },
    data: {
      title: 'Storehub Intelligence Orchestration',
      status: 'planned',
      description: 'Complete AI-driven business intelligence platform',
      layers: [
        'AI Agent Layer',
        'Semantic Layer', 
        'Autonomous Operations',
        'Data Sources Integration'
      ],
      timeline: '2024-2025'
    },
  },
  
  // Technology Stack
  {
    id: 'tech-stack',
    type: 'techStack',
    position: { x: 400, y: 100 },
    data: {
      title: 'Technology Stack',
      technologies: {
        'LLM': 'Google Gemini',
        'Database': 'Neo4j Aura Cloud',
        'Backend': 'Python + Poetry',
        'Architecture': 'GraphRAG',
        'Interface': 'Rich CLI'
      }
    },
  },
  
  // Semantic Layer (Current Implementation)
  {
    id: 'semantic-layer',
    type: 'project',
    position: { x: 600, y: 300 },
    data: {
      title: 'Semantic Layer',
      status: 'active',
      description: 'Business context understanding and natural language processing',
      features: [
        '✅ Business Context Understanding',
        '✅ Natural Language Processing',
        '✅ Query Translation',
        '⚠️ Access Control (Planned)'
      ],
      progress: 75
    },
  },
  
  // Data Sources
  {
    id: 'data-sources',
    type: 'project',
    position: { x: 400, y: 500 },
    data: {
      title: 'Data Sources',
      status: 'expanding',
      description: 'Multi-system integration for comprehensive analysis',
      features: [
        '✅ Salesforce Flows',
        '⚠️ Metabase (Planned)',
        '⚠️ Chargebee (Planned)',
        '⚠️ Intercom (Planned)'
      ],
      progress: 25
    },
  },
  
  // Future AI Agents
  {
    id: 'ai-agents',
    type: 'vision',
    position: { x: 750, y: 350 },
    data: {
      title: 'AI Agent Ecosystem',
      status: 'future',
      description: 'Specialized agents for different business functions',
      layers: [
        '💡 Insight Agent',
        '🚨 Triage Agent', 
        '👁️ Monitor Agent',
        '🔧 Fix Agent',
        '📚 Learn Agent'
      ],
      timeline: 'V2.0+'
    },
  },
];

const initialEdges: Edge[] = [
  // Evolution path
  {
    id: 'poc-to-v1',
    source: 'poc-archive',
    target: 'ai-colleague-v1',
    type: 'smoothstep',
    animated: true,
    label: 'Evolution',
    style: { stroke: '#10b981', strokeWidth: 3 }
  },
  
  // Current system connections
  {
    id: 'v1-to-semantic',
    source: 'ai-colleague-v1',
    target: 'semantic-layer',
    type: 'smoothstep',
    label: 'Powers',
    style: { stroke: '#3b82f6' }
  },
  
  {
    id: 'v1-to-data',
    source: 'ai-colleague-v1',
    target: 'data-sources',
    type: 'smoothstep',
    label: 'Processes',
    style: { stroke: '#3b82f6' }
  },
  
  {
    id: 'tech-to-v1',
    source: 'tech-stack',
    target: 'ai-colleague-v1',
    type: 'smoothstep',
    label: 'Built With',
    style: { stroke: '#8b5cf6' }
  },
  
  // Future vision connections
  {
    id: 'v1-to-orchestration',
    source: 'ai-colleague-v1',
    target: 'storehub-orchestration',
    type: 'smoothstep',
    animated: true,
    label: 'Evolves Into',
    style: { stroke: '#f59e0b', strokeWidth: 3, strokeDasharray: '5,5' }
  },
  
  {
    id: 'semantic-to-agents',
    source: 'semantic-layer',
    target: 'ai-agents',
    type: 'smoothstep',
    animated: true,
    label: 'Enables',
    style: { stroke: '#f59e0b', strokeDasharray: '5,5' }
  },
  
  {
    id: 'agents-to-orchestration',
    source: 'ai-agents',
    target: 'storehub-orchestration',
    type: 'smoothstep',
    label: 'Part Of',
    style: { stroke: '#ef4444', strokeDasharray: '5,5' }
  },
];

export default function ProjectMap() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const proOptions = useMemo(() => ({ hideAttribution: true }), []);

  return (
    <div className="h-screen w-full bg-gradient-to-br from-slate-900 to-slate-800">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        connectionLineType={ConnectionLineType.SmoothStep}
        fitView
        proOptions={proOptions}
        className="react-flow-dark-theme"
      >
        <Background 
          color="#1f2937" 
          gap={20} 
          className="bg-slate-800"
        />
        <Controls 
          className="bg-slate-700 border-slate-600 text-white"
        />
        <MiniMap 
          className="bg-slate-700 border-slate-600"
          nodeColor="#3b82f6"
          maskColor="rgba(0, 0, 0, 0.2)"
        />
        <Panel position="top-left" className="text-white">
          <div className="bg-slate-800/90 backdrop-blur-sm rounded-lg p-4 border border-slate-600">
            <h1 className="text-2xl font-bold mb-2 text-blue-400">
              🤖 AI Colleague Project Evolution
            </h1>
            <p className="text-sm text-slate-300 max-w-sm">
              Interactive visualization showing the journey from POC to production system 
              and future vision. Click nodes to explore details.
            </p>
          </div>
        </Panel>
        
        <Panel position="bottom-right" className="text-white">
          <div className="bg-slate-800/90 backdrop-blur-sm rounded-lg p-3 border border-slate-600">
            <div className="flex flex-col space-y-2 text-xs">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-green-500 rounded"></div>
                <span>Production Ready</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-blue-500 rounded"></div>
                <span>In Development</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-yellow-500 rounded"></div>
                <span>Future Vision</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-gray-500 rounded"></div>
                <span>Archived</span>
              </div>
            </div>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
} 