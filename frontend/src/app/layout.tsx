'use client';

import "./globals.css";
import React from 'react';
import Header from './components/Header'; // Import the new Header component

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <div className="app-container">
          <Header />
          <main className="main-content">
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
