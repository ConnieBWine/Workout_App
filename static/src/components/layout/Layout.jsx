import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';

// Layout components
import Layout from './components/layout/Layout';

// Pages
import Dashboard from './pages/Dashboard';
import ExerciseTracker from './pages/ExerciseTracker';
import WorkoutPlanner from './pages/WorkoutPlanner';
import WorkoutHistory from './pages/WorkoutHistory';
import AIChat from './pages/AIChat';
import Profile from './pages/Profile';

// Context providers
import { WorkoutProvider } from './context/WorkoutContext';

// Initialize React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000,
    },
  },
});

/**
 * Main application component that sets up routing and global providers
 * 
 * This component initializes the React Router for navigation, 
 * sets up global context providers, and defines all application routes.
 */
function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <WorkoutProvider>
        <Router>
          <Routes>
            <Route path="/" element={<Layout />}>
              {/* Dashboard/home page */}
              <Route index element={<Dashboard />} />
              
              {/* Exercise tracking */}
              <Route path="exercise" element={<ExerciseTracker />} />
              
              {/* Workout planning */}
              <Route path="workout">
                <Route index element={<WorkoutPlanner />} />
                <Route path=":planId" element={<WorkoutPlanner />} />
              </Route>
              
              {/* History and stats */}
              <Route path="history" element={<WorkoutHistory />} />
              
              {/* AI chat interface */}
              <Route path="ai-chat" element={<AIChat />} />
              
              {/* User profile */}
              <Route path="profile" element={<Profile />} />
            </Route>
          </Routes>
        </Router>
      </WorkoutProvider>
    </QueryClientProvider>
  );
}

export default App;