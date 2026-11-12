import React, { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AssistantProvider } from './contexts/AssistantContext';
import Avatar from './components/Avatar';
import AppShell from './components/AppShell';

const Login = lazy(() => import('./pages/Login'));
const Registro = lazy(() => import('./pages/Registro'));
const Terminos = lazy(() => import('./pages/Terminos'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Anexos = lazy(() => import('./pages/Anexos'));
const Configuracion = lazy(() => import('./pages/Configuracion'));
const AnexoCompras = lazy(() => import('./pages/AnexoCompras'));
const AnexoVentasCF = lazy(() => import('./pages/AnexoVentasCF'));
const AnexoVentasContribuyentes = lazy(() => import('./pages/AnexoVentasContribuyentes'));
const AnexoAnulados = lazy(() => import('./pages/AnexoAnulados'));
const AnexoRetenciones = lazy(() => import('./pages/AnexoRetenciones'));
const Liquidacion = lazy(() => import('./pages/Liquidacion'));

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

function RouteFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#f3f4f6] px-4">
      <div role="status" aria-live="polite" className="flex flex-col items-center gap-3">
        <div className="h-9 w-9 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
        <p className="text-sm font-medium text-slate-500">Cargando módulo…</p>
      </div>
    </div>
  );
}

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

      <Route path="/anexos" element={
        <ProtectedRoute>
          <Anexos />
        </ProtectedRoute>
      } />

      <Route path="/configuracion" element={
        <ProtectedRoute>
          <Configuracion />
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
            <AppShell>
              <Suspense fallback={<RouteFallback />}>
                <AppRoutes />
              </Suspense>
            </AppShell>
            <Avatar />
          </Router>
        </AssistantProvider>
      </AuthProvider>
    </GoogleOAuthProvider>
  );
}

export default App;
