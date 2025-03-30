'use client'; // Mark as a Client Component

import React, { useState, useEffect } from 'react';
import Layout from '@/components/Layout';
import CandlestickChart from '@/components/CandlestickChart'; // Import the chart component
import { getKlines, getTicker, KlineResponse, TickerResponse } from '@/lib/apiClient'; // Import API functions and types

export default function DashboardPage() {
  // State for data, loading, and errors
  const [klineData, setKlineData] = useState<KlineResponse | null>(null);
  const [tickerData, setTickerData] = useState<TickerResponse | null>(null); // Ticker state remains
  const [isLoadingKlines, setIsLoadingKlines] = useState<boolean>(true);
  const [isLoadingTicker, setIsLoadingTicker] = useState<boolean>(true); // Keep ticker loading until WS connects or initial fetch fails
  const [error, setError] = useState<string | null>(null);
  const [wsError, setWsError] = useState<string | null>(null); // Separate state for WS errors

  const symbol = 'BTCUSDT'; // Example symbol
  const interval = '1h';    // Example interval

  useEffect(() => {
    // Fetch initial Klines data
    const fetchKlineData = async () => {
      setIsLoadingKlines(true);
      setError(null); // Clear previous errors
      setWsError(null);
      try {
        const klines = await getKlines(symbol, interval, 100);
        setKlineData(klines);
      } catch (err: any) {
        console.error("Failed to fetch kline data:", err);
        setError(err.message || 'Failed to fetch chart data');
      } finally {
        setIsLoadingKlines(false);
      }
    };

    // Fetch initial Ticker data as a fallback in case WS fails immediately
    const fetchInitialTicker = async () => {
        setIsLoadingTicker(true);
        try {
            const ticker = await getTicker(symbol);
            // Only set if WS hasn't provided data yet
            setTickerData(current => current === null ? ticker : current);
        } catch (err: any) {
             console.error("Failed to fetch initial ticker data:", err);
             // Don't set main error, let WS try
             if (!tickerData) { // Only show error if WS hasn't connected either
                 setError(prev => prev ? `${prev}\nFailed to fetch initial ticker.` : 'Failed to fetch initial ticker.');
             }
        } finally {
             // Let WS connection handle setting loading to false ideally
             // setIsLoadingTicker(false);
        }
    };

    fetchKlineData();
    fetchInitialTicker(); // Fetch initial ticker once

    // --- WebSocket Connection for Ticker ---
    // Determine WebSocket URL (consider wss for production)
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Assuming backend runs on same host or use env var
    const backendHost = process.env.NEXT_PUBLIC_API_URL?.replace(/^http/, '') || '//localhost:8000';
    const wsUrl = `${wsProtocol}${backendHost}/api/v1/ws/market-updates/${symbol}`;

    let ws: WebSocket | null = null;
    let reconnectTimeout: NodeJS.Timeout | null = null;

    const connectWebSocket = () => {
      console.log(`Attempting to connect WebSocket to ${wsUrl}...`);
      ws = new WebSocket(wsUrl);
      setWsError(null); // Clear previous WS error on new attempt

      ws.onopen = () => {
        console.log(`WebSocket connected for ${symbol}`);
        setIsLoadingTicker(false); // Connected, stop initial loading indicator
        if (reconnectTimeout) {
          clearTimeout(reconnectTimeout);
          reconnectTimeout = null;
        }
      };

      ws.onmessage = (event) => {
        try {
          const messageData = JSON.parse(event.data);
          // Assuming the backend sends ticker data like: { s: 'BTCUSDT', c: 'PRICE' } (from Binance @ticker stream)
          if (messageData && messageData.s === symbol.toUpperCase() && messageData.c) {
             setTickerData({ symbol: messageData.s, price: messageData.c });
             setIsLoadingTicker(false); // Ensure loading is false on update
             setWsError(null); // Clear error on successful message
          } else {
              // console.warn("Received unexpected WS message format:", messageData);
          }
        } catch (e) {
          console.error("Failed to parse WebSocket message:", e);
          setWsError("Error processing real-time data.");
        }
      };

      ws.onerror = (error) => {
        console.error(`WebSocket error for ${symbol}:`, error);
        setWsError("WebSocket connection error.");
        // Don't set loading false here, as we might retry
      };

      ws.onclose = (event) => {
        console.log(`WebSocket disconnected for ${symbol}. Code: ${event.code}, Reason: ${event.reason}`);
        ws = null; // Clear the instance
        // Don't retry immediately if closed cleanly by server or client
        if (!event.wasClean && !reconnectTimeout) {
            console.log(`Attempting to reconnect WebSocket for ${symbol} in 5 seconds...`);
            setWsError("WebSocket disconnected. Attempting to reconnect...");
            setIsLoadingTicker(true); // Show loading while disconnected/reconnecting
            reconnectTimeout = setTimeout(connectWebSocket, 5000); // Retry after 5s
        } else if (event.wasClean) {
             setWsError("WebSocket connection closed.");
             setIsLoadingTicker(false); // Stop loading if closed cleanly
        }
      };
    };

    connectWebSocket(); // Initial connection attempt

    // Cleanup function: close WebSocket and clear timeout on component unmount
    return () => {
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
      if (ws) {
        console.log(`Closing WebSocket for ${symbol}`);
        ws.onclose = null; // Prevent reconnect logic on manual close
        ws.close();
        ws = null;
      }
    };

  }, [symbol, interval]); // Dependencies for initial fetch and WS setup

  return (
    <Layout>
      <div>
        <h1 className="text-2xl font-semibold text-gray-800 mb-4">Dashboard ({symbol})</h1>

        {/* Ticker Display */}
        <div className="mb-6 p-4 bg-white rounded shadow">
          <h2 className="text-lg font-semibold mb-2">Current Price</h2>
          {isLoadingTicker && <p>Loading price...</p>}
          {tickerData && <p className="text-3xl font-bold">{parseFloat(tickerData.price).toFixed(2)} USDT</p>}
          {!isLoadingTicker && !tickerData && !error && !wsError && <p>Could not load ticker price.</p>}
          {wsError && <p className="text-sm text-red-500">{wsError}</p>}
        </div>

        {/* Kline Chart */}
        <div className="mb-6 p-4 bg-white rounded shadow">
          <h2 className="text-lg font-semibold mb-2">Price Chart ({interval})</h2>
          {isLoadingKlines && <p className="text-center p-4">Loading chart data...</p>}
          {!isLoadingKlines && klineData && klineData.klines.length > 0 && (
            <CandlestickChart chartData={klineData} />
          )}
          {!isLoadingKlines && klineData && klineData.klines.length === 0 && (
            <p className="text-center p-4">No kline data available for {symbol} {interval}.</p>
          )}
          {!isLoadingKlines && !klineData && !error && <p className="text-center p-4 text-red-500">Could not load chart data.</p>}
        </div>

        {/* General Error Display */}
        {error && (
          <div className="p-4 bg-red-100 text-red-700 rounded shadow">
            <h2 className="text-lg font-semibold mb-2">Error</h2>
            <p>{error}</p>
          </div>
        )}

      </div>
    </Layout>
  );
}
