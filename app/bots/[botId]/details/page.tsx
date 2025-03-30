'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import Layout from '@/components/Layout';
import { useAuth } from '@/context/AuthContext';
import { getBot, getBotStatus, updateBot, deleteBot, getBotPerformance, BotConfiguration, BotStatusResponse, PerformanceMetrics } from '@/lib/apiClient'; // Added getBotPerformance, PerformanceMetrics
import { format } from 'date-fns';

export default function BotDetailsPage() {
  const { user, loading: authLoading } = useAuth();
  const params = useParams();
  const router = useRouter();
  const botId = parseInt(params.botId as string, 10);

  const [bot, setBot] = useState<BotConfiguration | null>(null);
  const [status, setStatus] = useState<BotStatusResponse | null>(null);
  const [performance, setPerformance] = useState<PerformanceMetrics | null>(null); // State for performance
  const [loadingDetails, setLoadingDetails] = useState(true);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [loadingPerformance, setLoadingPerformance] = useState(true); // Loading state for performance
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // Use useCallback to memoize fetchData function
  const fetchData = useCallback(async () => {
    if (isNaN(botId) || !user) {
      setLoadingDetails(false);
      setLoadingStatus(false);
      setLoadingPerformance(false);
      return;
    }
    setLoadingDetails(true);
    setLoadingStatus(true);
    setLoadingPerformance(true);
    setError(null);
    setActionError(null);
    try {
      // Fetch all data concurrently
      const [fetchedBot, fetchedStatus, fetchedPerformance] = await Promise.all([
        getBot(botId),
        getBotStatus(botId),
        getBotPerformance(botId) // Fetch performance data
      ]);

      setBot(fetchedBot);
      setStatus(fetchedStatus);
      setPerformance(fetchedPerformance);

    } catch (err: any) {
      console.error("Failed to fetch bot details, status, or performance:", err);
      setError(err.message || 'Failed to load bot data.');
    } finally {
        setLoadingDetails(false);
        setLoadingStatus(false);
        setLoadingPerformance(false);
    }
  }, [botId, user]); // Dependencies for useCallback

  useEffect(() => {
    if (isNaN(botId)) {
      setError("Invalid Bot ID.");
      setLoadingDetails(false);
      setLoadingStatus(false);
      setLoadingPerformance(false);
      return; // Exit early
    }

    if (!authLoading && user) {
      fetchData(); // Call the memoized fetch function
    } else if (!authLoading && !user) {
      setLoadingDetails(false);
      setLoadingStatus(false);
      setLoadingPerformance(false);
      setError("Please log in to view bot details.");
    }
  }, [user, authLoading, botId, router, fetchData]); // Include fetchData

  const renderSettings = (settings: Record<string, any>) => {
    return Object.entries(settings).map(([key, value]) => (
      <p key={key} className="text-sm"><span className="font-medium capitalize">{key.replace(/_/g, ' ')}:</span> {JSON.stringify(value)}</p>
    ));
  };

  const renderStatusDetails = (details: Record<string, any>) => {
    if (!details || Object.keys(details).length === 0) return <p className="text-sm italic">No specific details available.</p>;
    if (details.signal) {
      return <p className="text-lg font-bold">Signal: <span className={details.signal === 'BUY' ? 'text-green-600' : details.signal === 'SELL' ? 'text-red-600' : 'text-gray-600'}>{details.signal}</span></p>;
    }
    if (details.potential_actions) {
      return (
        <div>
          <p className="text-sm font-medium mb-1">Potential Actions:</p>
          {details.potential_actions.length > 0 ? (
            <ul className="list-disc list-inside text-sm">
              {details.potential_actions.map((action: any, index: number) => (
                <li key={index}>{action.action} {action.amount ? `(${action.amount})` : ''} @ ~{action.price?.toFixed(2)}</li>
              ))}
            </ul>
          ) : <p className="text-sm italic">None</p>}
        </div>
      );
    }
    return <pre className="text-xs bg-gray-100 p-2 rounded overflow-x-auto">{JSON.stringify(details, null, 2)}</pre>;
  };

   const renderPerformance = (perf: PerformanceMetrics | null) => {
     if (!perf) return <p className="text-sm italic">No performance data available.</p>;
     if (perf.message) return <p className="text-sm italic">{perf.message}</p>;

     return (
       <div className="space-y-1 text-sm">
         <p><span className="font-medium">Total Cycles:</span> {perf.total_trades_cycles ?? 'N/A'}</p>
         <p><span className="font-medium">Wins:</span> {perf.winning_trades ?? 'N/A'}</p>
         <p><span className="font-medium">Losses:</span> {perf.losing_trades ?? 'N/A'}</p>
         <p><span className="font-medium">Win Rate:</span> {perf.win_rate_pct ?? 'N/A'}%</p>
         <p><span className="font-medium">Total PnL:</span> {perf.total_pnl?.toFixed(4) ?? 'N/A'}</p>
         <p><span className="font-medium">Avg PnL/Cycle:</span> {perf.average_pnl_per_cycle?.toFixed(4) ?? 'N/A'}</p>
         {perf.calculation_notes && <p className="text-xs text-gray-500 mt-2"><i>Note: {perf.calculation_notes}</i></p>}
       </div>
     );
   };


  // Handler for toggling active status
  const handleToggleActive = async () => {
    if (!bot) return;
    setActionLoading(true);
    setActionError(null);
    try {
      const updatedBot = await updateBot(bot.id, { is_active: !bot.is_active });
      setBot(updatedBot); // Update local state with the response
    } catch (err: any) {
      console.error("Failed to toggle bot status:", err);
      setActionError(`Failed to update status: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  // Handler for deleting the bot
  const handleDeleteBot = async () => {
    if (!bot) return;
    if (!confirm(`Are you sure you want to delete the bot "${bot.name}"? This action cannot be undone.`)) {
      return;
    }
    setActionLoading(true);
    setActionError(null);
    try {
      await deleteBot(bot.id);
      router.push('/bots');
    } catch (err: any) {
      console.error("Failed to delete bot:", err);
      setActionError(`Failed to delete bot: ${err.message}`);
      setActionLoading(false);
    }
  };

  return (
    <Layout>
      <div>
        <Link href="/bots" className="text-indigo-600 hover:text-indigo-800 mb-4 inline-block">&larr; Back to Bots List</Link>

        {authLoading && <p>Loading authentication...</p>}
        {(loadingDetails || loadingStatus || loadingPerformance) && !authLoading && <p>Loading bot data...</p>}
        {error && <p className="text-red-600">Error: {error}</p>}

        {!loadingDetails && !error && bot && (
          <div className="bg-white p-6 rounded shadow border border-gray-200">
            {/* Header */}
            <div className="flex justify-between items-start mb-4">
              <div>
                <h1 className="text-2xl font-semibold text-gray-800 mb-1">{bot.name}</h1>
                <p className="text-sm text-gray-500">ID: {bot.id} | Type: {bot.bot_type}</p>
              </div>
              <span className={`px-3 py-1 rounded-full text-sm font-semibold ${bot.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                {bot.is_active ? 'Active' : 'Inactive'}
              </span>
            </div>

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Configuration Details */}
              <div className="md:col-span-1 border-t md:border-t-0 md:border-r border-gray-200 pt-4 md:pt-0 md:pr-6">
                <h2 className="text-lg font-semibold mb-2">Configuration</h2>
                {renderSettings(bot.settings)}
                <p className="text-sm mt-2"><span className="font-medium">Created:</span> {format(new Date(bot.created_at), 'PPpp')}</p>
                {bot.updated_at && <p className="text-sm"><span className="font-medium">Updated:</span> {format(new Date(bot.updated_at), 'PPpp')}</p>}
              </div>

              {/* Current Status */}
              <div className="md:col-span-1 border-t md:border-t-0 md:border-r border-gray-200 pt-4 md:pt-0 md:pr-6">
                <h2 className="text-lg font-semibold mb-2">Current Status</h2>
                {loadingStatus && <p>Loading status...</p>}
                {!loadingStatus && status && renderStatusDetails(status.details)}
                {!loadingStatus && !status && <p className="text-sm text-red-500">Could not load status.</p>}
              </div>

               {/* Performance Metrics */}
               <div className="md:col-span-1 border-t md:border-t-0 border-gray-200 pt-4 md:pt-0">
                 <h2 className="text-lg font-semibold mb-2">Performance</h2>
                 {loadingPerformance && <p>Loading performance...</p>}
                 {!loadingPerformance && renderPerformance(performance)}
                 {!loadingPerformance && !performance && <p className="text-sm text-red-500">Could not load performance data.</p>}
                 {/* TODO: Add PnL Chart */}
               </div>
            </div>

            {/* Action Buttons */}
            <div className="mt-6 pt-4 border-t border-gray-200 flex space-x-3">
              <Link href={`/bots/${bot.id}/edit`} className={`px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm ${actionLoading ? 'opacity-50 cursor-not-allowed' : ''}`}>Edit</Link>
              <button
                onClick={handleToggleActive}
                disabled={actionLoading}
                className={`px-4 py-2 text-white rounded text-sm ${
                  bot.is_active
                    ? 'bg-yellow-500 hover:bg-yellow-600'
                    : 'bg-green-500 hover:bg-green-600'
                } disabled:opacity-50`}
              >
                {actionLoading ? 'Updating...' : (bot.is_active ? 'Deactivate' : 'Activate')}
              </button>
              <button
                onClick={handleDeleteBot}
                disabled={actionLoading}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 text-sm disabled:opacity-50"
              >
                {actionLoading ? 'Deleting...' : 'Delete'}
              </button>
            </div>
            {actionError && <p className="text-red-600 mt-2 text-sm">Error: {actionError}</p>}

          </div>
        )}
        {!loadingDetails && !error && !bot && (
          <p>Bot not found.</p> // Should be caught by error handling usually
        )}
      </div>
    </Layout>
  );
}
