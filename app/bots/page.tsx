'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import Layout from '@/components/Layout';
import { useAuth } from '@/context/AuthContext'; // Use auth context
import { listBots, deleteBot, BotConfiguration } from '@/lib/apiClient'; // Import API functions and type

export default function BotsPage() {
  const { user, loading: authLoading } = useAuth(); // Get user and loading state
  const [bots, setBots] = useState<BotConfiguration[]>([]);
  const [loadingBots, setLoadingBots] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null); // Separate error state for delete

  const fetchBots = async () => {
      setLoadingBots(true);
      setError(null);
      setDeleteError(null); // Clear delete error on refresh
      try {
        const fetchedBots = await listBots();
        setBots(fetchedBots);
      } catch (err: any) {
        console.error("Failed to fetch bots:", err);
        setError(err.message || 'Failed to load bot configurations.');
      } finally {
        setLoadingBots(false);
      }
    };

  useEffect(() => {
    // Fetch bots only if user is loaded and authenticated
    if (!authLoading && user) {
      const fetchBots = async () => {
        setLoadingBots(true);
        setError(null);
        try {
          const fetchedBots = await listBots();
          setBots(fetchedBots);
        } catch (err: any) {
          console.error("Failed to fetch bots:", err);
          setError(err.message || 'Failed to load bot configurations.');
        } finally {
          setLoadingBots(false);
        }
      };
      fetchBots(); // Initial fetch
    } else if (!authLoading && !user) {
      // Handle case where user is definitely not logged in (though middleware should prevent this)
      setLoadingBots(false);
      setError("Please log in to manage bots.");
    }
    // We don't strictly need user/authLoading as dependencies if fetchBots is stable,
    // but it ensures re-fetch on login/logout if needed.
  }, [user, authLoading]);

  const handleDelete = async (botId: number, botName: string) => {
      setDeleteError(null); // Clear previous delete errors
      if (!confirm(`Are you sure you want to delete the bot "${botName}"? This action cannot be undone.`)) {
          return;
      }

      try {
          await deleteBot(botId);
          // Refresh the list after successful deletion
          setBots(prevBots => prevBots.filter(b => b.id !== botId));
          // Optionally show a success message
      } catch (err: any) {
          console.error(`Failed to delete bot ${botId}:`, err);
          setDeleteError(`Failed to delete bot "${botName}": ${err.message}`);
      }
  };


  return (
    <Layout>
      <div>
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-semibold text-gray-800">Manage Bots</h1>
          {/* Link to a future 'Create Bot' page */}
          <Link href="/bots/new" className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
              + Create New Bot
          </Link>
        </div>

        {/* Loading and Error States */}
        {authLoading && <p>Loading authentication...</p>}
        {loadingBots && !authLoading && <p>Loading bots...</p>}
        {error && <p className="text-red-600">Error loading bots: {error}</p>}
        {deleteError && <p className="text-red-600 mt-2">Error deleting bot: {deleteError}</p>}


        {/* Bot List */}
        {!loadingBots && !error && bots.length === 0 && (
          <p className="text-gray-500">You haven't configured any bots yet.</p>
        )}
        {!loadingBots && !error && bots.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {bots.map((bot) => (
              <div key={bot.id} className="bg-white p-4 rounded shadow border border-gray-200">
                <h2 className="text-lg font-semibold mb-2">{bot.name}</h2>
                <p className="text-sm text-gray-600 mb-1">Type: <span className="font-medium">{bot.bot_type}</span></p>
                <p className="text-sm text-gray-600 mb-3">Status:
                  <span className={`ml-2 px-2 py-0.5 rounded text-xs font-semibold ${bot.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                    {bot.is_active ? 'Active' : 'Inactive'}
                  </span>
                </p>
                {/* Add placeholder links/buttons for details/edit/delete */}
                <div className="flex space-x-2 mt-4">
                   <Link href={`/bots/${bot.id}/details`} className="text-sm text-indigo-600 hover:text-indigo-800">Details</Link>
                   <Link href={`/bots/${bot.id}/edit`} className="text-sm text-blue-600 hover:text-blue-800">Edit</Link>
                   {/* Delete button triggers handleDelete */}
                   <button
                     onClick={() => handleDelete(bot.id, bot.name)}
                     className="text-sm text-red-600 hover:text-red-800"
                   >
                     Delete
                   </button>
                 </div>
               </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
