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
  // === HISTORICAL LAYER (Far Left) ===
  {
    id: 'poc-archive',
    type: 'project',
    position: { x: 50, y: 350 },
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

  // === FOUNDATION LAYER (Top, well spaced) ===
  {
    id: 'tech-stack',
    type: 'techStack',
    position: { x: 650, y: 50 },
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

  // === PRODUCTION LAYER (Center, main focus) ===
  {
    id: 'ai-colleague-v1',
    type: 'project',
    position: { x: 650, y: 330 },
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

  // === ACTIVE COMPONENTS (Right side, well spaced) ===
  {
    id: 'semantic-layer',
    type: 'project',
    position: { x: 1100, y: 200 },
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
  
  {
    id: 'data-sources',
    type: 'project',
    position: { x: 650, y: 680 },
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

  // === FUTURE VISION LAYER (Far right, well spaced) ===
  {
    id: 'storehub-orchestration',
    type: 'vision',
    position: { x: 1550, y: 150 },
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
  
  {
    id: 'ai-agents',
    type: 'vision',
    position: { x: 1550, y: 480 },
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
  // === EVOLUTION FLOW (Left to Center) ===
  {
    id: 'poc-to-v1',
    source: 'poc-archive',
    target: 'ai-colleague-v1',
    type: 'smoothstep',
    animated: true,
    label: 'Evolution',
    style: { stroke: '#10b981', strokeWidth: 3 }
  },
  
  // === FOUNDATION CONNECTIONS (Top to Center) ===
  {
    id: 'tech-to-v1',
    source: 'tech-stack',
    target: 'ai-colleague-v1',
    type: 'smoothstep',
    label: 'Built With',
    style: { stroke: '#8b5cf6', strokeWidth: 2 }
  },
  
  // === CURRENT SYSTEM ARCHITECTURE (Center outward) ===
  {
    id: 'v1-to-semantic',
    source: 'ai-colleague-v1',
    target: 'semantic-layer',
    type: 'smoothstep',
    label: 'Powers',
    style: { stroke: '#3b82f6', strokeWidth: 2 }
  },
  
  {
    id: 'v1-to-data',
    source: 'ai-colleague-v1',
    target: 'data-sources',
    type: 'smoothstep',
    label: 'Processes',
    style: { stroke: '#3b82f6', strokeWidth: 2 }
  },
  
  // === FUTURE VISION FLOW (Center to Right) ===
  {
    id: 'v1-to-orchestration',
    source: 'ai-colleague-v1',
    target: 'storehub-orchestration',
    type: 'smoothstep',
    animated: true,
    label: 'Evolves Into',
    style: { stroke: '#f59e0b', strokeWidth: 3, strokeDasharray: '8,4' }
  },
  
  {
    id: 'semantic-to-agents',
    source: 'semantic-layer',
    target: 'ai-agents',
    type: 'smoothstep',
    animated: true,
    label: 'Enables',
    style: { stroke: '#f59e0b', strokeWidth: 2, strokeDasharray: '5,3' }
  },
  
  {
    id: 'agents-to-orchestration',
    source: 'ai-agents',
    target: 'storehub-orchestration',
    type: 'smoothstep',
    label: 'Part Of',
    style: { stroke: '#ef4444', strokeWidth: 2, strokeDasharray: '5,3' }
  },
  
  // === DATA FLOW CONNECTIONS ===
  {
    id: 'data-to-semantic',
    source: 'data-sources',
    target: 'semantic-layer',
    type: 'smoothstep',
    label: 'Feeds',
    style: { stroke: '#06b6d4', strokeWidth: 1.5 }
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
    <div className="h-screen w-full bg-gradient-to-br from-blue-50 to-indigo-100">
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
        className="react-flow-light-theme"
        fitViewOptions={{
          padding: 0.2,
          includeHiddenNodes: false,
          minZoom: 0.5,
          maxZoom: 1.5,
        }}
      >
        <Background 
          color="#e2e8f0" 
          gap={20} 
          className="bg-white"
        />
        <Controls 
          className="bg-white border-gray-300 shadow-lg text-gray-700"
        />
        <MiniMap 
          className="bg-white border-gray-300 shadow-lg"
          nodeColor="#3b82f6"
          maskColor="rgba(255, 255, 255, 0.8)"
        />
        <Panel position="top-left" className="text-gray-800">
          <div className="bg-white/95 backdrop-blur-sm rounded-lg p-4 border border-gray-200 shadow-lg">
            <h1 className="text-2xl font-bold mb-2 text-blue-600">
              🤖 AI Colleague Project Evolution
            </h1>
            <p className="text-sm text-gray-600 max-w-sm">
              Interactive visualization showing the journey from POC to production system 
              and future vision. Drag, zoom, and click nodes to explore details.
            </p>
          </div>
        </Panel>
        
        <Panel position="bottom-right" className="text-gray-800">
          <div className="bg-white/95 backdrop-blur-sm rounded-lg p-3 border border-gray-200 shadow-lg">
            <div className="flex flex-col space-y-2 text-xs">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-green-500 rounded shadow"></div>
                <span>Production Ready</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-blue-500 rounded shadow"></div>
                <span>In Development</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-orange-500 rounded shadow"></div>
                <span>Future Vision</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-gray-500 rounded shadow"></div>
                <span>Archived</span>
              </div>
            </div>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
} 