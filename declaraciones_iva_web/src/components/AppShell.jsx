import React, { useEffect, useMemo, useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  FileSpreadsheet,
  ShoppingCart,
  Receipt,
  Percent,
  Settings,
  Menu,
  X,
  LogOut,
  ChevronDown,
  ChevronRight,
  Building2,
  Calculator,
  Landmark,
  Lock,
  ShieldCheck,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const PUBLIC_PATHS = ['/', '/login', '/registro', '/terminos'];

const PAGE_META = {
  '/dashboard': { section: 'General', title: 'Dashboard' },
  '/anexos': { section: 'General', title: 'Generador de Anexos' },
  '/compras': { section: 'Libros y anexos', title: 'Libro de Compras' },
  '/consumidor-final': { section: 'Libros y anexos', title: 'Ventas · Consumidor Final' },
  '/ventas-contribuyentes': { section: 'Libros y anexos', title: 'Ventas · Contribuyentes' },
  '/anulados': { section: 'Libros y anexos', title: 'Documentos Invalidados' },
  '/retenciones': { section: 'Libros y anexos', title: 'Retenciones 1%' },
  '/liquidacion': { section: 'Herramientas', title: 'Liquidación F-07' },
  '/configuracion': { section: 'Sistema', title: 'Configuración' },
};

const VENTAS_LINKS = [
  { label: 'Consumidor Final', to: '/consumidor-final' },
  { label: 'Contribuyentes', to: '/ventas-contribuyentes' },
  { label: 'Documentos Invalidados', to: '/anulados' },
];

function initialsOf(name) {
  if (!name) return 'US';
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return (parts[0]?.[0] || 'U').concat(parts[1]?.[0] || '').toUpperCase();
}

export default function AppShell({ children }) {
  const { token, user, activeEmpresa, selectEmpresa, logout } = useAuth();
  const { pathname, search } = useLocation();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [ventasOpen, setVentasOpen] = useState(false);

  const params = new URLSearchParams(search);
  const currentDate = new Date();
  const mes =
    params.get('mes') ||
    localStorage.getItem('dashboard_mes') ||
    String(currentDate.getMonth() + 1).padStart(2, '0');
  const anio =
    params.get('anio') ||
    localStorage.getItem('dashboard_anio') ||
    String(currentDate.getFullYear());

  const withPeriod = (to) => `${to}?mes=${encodeURIComponent(mes)}&anio=${encodeURIComponent(anio)}`;
  const meta = PAGE_META[pathname] || { section: 'Panel', title: 'Sistema de IVA' };
  const authenticatedPage = Boolean(token) && !PUBLIC_PATHS.includes(pathname);
  const isVentasActive = VENTAS_LINKS.some((item) => pathname === item.to);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (isVentasActive) setVentasOpen(true);
  }, [isVentasActive]);

  useEffect(() => {
    if (!mobileOpen) return undefined;
    const onKeyDown = (event) => {
      if (event.key === 'Escape') setMobileOpen(false);
    };
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [mobileOpen]);

  const userName = user?.nombre || 'Usuario';
  const userInitials = useMemo(() => initialsOf(userName), [userName]);

  if (!authenticatedPage) return children;

  const closeMobile = () => setMobileOpen(false);

  const handleLogout = () => {
    logout();
    closeMobile();
    navigate('/login');
  };

  const handleChangeEmpresa = () => {
    selectEmpresa(null);
    closeMobile();
    navigate('/dashboard');
  };

  const navItemClass = ({ isActive }) =>
    `group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
      isActive
        ? 'bg-blue-600 text-white shadow-sm shadow-blue-950/40'
        : 'text-slate-300 hover:bg-white/5 hover:text-white'
    }`;

  const disabledItemClass =
    'flex cursor-not-allowed items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-600';

  const renderPeriodItem = (to, label, Icon) => {
    if (!activeEmpresa) {
      return (
        <div key={to} className={disabledItemClass} aria-disabled="true" title="Selecciona una empresa para continuar">
          <Icon className="h-[18px] w-[18px] shrink-0" />
          <span className="flex-1">{label}</span>
          <Lock className="h-3.5 w-3.5 text-slate-600" />
        </div>
      );
    }
    return (
      <NavLink key={to} to={withPeriod(to)} onClick={closeMobile} className={navItemClass}>
        <Icon className="h-[18px] w-[18px] shrink-0" />
        {label}
      </NavLink>
    );
  };

  const sidebar = (
    <div className="flex h-full flex-col bg-[#0b1220] text-slate-200">
      <div className="flex min-h-[80px] shrink-0 items-center gap-3 border-b border-white/10 px-4 py-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-600 shadow-lg shadow-blue-950/50">
          <Landmark className="h-5 w-5 text-white" aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[12px] font-bold leading-tight text-white">
            Sistema de Declaración de IVA
          </p>
          <p className="mt-1 text-[9px] font-semibold uppercase tracking-[0.14em] text-slate-500">
            El Salvador · F-07
          </p>
        </div>
        <button
          type="button"
          aria-label="Cerrar menú"
          onClick={closeMobile}
          className="rounded-lg p-2 text-slate-400 transition hover:bg-white/10 hover:text-white lg:hidden"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-4 custom-scrollbar">
        <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
          Principal
        </p>
        <nav aria-label="Navegación principal" className="space-y-1">
          <NavLink to="/dashboard" end onClick={closeMobile} className={navItemClass}>
            <LayoutDashboard className="h-[18px] w-[18px] shrink-0" />
            Dashboard
          </NavLink>
          <NavLink to="/anexos" onClick={closeMobile} className={navItemClass}>
            <FileSpreadsheet className="h-[18px] w-[18px] shrink-0" />
            Generador de Anexos
          </NavLink>
        </nav>

        <p className="px-3 pb-2 pt-5 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
          Libros y anexos
        </p>
        <nav aria-label="Libros y anexos" className="space-y-1">
          {renderPeriodItem('/compras', 'Libro de Compras', ShoppingCart)}

          <div>
            <button
              type="button"
              onClick={() => setVentasOpen((open) => !open)}
              aria-expanded={ventasOpen}
              className={`group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                isVentasActive
                  ? 'bg-blue-600 text-white shadow-sm shadow-blue-950/40'
                  : 'text-slate-300 hover:bg-white/5 hover:text-white'
              }`}
            >
              <Receipt className="h-[18px] w-[18px] shrink-0" />
              <span className="flex-1 text-left">Libro de Ventas</span>
              <ChevronDown
                className={`h-4 w-4 shrink-0 transition-transform ${ventasOpen ? 'rotate-180' : ''}`}
              />
            </button>
            {ventasOpen && (
              <div className="mt-1 space-y-0.5 border-l border-white/10 pl-4">
                {VENTAS_LINKS.map((item) => {
                  if (!activeEmpresa) {
                    return (
                      <div
                        key={item.to}
                        className="flex cursor-not-allowed items-center gap-2 rounded-lg px-3 py-2 text-[13px] text-slate-600"
                        aria-disabled="true"
                      >
                        <span className="h-1 w-1 rounded-full bg-slate-600" />
                        {item.label}
                      </div>
                    );
                  }
                  return (
                    <NavLink
                      key={item.to}
                      to={withPeriod(item.to)}
                      onClick={closeMobile}
                      className={({ isActive }) =>
                        `flex items-center gap-2 rounded-lg px-3 py-2 text-[13px] transition-colors ${
                          isActive
                            ? 'bg-white/10 font-semibold text-white'
                            : 'text-slate-400 hover:bg-white/5 hover:text-slate-100'
                        }`
                      }
                    >
                      <span className="h-1 w-1 rounded-full bg-current opacity-70" />
                      {item.label}
                    </NavLink>
                  );
                })}
              </div>
            )}
          </div>

          {renderPeriodItem('/retenciones', 'Retenciones', Percent)}
        </nav>

        <p className="px-3 pb-2 pt-5 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
          Herramientas
        </p>
        <nav aria-label="Herramientas" className="space-y-1">
          {renderPeriodItem('/liquidacion', 'Liquidación F-07', Calculator)}
          <NavLink to="/configuracion" onClick={closeMobile} className={navItemClass}>
            <Settings className="h-[18px] w-[18px] shrink-0" />
            Configuración
          </NavLink>
        </nav>
      </div>

      <div className="shrink-0 border-t border-white/10 p-3">
        <div className="rounded-xl border border-white/10 bg-white/[0.04] p-3">
          <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">
            <Building2 className="h-3.5 w-3.5" />
            Empresa activa
          </p>
          {activeEmpresa ? (
            <>
              <p className="mt-1.5 truncate text-sm font-semibold text-white" title={activeEmpresa.razon_social}>
                {activeEmpresa.razon_social}
              </p>
              <p className="mt-0.5 text-[11px] text-slate-400">NIT {activeEmpresa.nit}</p>
              <button
                type="button"
                onClick={handleChangeEmpresa}
                className="mt-2.5 flex w-full items-center justify-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-2 py-1.5 text-[11px] font-semibold text-slate-200 transition hover:bg-white/10"
              >
                <Building2 className="h-3.5 w-3.5" />
                Cambiar empresa
              </button>
            </>
          ) : (
            <>
              <p className="mt-1.5 text-sm font-medium text-slate-300">Sin empresa seleccionada</p>
              <button
                type="button"
                onClick={() => {
                  closeMobile();
                  navigate('/dashboard');
                }}
                className="mt-2.5 flex w-full items-center justify-center gap-1.5 rounded-lg bg-blue-600 px-2 py-1.5 text-[11px] font-semibold text-white transition hover:bg-blue-500"
              >
                <Building2 className="h-3.5 w-3.5" />
                Seleccionar empresa
              </button>
            </>
          )}
        </div>
        <p className="mt-3 flex items-center gap-1.5 px-1 text-[10px] text-slate-600">
          <ShieldCheck className="h-3.5 w-3.5" />
          Información fiscal protegida
        </p>
      </div>
    </div>
  );

  return (
    <div className="app-shell min-h-screen bg-[#f3f4f6] lg:pl-[268px]">
      <aside className="app-sidebar fixed inset-y-0 left-0 z-40 hidden w-[268px] lg:block">
        {sidebar}
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            aria-label="Cerrar menú lateral"
            onClick={closeMobile}
            className="absolute inset-0 bg-slate-950/60 backdrop-blur-sm"
          />
          <aside className="app-sidebar absolute inset-y-0 left-0 w-[280px] max-w-[86vw] animate-slide-in-left shadow-2xl">
            {sidebar}
          </aside>
        </div>
      )}

      <div className="flex min-h-screen min-w-0 flex-col">
        <header className="app-topbar sticky top-0 z-30 flex h-16 shrink-0 items-center gap-2 border-b border-slate-200 bg-white/90 px-4 backdrop-blur-md sm:gap-3 lg:px-8">
          <button
            type="button"
            aria-label="Abrir menú"
            onClick={() => setMobileOpen(true)}
            className="rounded-lg p-2 text-slate-600 transition hover:bg-slate-100 hover:text-slate-900 lg:hidden"
          >
            <Menu className="h-5 w-5" />
          </button>

          <div className="min-w-0 flex-1">
            <div className="hidden items-center gap-1.5 text-[11px] font-medium text-slate-400 sm:flex">
              <span>Panel</span>
              <ChevronRight className="h-3 w-3" />
              <span>{meta.section}</span>
            </div>
            <h1 className="truncate text-[17px] font-semibold tracking-tight text-slate-900">
              {meta.title}
            </h1>
          </div>

          {activeEmpresa && (
            <div className="hidden max-w-[400px] items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-600 xl:flex">
              <Building2 className="h-3.5 w-3.5 shrink-0 text-slate-400" />
              <span className="truncate font-medium text-slate-700">{activeEmpresa.razon_social}</span>
              <span className="text-slate-300">|</span>
              <span className="shrink-0 text-slate-500">NIT {activeEmpresa.nit}</span>
            </div>
          )}

          <div className="flex items-center gap-2 sm:gap-3">
            <div className="hidden text-right sm:block">
              <p className="max-w-[180px] truncate text-sm font-semibold text-slate-800">{userName}</p>
              <p className="text-[11px] text-slate-500">Cuenta empresarial</p>
            </div>
            <div
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-50 text-xs font-bold text-blue-700 ring-1 ring-blue-100"
              title={userName}
            >
              {userInitials}
            </div>
            <div className="hidden h-8 w-px bg-slate-200 sm:block" />
            <button
              type="button"
              onClick={handleLogout}
              title="Cerrar sesión"
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-sm font-semibold text-slate-600 transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700 sm:px-3"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Cerrar sesión</span>
            </button>
          </div>
        </header>

        <main id="contenido-principal" className="app-main min-w-0 flex-1 px-4 py-6 lg:px-8 lg:py-8">
          <div className="mx-auto w-full max-w-[1440px]">{children}</div>
        </main>
      </div>
    </div>
  );
}
