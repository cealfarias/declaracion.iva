import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './pages/Login';

// Placeholder for other components we will build
const Dashboard = () => <div className="p-8 text-2xl">Dashboard Próximamente...</div>;
const SeleccionEmpresa = () => <div className="p-8 text-2xl">Selección de Empresa Próximamente...</div>;
const Registro = () => <div className="p-8 text-2xl">Registro Próximamente...</div>;

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
    <GoogleOAuthProvider clientId="520602063183-02kdfek3f8vp2g146j2khacmhj4nbn6a.apps.googleusercontent.com">
      <AuthProvider>
        <Router>
          <AppRoutes />
        </Router>
      </AuthProvider>
    </GoogleOAuthProvider>
  );
}

export default App;
