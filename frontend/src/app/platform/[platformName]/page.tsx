'use client';

import React from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Database, Workflow, Box, ArrowRight } from 'lucide-react';

const metadataTypes = {
  salesforce: [
    { name: 'Objects', icon: <Database />, description: 'View and analyze standard and custom objects.' },
    { name: 'Flows', icon: <Workflow />, description: 'Explore and understand your Salesforce Flows.' },
  ],
  // Add other platforms here...
  chargebee: [
    { name: 'Customers', icon: <Database />, description: 'View and analyze your customer data.' },
    { name: 'Subscriptions', icon: <Workflow />, description: 'Explore and understand your subscription models.' },
    { name: 'Invoices', icon: <Box />, description: 'Get detailed analysis of your invoice data.' },
    { name: 'Items', icon: <Box />, description: 'Explore your product catalog of plans, addons, and charges.' },
  ],
  redshift: [],
  aws: [],
};

const PlatformPage = () => {
  const router = useRouter();
  const params = useParams();
  const platformName = params.platformName as keyof typeof metadataTypes;

  const handleTileClick = (metadataType: string) => {
    router.push(`/platform/${platformName}/${metadataType.toLowerCase()}`);
  };

  const availableMetadata = metadataTypes[platformName] || [];

  return (
    <div className="page-container">
      <h1 className="page-title">
        {platformName.charAt(0).toUpperCase() + platformName.slice(1)} Metadata
      </h1>
      <p className="page-subtitle">
        Select a metadata type to begin your analysis.
      </p>

      <div className="metadata-grid">
        {availableMetadata.map((meta) => (
          <div key={meta.name} className="metadata-tile" onClick={() => handleTileClick(meta.name)}>
            <div className="metadata-tile-header">
              <div className="metadata-tile-icon">{meta.icon}</div>
              <h2 className="metadata-tile-name">{meta.name}</h2>
            </div>
            <p className="metadata-tile-description">{meta.description}</p>
            <div className="metadata-tile-footer">
              <span>View {meta.name}</span>
              <ArrowRight size={16} />
            </div>
          </div>
        ))}
        {availableMetadata.length === 0 && (
            <p>No metadata types have been configured for this platform yet.</p>
        )}
      </div>
    </div>
  );
};

export default PlatformPage; 