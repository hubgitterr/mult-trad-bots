'use client'; // Layout now needs client-side hooks (useRouter)

import React, { ReactNode } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabaseClient';

interface LayoutProps {
  children: ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const router = useRouter();

  const handleLogout = async () => {
    const { error } = await supabase.auth.signOut();
    if (error) {
      console.error('Error logging out:', error);
      // Optionally show an error message to the user
    } else {
      // Redirect to login page after successful logout
      router.push('/login');
      // router.refresh(); // Optional refresh
    }
  };

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-800 text-white flex flex-col">
        <div className="p-4 border-b border-gray-700">
          <h1 className="text-2xl font-semibold">Trading Bots</h1>
        </div>
        <nav className="flex-1 p-4 space-y-2">
          <Link href="/dashboard" className="block px-4 py-2 rounded hover:bg-gray-700">
              Dashboard
          </Link>
          <Link href="/bots" className="block px-4 py-2 rounded hover:bg-gray-700">
              Bots
          </Link>
          <Link href="/settings" className="block px-4 py-2 rounded hover:bg-gray-700">
              Settings
          </Link>
          {/* Add more links as needed */}
          <button
            onClick={handleLogout}
            className="w-full text-left px-4 py-2 rounded text-red-300 hover:bg-red-700 hover:text-white focus:outline-none"
          >
            Logout
          </button>
        </nav>
        <div className="p-4 border-t border-gray-700">
          {/* Footer or user info can go here */}
          <p className="text-sm text-gray-400">© 2025 Trading Inc.</p>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Optional Header */}
        <header className="bg-white shadow-md p-4">
          <h2 className="text-xl font-semibold text-gray-800">Page Title Placeholder</h2>
        </header>
        {/* Content */}
        <div className="flex-1 p-6 overflow-y-auto">
          {children}
        </div>
      </main>
    </div>
  );
};

export default Layout;
