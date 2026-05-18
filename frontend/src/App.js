import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import StudentDashboard from './pages/StudentDashboard';
import LecturerDashboard from './pages/LecturerDashboard';

const BACKEND_BASE = (
  process.env.REACT_APP_API_BASE
  || (
    typeof window !== 'undefined' && ['localhost', '127.0.0.1'].includes(window.location.hostname)
      ? 'http://localhost:8000'
      : 'https://studentattendancetrackingsystem-production-7589.up.railway.app'
  )
).replace(/\/$/, '');

function ExternalRedirect({ to }) {
  useEffect(() => {
    window.location.replace(to);
  }, [to]);

  return <p>Redirecting...</p>;
}

function ProtectedRoute({ children, requiredRole }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <p>Loading…</p>;
  }

  if (!user) {
    return <ExternalRedirect to={`${BACKEND_BASE}/login/`} />;
  }

  if (requiredRole && user.user_type !== requiredRole) {
    return <ExternalRedirect to={`${BACKEND_BASE}/login/`} />;
  }

  return children;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<ExternalRedirect to={`${BACKEND_BASE}/login/`} />} />
          <Route path="/login" element={<ExternalRedirect to={`${BACKEND_BASE}/login/`} />} />
          <Route
            path="/student"
            element={
              <ProtectedRoute requiredRole="Student">
                <StudentDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/lecturer"
            element={
              <ProtectedRoute requiredRole="Lecturer">
                <LecturerDashboard />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<ExternalRedirect to={`${BACKEND_BASE}/login/`} />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
