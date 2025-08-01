'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { ArrowRight } from 'lucide-react';
import { platforms } from './platforms';

const PlatformsPage = () => {
    const router = useRouter();
    const handleTileClick = (href: string) => {
        router.push(href);
    };

    return (
        <div className="page-container">
            <div className="page-header">
                <h1 className="page-title">Platforms</h1>
                <p className="page-subtitle">Select a platform to begin your analysis.</p>
            </div>
            <div className="metadata-grid">
                {platforms.map((platform) => (
                    <div key={platform.name} className="metadata-tile" onClick={() => handleTileClick(platform.href)}>
                        <div className="metadata-tile-header">
                            <div className="metadata-tile-icon">
                                <Image src={platform.logo} alt={`${platform.name} logo`} width={24} height={24} />
                            </div>
                            <h2 className="metadata-tile-name">{platform.name}</h2>
                        </div>
                        <p className="metadata-tile-description">
                            Analyze and manage your {platform.name} metadata.
                        </p>
                        <div className="metadata-tile-footer">
                            <span>View {platform.name}</span>
                            <ArrowRight size={16} />
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default PlatformsPage; 