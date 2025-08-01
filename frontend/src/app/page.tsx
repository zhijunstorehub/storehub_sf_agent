'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { ArrowRight, Database, GitBranch, Share2 } from 'lucide-react';

const HomePage = () => {
  const router = useRouter();

  return (
    <div className="home-container">
      <div className="hero-section">
        <h1 className="hero-title">Your Business Intelligence Hub</h1>
        <p className="hero-subtitle">
          Seamlessly explore, analyze, and manage your metadata across all platforms.
        </p>
        <button onClick={() => router.push('/platform')} className="hero-cta">
          Get Started <ArrowRight size={20} />
        </button>
      </div>

      <div className="guides-section">
        <div className="guide-card">
          <div className="guide-icon"><Database /></div>
          <h3 className="guide-title">Centralized Metadata</h3>
          <p className="guide-description">
            Connect to your platforms and get a comprehensive, unified view of your metadata.
          </p>
        </div>
        <div className="guide-card">
          <div className="guide-icon"><GitBranch /></div>
          <h3 className="guide-title">Powerful Analysis</h3>
          <p className="guide-description">
            Leverage advanced tools to understand dependencies and analyze your data architecture.
          </p>
        </div>
        <div className="guide-card">
          <div className="guide-icon"><Share2 /></div>
          <h3 className="guide-title">Collaborative Insights</h3>
          <p className="guide-description">
            Share insights and collaborate with your team to make data-driven decisions.
          </p>
        </div>
      </div>
    </div>
  );
};

export default HomePage; 