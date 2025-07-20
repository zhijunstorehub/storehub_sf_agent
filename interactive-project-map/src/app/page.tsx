'use client';

import dynamic from 'next/dynamic';

// Dynamically import ProjectMap to avoid SSR issues with React Flow
const ProjectMap = dynamic(() => import('../components/ProjectMap'), {
  ssr: false,
  loading: () => (
    <div className="h-screen w-full bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center">
      <div className="text-white text-xl">Loading Interactive Project Map...</div>
    </div>
  )
});

export default function Home() {
  return (
    <div className="h-screen w-full">
      <ProjectMap />
    </div>
  );
}
