import React, { createContext, useState, useContext } from 'react';

const AuthContext = createContext();

export function useAuth() {
  return useContext(AuthContext);
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

  const login = (newToken, userData) => {
    setToken(newToken);
    setUser(userData);
    localStorage.setItem('iva_token', newToken);
    localStorage.setItem('iva_user_name', userData.nombre);
    if (userData.id) localStorage.setItem('iva_user_id', userData.id);
    if (userData.terminos_aceptados !== undefined) {
      localStorage.setItem('iva_terminos_aceptados', userData.terminos_aceptados);
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    setActiveEmpresa(null);
    localStorage.removeItem('iva_token');
    localStorage.removeItem('iva_user_name');
    localStorage.removeItem('iva_user_id');
    localStorage.removeItem('iva_terminos_aceptados');
    localStorage.removeItem('iva_active_empresa');
  };

  const selectEmpresa = (empresa) => {
    setActiveEmpresa(empresa);
    localStorage.setItem('iva_active_empresa', JSON.stringify(empresa));
  };

  return (
    <AuthContext.Provider value={{ token, user, activeEmpresa, login, logout, selectEmpresa }}>
      {children}
    </AuthContext.Provider>
  );
}
