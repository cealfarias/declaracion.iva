import React, { createContext, useState, useContext } from 'react';

const AuthContext = createContext();

export function useAuth() {
  return useContext(AuthContext);
}

// TEMPORAL: habilita una sesión de demostración para revisar el diseño en
// previews de Vercel. No autentica contra el backend ni concede acceso a datos.
// Se oculta en el dominio de producción conocido y puede forzarse con
// VITE_ENABLE_TEST_BYPASS=true. Eliminar cuando termine la revisión visual.
export function canUseDemoBypass() {
  if (import.meta.env.VITE_ENABLE_TEST_BYPASS === 'true') return true;
  const hostname = window.location.hostname;
  if (hostname === 'demiempresa.vercel.app') return false;
  return (
    hostname === 'localhost' ||
    hostname === '127.0.0.1' ||
    hostname.endsWith('.vercel.app')
  );
}

function readStoredUser() {
  const storedToken = localStorage.getItem('iva_token');
  if (!storedToken) return null;

  let decodedId = null;
  try {
    const payload = JSON.parse(atob(storedToken.split('.')[1]));
    decodedId = payload.id;
  } catch (error) {
    console.error('No se pudo decodificar el token', error);
  }

  const storedId = localStorage.getItem('iva_user_id');
  return {
    nombre: localStorage.getItem('iva_user_name') || 'Usuario',
    id: storedId ? parseInt(storedId, 10) : decodedId,
    terminos_aceptados: localStorage.getItem('iva_terminos_aceptados') === 'true',
  };
}

function readStoredEmpresa() {
  const storedEmpresa = localStorage.getItem('iva_active_empresa');
  if (!storedEmpresa) return null;
  try {
    return JSON.parse(storedEmpresa);
  } catch (error) {
    console.error('No se pudo leer la empresa activa', error);
    return null;
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(localStorage.getItem('iva_token') || null);
  // Hidratación síncrona: evita que un refresh en una vista protegida redirija
  // al dashboard antes de recuperar la empresa activa.
  const [user, setUser] = useState(readStoredUser);
  const [activeEmpresa, setActiveEmpresa] = useState(readStoredEmpresa);
  const [demoMode, setDemoMode] = useState(
    () => localStorage.getItem('iva_demo_mode') === 'true'
  );

  const login = (newToken, userData) => {
    setDemoMode(false);
    localStorage.removeItem('iva_demo_mode');
    setToken(newToken);
    setUser(userData);
    localStorage.setItem('iva_token', newToken);
    localStorage.setItem('iva_user_name', userData.nombre);
    if (userData.id) localStorage.setItem('iva_user_id', userData.id);
    if (userData.terminos_aceptados !== undefined) {
      localStorage.setItem('iva_terminos_aceptados', userData.terminos_aceptados);
    }
  };

  const loginDemo = () => {
    const payload = btoa(
      JSON.stringify({ id: 999999, exp: Math.floor(Date.now() / 1000) + 60 * 60 * 8 })
    );
    const demoToken = `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.${payload}.demo`;
    const demoUser = {
      nombre: 'Usuario de Prueba',
      id: 999999,
      terminos_aceptados: true,
    };
    const demoEmpresa = {
      id: 999999,
      razon_social: 'Empresa Demo, S.A. de C.V.',
      nit: '0000-000000-000-0',
      nrc: '000000-0',
    };

    login(demoToken, demoUser);
    selectEmpresa(demoEmpresa);
    setDemoMode(true);
    localStorage.setItem('iva_demo_mode', 'true');
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    setActiveEmpresa(null);
    setDemoMode(false);
    localStorage.removeItem('iva_token');
    localStorage.removeItem('iva_user_name');
    localStorage.removeItem('iva_user_id');
    localStorage.removeItem('iva_terminos_aceptados');
    localStorage.removeItem('iva_active_empresa');
    localStorage.removeItem('iva_demo_mode');
  };

  const selectEmpresa = (empresa) => {
    setActiveEmpresa(empresa);
    localStorage.setItem('iva_active_empresa', JSON.stringify(empresa));
  };

  return (
    <AuthContext.Provider value={{ token, user, activeEmpresa, demoMode, login, loginDemo, logout, selectEmpresa }}>
      {children}
    </AuthContext.Provider>
  );
}
