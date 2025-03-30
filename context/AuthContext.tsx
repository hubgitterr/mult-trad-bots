'use client';

import React, { createContext, useState, useEffect, useContext, ReactNode } from 'react';
import { Session, User } from '@supabase/supabase-js';
import { supabase } from '@/lib/supabaseClient'; // Import your Supabase client

// Define the shape of the context data
interface AuthContextType {
  session: Session | null;
  user: User | null;
  loading: boolean;
  signOut: () => Promise<void>; // Add signOut method for convenience
}

// Create the context with a default value (null or undefined)
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Create the provider component
interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true); // Start loading until initial check is done

  useEffect(() => {
    // Function to get the initial session
    const getInitialSession = async () => {
      const { data: { session: initialSession }, error } = await supabase.auth.getSession();
      if (error) {
        console.error("Error getting initial session:", error);
      }
      setSession(initialSession);
      setUser(initialSession?.user ?? null);
      setLoading(false); // Initial check complete
    };

    getInitialSession();

    // Set up a listener for auth state changes (login, logout, token refresh)
    const { data: authListener } = supabase.auth.onAuthStateChange((event, newSession) => {
      console.log('Auth state changed:', event, newSession);
      setSession(newSession);
      setUser(newSession?.user ?? null);
      // If loading was true, set it to false after the first event if needed
      if (loading) setLoading(false);
    });

    // Cleanup function to unsubscribe from the listener when the component unmounts
    return () => {
      authListener?.subscription.unsubscribe();
    };
  }, [loading]); // Rerun effect if loading state changes (though primarily runs once)

  // Sign out function
  const signOut = async () => {
    setLoading(true); // Optional: show loading state during sign out
    const { error } = await supabase.auth.signOut();
    if (error) {
      console.error("Error signing out:", error);
      // Handle error appropriately
    }
    // State will be updated by onAuthStateChange listener
    setLoading(false);
  };

  // Value object provided by the context
  const value = {
    session,
    user,
    loading,
    signOut,
  };

  // Render children only after initial loading is complete? Or show loading state?
  // For now, render children immediately, components can check loading state.
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Custom hook to easily consume the context
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
