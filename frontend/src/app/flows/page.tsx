'use client';

import React, { useState, useEffect } from 'react';
import FlowsTable from '../components/FlowsTable';

interface Flow {
  id: string;
  flow_name: string;
  description: string;
  process_type: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export default function FlowsPage() {
  const [flows, setFlows] = useState<Flow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const API_BASE = 'http://localhost:8000';

  useEffect(() => {
    const fetchFlows = async () => {
      try {
        setLoading(true);
        const response = await fetch(`${API_BASE}/api/flows`);
        if (!response.ok) {
          throw new Error('Failed to fetch flows');
        }
        const data = await response.json();
        setFlows(Array.isArray(data) ? data : []);
        setError(null);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error';
        setError(`Failed to load flows.`);
        setFlows([]);
        console.error('Error fetching flows:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchFlows();
  }, []);

  if (loading) {
    return (
      <div className="supabase-app">
        <div className="flex items-center justify-center w-full">
          <div className="text-center">
            <div className="supabase-loading mb-4"></div>
            <p className="text-sm text-gray-600">Loading flows...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="supabase-app">
        <div className="flex items-center justify-center w-full">
          <div className="text-center">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="supabase-app">
      <main className="supabase-main">
        <div className="supabase-content">
          <div className="supabase-table-panel">
            <div className="supabase-table-header">
              <div className="supabase-table-title">
                Salesforce Flows ({flows.length} flows)
              </div>
            </div>
            <div className="supabase-table-container">
              <FlowsTable flows={flows} />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
} 