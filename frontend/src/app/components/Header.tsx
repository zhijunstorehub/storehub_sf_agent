'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Aperture, Settings, ChevronDown, LayoutGrid, Zap, Cloud, BarChart2 } from 'lucide-react';
import Image from 'next/image';

const platforms = [
  { name: 'Salesforce', icon: '/salesforce-logo.svg', href: '/platform/salesforce' },
  { name: 'Chargebee', icon: '/chargebee-logo.svg', href: '/platform/chargebee' },
  { name: 'Redshift', icon: '/redshift-logo.svg', href: '/platform/redshift' },
  { name: 'AWS', icon: '/aws-logo.svg', href: '/platform/aws' },
];

const Header = () => {
  const [isPlatformsMenuOpen, setIsPlatformsMenuOpen] = useState(false);

  return (
    <header className="top-nav">
      <div className="top-nav-left">
        <Link href="/" className="logo">
          <Aperture size={20} />
          <span>Metadata Explorer</span>
        </Link>
        <nav className="main-nav">
          <Link href="/dashboard" className="nav-item">
            Dashboard
          </Link>
          <Link href="/platform" className="nav-item">
            Platforms
          </Link>
        </nav>
      </div>
      <div className="top-nav-right">
        <Link href="/settings" className="nav-item">
          <Settings size={18} />
        </Link>
      </div>
    </header>
  );
};

export default Header; 