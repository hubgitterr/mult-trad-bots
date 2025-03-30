// Basic API client using fetch
import { supabase } from './supabaseClient'; // Import Supabase client

// Define the base URL for your backend API
// This should ideally come from an environment variable
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'; // Default to localhost:8000 for dev

/**
 * Generic fetch wrapper to handle requests and basic error handling.
 * Automatically adds Authorization header if user is logged in.
 * @param endpoint - The API endpoint path (e.g., '/market/klines')
 * @param options - Optional fetch options (method, headers, body, etc.)
 * @returns Promise<T> - The JSON response data
 * @throws Error if the network response is not ok
 */
async function apiClient<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  // Get the current session/token from Supabase
  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token;

  const defaultHeaders: HeadersInit = {
    'Content-Type': 'application/json',
  };

  // Add Authorization header if token exists
  if (token) {
    defaultHeaders['Authorization'] = `Bearer ${token}`;
  }

  const config: RequestInit = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers, // Allow overriding default headers
    },
  };

  try {
    const response = await fetch(url, config);

    if (!response.ok) {
      // Attempt to parse error details from the response body
      let errorData;
      try {
        errorData = await response.json();
      } catch (e) {
        // Ignore if response body is not JSON
      }
      // Handle specific auth error (e.g., 401 Unauthorized)
      if (response.status === 401) {
         console.error("API Client Error: Unauthorized. Token might be expired or invalid.");
         // Optionally trigger a sign-out or token refresh here
         // Example: await supabase.auth.signOut(); window.location.href = '/login';
      }
      const errorMessage = errorData?.detail || `HTTP error! status: ${response.status}`;
      throw new Error(errorMessage);
    }

    // Handle cases where the response might be empty (e.g., 204 No Content)
    if (response.status === 204) {
      return {} as T; // Or return null or undefined based on expected behavior
    }

    return await response.json() as T;
  } catch (error) {
    console.error('API Client Error:', error);
    // Re-throw the error so calling components can handle it
    throw error;
  }
}

export default apiClient;

// --- Specific API function examples ---

// Interface matching backend's KlineResponse schema
export interface KlineResponse {
    symbol: string;
    interval: string;
    klines: (string | number)[][]; // Array of arrays
}

// Interface matching backend's Ticker response (simple dict)
export interface TickerResponse {
    symbol: string;
    price: string;
    // Add other fields if needed based on actual Binance response
}

// Interface matching backend's BotConfiguration schema (adjust based on actual schema)
export interface BotConfiguration {
    id: number;
    user_id: string; // Assuming UUID comes as string
    bot_type: string;
    name: string;
    settings: Record<string, any>; // Or a more specific type
    is_active: boolean;
    created_at: string; // ISO date string
    updated_at?: string | null;
}

// Interface for creating a bot
export interface BotConfigurationCreate {
    bot_type: string;
    name: string;
    settings: Record<string, any>;
    is_active?: boolean; // Optional on create
}

// Interface for updating a bot
export interface BotConfigurationUpdate {
    name?: string;
    settings?: Record<string, any>;
    is_active?: boolean;
}

// Interface for bot status response
export interface BotStatusResponse {
    bot_id: number;
    bot_type: string;
    symbol: string;
    is_active: boolean;
    status: string;
    details: Record<string, any>;
}

// Interface for performance metrics response (adjust based on actual calculator output)
export interface PerformanceMetrics {
    total_trades_cycles?: number;
    winning_trades?: number;
    losing_trades?: number;
    win_rate_pct?: number;
    total_pnl?: number;
    average_pnl_per_cycle?: number;
    calculation_notes?: string;
    message?: string; // For cases like "No trades found"
}


// --- Market Data Functions ---
export const getKlines = (symbol: string, interval: string, limit: number = 100): Promise<KlineResponse> => {
    const params = new URLSearchParams({ symbol, interval, limit: String(limit) });
    // Public endpoint, doesn't strictly need auth, but apiClient handles it gracefully
    return apiClient<KlineResponse>(`/market/klines?${params.toString()}`);
};

export const getTicker = (symbol: string): Promise<TickerResponse> => {
    // Public endpoint
    return apiClient<TickerResponse>(`/market/ticker/${symbol}`);
};


// --- Bot Management Functions (Require Auth) ---
export const listBots = (): Promise<BotConfiguration[]> => {
    return apiClient<BotConfiguration[]>('/bots/');
};

export const getBot = (botId: number): Promise<BotConfiguration> => {
    return apiClient<BotConfiguration>(`/bots/${botId}`);
};

export const createBot = (botData: BotConfigurationCreate): Promise<BotConfiguration> => {
    return apiClient<BotConfiguration>('/bots/', {
        method: 'POST',
        body: JSON.stringify(botData),
    });
};

export const updateBot = (botId: number, botData: BotConfigurationUpdate): Promise<BotConfiguration> => {
    return apiClient<BotConfiguration>(`/bots/${botId}`, {
        method: 'PUT',
        body: JSON.stringify(botData),
    });
};

export const deleteBot = (botId: number): Promise<BotConfiguration> => { // Returns deleted bot info
    return apiClient<BotConfiguration>(`/bots/${botId}`, {
        method: 'DELETE',
    });
};

export const getBotStatus = (botId: number): Promise<BotStatusResponse> => {
    return apiClient<BotStatusResponse>(`/bots/${botId}/status`);
};

export const getBotPerformance = (botId: number): Promise<PerformanceMetrics> => {
    return apiClient<PerformanceMetrics>(`/bots/${botId}/performance`);
};
