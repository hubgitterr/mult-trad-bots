import { createBrowserClient } from '@supabase/ssr'; // Use browser client for frontend

// Fetch Supabase URL and Anon Key from environment variables
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase environment variables (NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY)');
}

// Create and export the Supabase client instance
// This client can be used in client components and client-side logic.
// For server components/actions, you might use createServerClient from @supabase/ssr
export const supabase = createBrowserClient(
  supabaseUrl,
  supabaseAnonKey
);
