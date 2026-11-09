import React, { useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Bars3Icon, XMarkIcon, BuildingOffice2Icon, HomeIcon,
  ShoppingBagIcon, DocumentTextIcon, ReceiptPercentIcon,
  NoSymbolIcon, CalculatorIcon, ArrowRightStartOnRectangleIcon
} from '@heroicons/react/24/outline';

const items = [
  { label: 'Panel principal', to: '/dashboard', icon: HomeIcon },
  { label: 'Compras', to: '/compras', icon: ShoppingBagIcon, periodo: true },
  { label: 'Ventas consumidor final', to: '/consumidor-final', icon: ReceiptPercentIcon, periodo: true },
  { label: 'Ventas contribuyentes', to: '/ventas-contribuyentes', icon: DocumentTextIcon, periodo: true },
  { label: 'Documentos invalidados', to: '/anulados', icon: NoSymbolIcon, periodo: true },
  { label: 'Liquidación', to: '/liquidacion', icon: CalculatorIcon, periodo: true }
];

export default function AppShell({ children }) {
  const { token, activeEmpresa, selectEmpresa, logout } = useAuth();
  const { pathname, search } = useLocation();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const authenticatedPage = token && !['/', '/login', '/registro', '/terminos'].includes(pathname);
  if (!authenticatedPage) return children;

  const params = new URLSearchParams(search);
  const mes = params.get('mes') || localStorage.getItem('dashboard_mes') || String(new Date().getMonth() + 1).padStart(2, '0');
  const anio = params.get('anio') || localStorage.getItem('dashboard_anio') || String(new Date().getFullYear());

  const sidebar = (
    <div className="flex h-full flex-col bg-slate-900 text-slate-100">
      <div className="flex items-center justify-between border-b border-slate-700 px-5 py-6">
        <div>
          <p className="text-lg font-bold tracking-tight">Declaraciones IVA</p>
          <p className="text-xs text-slate-400">Gestión tributaria</p>
        </div>
        <button type="button" aria-label="Cerrar menú" onClick={() => setMobileOpen(false)} className="rounded-lg p-2 hover:bg-slate-800 lg:hidden"><XMarkIcon className="h-5 w-5" /></button>
      </div>
      <div className="border-b border-slate-700 px-4 py-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Empresa activa</p>
        <p className="truncate text-sm font-semibold" title={activeEmpresa?.razon_social}>{activeEmpresa?.razon_social || 'Sin empresa seleccionada'}</p>
        <button type="button" onClick={() => { selectEmpresa(null); setMobileOpen(false); navigate('/dashboard'); }} className="mt-2 flex items-center gap-2 text-xs text-sky-300 hover:text-white">
          <BuildingOffice2Icon className="h-4 w-4" /> Cambiar / administrar empresas
        </button>
      </div>
      <nav aria-label="Navegación principal" className="flex-1 space-y-1 overflow-y-auto px-3 py-5">
        {items.map(({ label, to, icon: Icon, periodo }) => {
          const disabled = periodo && !activeEmpresa;
          const destination = periodo ? `${to}?mes=${encodeURIComponent(mes)}&anio=${encodeURIComponent(anio)}` : to;
          return disabled ? (
            <div key={to} aria-disabled="true" className="flex cursor-not-allowed items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-500"><Icon className="h-5 w-5 shrink-0" />{label}</div>
          ) : (
            <NavLink key={to} to={destination} onClick={() => setMobileOpen(false)} className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${isActive ? 'bg-sky-600 font-semibold text-white' : 'text-slate-300 hover:bg-slate-800 hover:text-white'}`}>
              <Icon className="h-5 w-5 shrink-0" />{label}
            </NavLink>
          );
        })}
      </nav>
      <div className="border-t border-slate-700 p-3">
        <button type="button" onClick={() => { logout(); setMobileOpen(false); navigate('/login'); }} className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-white">
          <ArrowRightStartOnRectangleIcon className="h-5 w-5" /> Cerrar sesión
        </button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50 lg:pl-64">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 lg:block">{sidebar}</aside>
      <div className="sticky top-0 z-30 flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-3 lg:hidden">
        <button type="button" aria-label="Abrir menú" onClick={() => setMobileOpen(true)} className="rounded-lg p-2 text-slate-700 hover:bg-slate-100"><Bars3Icon className="h-6 w-6" /></button>
        <span className="font-semibold text-slate-800">Declaraciones IVA</span>
      </div>
      {mobileOpen && <div className="fixed inset-0 z-50 lg:hidden">
        <button type="button" aria-label="Cerrar menú lateral" onClick={() => setMobileOpen(false)} className="absolute inset-0 bg-slate-950/60" />
        <aside className="relative h-full w-72 max-w-[85vw]">{sidebar}</aside>
      </div>}
      <main id="contenido-principal" className="min-w-0">{children}</main>
    </div>
  );
}
