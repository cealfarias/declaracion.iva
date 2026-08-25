import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AssistantProvider } from './contexts/AssistantContext';
import Login from './pages/Login';
import SeleccionEmpresa from './pages/SeleccionEmpresa';
import Registro from './pages/Registro';
import Avatar from './components/Avatar';

import Dashboard from './pages/Dashboard';

const ProtectedRoute = ({ children }) => {
  const { token } = useAuth();
  if (!token) return <Navigate to="/login" />;
  return children;
};

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" />} />
      <Route path="/login" element={<Login />} />
      <Route path="/registro" element={<Registro />} />
      
      <Route path="/empresas" element={
        <ProtectedRoute>
          <SeleccionEmpresa />
        </ProtectedRoute>
      } />
      
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
