import React, { createContext, useState, useEffect, useContext } from 'react';

const AuthContext = createContext();

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(localStorage.getItem('iva_token') || null);
  const [user, setUser] = useState(null);
  const [activeEmpresa, setActiveEmpresa] = useState(null); // { id, razon_social, nit, nrc }

  useEffect(() => {
    // In a real app, verify token and fetch user details here
    if (token) {
      let decodedId = null;
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        decodedId = payload.id;
      } catch (e) {
        console.error("No se pudo decodificar el token", e);
      }
      
      setUser({ 
        nombre: localStorage.getItem('iva_user_name') || 'Usuario',
        id: localStorage.getItem('iva_user_id') ? parseInt(localStorage.getItem('iva_user_id')) : decodedId
      });
      
      const storedEmpresa = localStorage.getItem('iva_active_empresa');
      if (storedEmpresa) {
        setActiveEmpresa(JSON.parse(storedEmpresa));
      }
    }
  }, [token]);

  const login = (newToken, userData) => {
    setToken(newToken);
    setUser(userData);
    localStorage.setItem('iva_token', newToken);
    localStorage.setItem('iva_user_name', userData.nombre);
    if (userData.id) localStorage.setItem('iva_user_id', userData.id);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    setActiveEmpresa(null);
    localStorage.removeItem('iva_token');
    localStorage.removeItem('iva_user_name');
    localStorage.removeItem('iva_user_id');
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
