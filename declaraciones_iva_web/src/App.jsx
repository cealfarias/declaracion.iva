import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AssistantProvider } from './contexts/AssistantContext';
import Login from './pages/Login';
import Registro from './pages/Registro';
import Avatar from './components/Avatar';

import Terminos from './pages/Terminos';
import Dashboard from './pages/Dashboard';

const ProtectedRoute = ({ children, requireTerms = true }) => {
  const { token, user } = useAuth();
  if (!token) return <Navigate to="/login" />;
  
  if (requireTerms && user && user.terminos_aceptados !== true) {
    return <Navigate to="/terminos" state={{ fromGuard: true }} />;
  }
  
  if (!requireTerms && user && user.terminos_aceptados === true) {
    return <Navigate to="/dashboard" />;
  }

  return children;
};

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" />} />
      <Route path="/login" element={<Login />} />
      <Route path="/registro" element={<Registro />} />
      
      <Route path="/terminos" element={<Terminos />} />
      
      <Route path="/dashboard" element={
        <ProtectedRoute>
          <Dashboard />
        </ProtectedRoute>
      } />
    </Routes>
  );
}

function App() {
  return (
    <GoogleOAuthProvider clientId="231508841464-22ln2h2p8k524lb6njdqmsk7s9e9bvl7.apps.googleusercontent.com">
      <AuthProvider>
        <AssistantProvider>
          <Router>
            <AppRoutes />
            <Avatar />
          </Router>
        </AssistantProvider>
      </AuthProvider>
    </GoogleOAuthProvider>
  );
}

export default App;
