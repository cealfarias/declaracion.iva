import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AssistantProvider } from './contexts/AssistantContext';
import Login from './pages/Login';
import Registro from './pages/Registro';
import Avatar from './components/Avatar';
import AppShell from './components/AppShell';

import Terminos from './pages/Terminos';
import Dashboard from './pages/Dashboard';
import AnexoCompras from './pages/AnexoCompras';
import AnexoVentasCF from './pages/AnexoVentasCF';
import AnexoVentasContribuyentes from './pages/AnexoVentasContribuyentes';
import AnexoAnulados from './pages/AnexoAnulados';
import AnexoRetenciones from './pages/AnexoRetenciones';
import Liquidacion from './pages/Liquidacion';

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
      <Route path="/liquidacion" element={
        <ProtectedRoute>
          <Liquidacion />
        </ProtectedRoute>
      } />
      <Route path="/" element={<Navigate to="/login" />} />
      <Route path="/login" element={<Login />} />
      <Route path="/registro" element={<Registro />} />
      
      <Route path="/terminos" element={<Terminos />} />
      
      <Route path="/dashboard" element={
        <ProtectedRoute>
          <Dashboard />
        </ProtectedRoute>
      } />
      
      <Route path="/compras" element={
        <ProtectedRoute>
          <AnexoCompras />
        </ProtectedRoute>
      } />

      <Route path="/consumidor-final" element={
        <ProtectedRoute>
          <AnexoVentasCF />
        </ProtectedRoute>
      } />

      <Route path="/ventas-contribuyentes" element={
        <ProtectedRoute>
          <AnexoVentasContribuyentes />
        </ProtectedRoute>
      } />

      <Route path="/anulados" element={
        <ProtectedRoute>
          <AnexoAnulados />
        </ProtectedRoute>
      } />

      <Route path="/retenciones" element={
        <ProtectedRoute>
          <AnexoRetenciones />
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
            <AppShell><AppRoutes /></AppShell>
            <Avatar />
          </Router>
        </AssistantProvider>
      </AuthProvider>
    </GoogleOAuthProvider>
  );
}

export default App;
