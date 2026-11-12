import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Building2,
  CalendarDays,
  CheckCircle2,
  KeyRound,
  LogOut,
  Save,
  ShieldCheck,
  UserRound,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const MONTHS = [
  ['01', 'Enero'],
  ['02', 'Febrero'],
  ['03', 'Marzo'],
  ['04', 'Abril'],
  ['05', 'Mayo'],
  ['06', 'Junio'],
  ['07', 'Julio'],
  ['08', 'Agosto'],
  ['09', 'Septiembre'],
  ['10', 'Octubre'],
  ['11', 'Noviembre'],
  ['12', 'Diciembre'],
];

function initialsOf(name) {
  if (!name) return 'US';
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return (parts[0]?.[0] || 'U').concat(parts[1]?.[0] || '').toUpperCase();
}

export default function Configuracion() {
  const { user, activeEmpresa, selectEmpresa, logout } = useAuth();
  const navigate = useNavigate();
  const currentDate = new Date();

  const [mes, setMes] = useState(
    localStorage.getItem('dashboard_mes') || String(currentDate.getMonth() + 1).padStart(2, '0')
  );
  const [anio, setAnio] = useState(
    localStorage.getItem('dashboard_anio') || String(currentDate.getFullYear())
  );
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!saved) return undefined;
    const timer = window.setTimeout(() => setSaved(false), 3000);
    return () => window.clearTimeout(timer);
  }, [saved]);

  const handleSavePeriod = (event) => {
    event.preventDefault();
    localStorage.setItem('dashboard_mes', mes);
    localStorage.setItem('dashboard_anio', anio);
    setSaved(true);
  };

  const handleUseCurrentPeriod = () => {
    setMes(String(currentDate.getMonth() + 1).padStart(2, '0'));
    setAnio(String(currentDate.getFullYear()));
    setSaved(false);
  };

  const handleChangeEmpresa = () => {
    selectEmpresa(null);
    navigate('/dashboard');
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="space-y-6 animate-fade-in-up">
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="card p-5 sm:p-6">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600 ring-1 ring-blue-100">
              <UserRound className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-900">Perfil de usuario</h2>
              <p className="mt-0.5 text-sm text-slate-500">Información de la sesión actual.</p>
            </div>
          </div>

          <div className="mt-5 flex items-center gap-4 rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-blue-600 text-sm font-bold text-white shadow-sm">
              {initialsOf(user?.nombre)}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-slate-900">{user?.nombre || 'Usuario'}</p>
              <p className="mt-0.5 text-xs text-slate-500">
                {user?.id ? `ID de usuario #${user.id}` : 'Sesión autenticada'}
              </p>
            </div>
            <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-emerald-700 ring-1 ring-emerald-100">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              Activa
            </span>
          </div>

          <dl className="mt-5 divide-y divide-slate-100 text-sm">
            <div className="flex items-center justify-between gap-4 py-2.5">
              <dt className="text-slate-500">Nombre</dt>
              <dd className="truncate font-medium text-slate-800">{user?.nombre || 'No disponible'}</dd>
            </div>
            <div className="flex items-center justify-between gap-4 py-2.5">
              <dt className="text-slate-500">Identificador</dt>
              <dd className="font-medium text-slate-800">{user?.id || 'No disponible'}</dd>
            </div>
            <div className="flex items-center justify-between gap-4 py-2.5">
              <dt className="text-slate-500">Términos de referencia</dt>
              <dd className="inline-flex items-center gap-1.5 font-medium text-emerald-700">
                <CheckCircle2 className="h-4 w-4" />
                {user?.terminos_aceptados ? 'Aceptados' : 'Pendientes'}
              </dd>
            </div>
          </dl>
        </section>

        <section className="card p-5 sm:p-6">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600 ring-1 ring-blue-100">
              <Building2 className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-900">Empresa activa</h2>
              <p className="mt-0.5 text-sm text-slate-500">Entidad con la que se generan los anexos.</p>
            </div>
          </div>

          {activeEmpresa ? (
            <>
              <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="truncate text-base font-semibold text-slate-900">{activeEmpresa.razon_social}</p>
                <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
                  <div className="rounded-lg bg-white px-3 py-2 ring-1 ring-slate-200">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">NIT</p>
                    <p className="mt-0.5 font-medium text-slate-800">{activeEmpresa.nit}</p>
                  </div>
                  <div className="rounded-lg bg-white px-3 py-2 ring-1 ring-slate-200">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">NRC</p>
                    <p className="mt-0.5 font-medium text-slate-800">{activeEmpresa.nrc || 'No registrado'}</p>
                  </div>
                </div>
              </div>
              <button type="button" onClick={handleChangeEmpresa} className="btn-secondary mt-4 w-full">
                <Building2 className="h-4 w-4" />
                Cambiar o administrar empresas
              </button>
            </>
          ) : (
            <>
              <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4">
                <p className="text-sm font-semibold text-amber-900">No hay una empresa seleccionada</p>
                <p className="mt-1 text-sm text-amber-800">
                  Selecciona una empresa para habilitar los libros, retenciones y la liquidación.
                </p>
              </div>
              <button type="button" onClick={() => navigate('/dashboard')} className="btn-primary mt-4 w-full">
                <Building2 className="h-4 w-4" />
                Ir a mis empresas
              </button>
            </>
          )}
        </section>
      </div>

      <section className="card p-5 sm:p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600 ring-1 ring-blue-100">
              <CalendarDays className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-900">Preferencias del período</h2>
              <p className="mt-0.5 max-w-xl text-sm text-slate-500">
                Define el mes y año que se cargarán por defecto en el dashboard y en el generador de anexos.
              </p>
            </div>
          </div>
          {saved && (
            <span className="inline-flex items-center gap-1.5 self-start rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-100">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Preferencias guardadas
            </span>
          )}
        </div>

        <form onSubmit={handleSavePeriod} className="mt-5 flex flex-col gap-4 border-t border-slate-100 pt-5 sm:flex-row sm:items-end">
          <div className="w-full sm:max-w-[220px]">
            <label htmlFor="config-mes" className="mb-1.5 block text-xs font-semibold text-slate-600">
              Mes por defecto
            </label>
            <select id="config-mes" value={mes} onChange={(event) => setMes(event.target.value)} className="input-base">
              {MONTHS.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <div className="w-full sm:max-w-[140px]">
            <label htmlFor="config-anio" className="mb-1.5 block text-xs font-semibold text-slate-600">
              Año por defecto
            </label>
            <input
              id="config-anio"
              type="number"
              min="2000"
              max="2100"
              value={anio}
              onChange={(event) => setAnio(event.target.value)}
              className="input-base"
            />
          </div>
          <div className="flex flex-wrap gap-2 sm:ml-auto">
            <button type="button" onClick={handleUseCurrentPeriod} className="btn-secondary">
              Usar período actual
            </button>
            <button type="submit" className="btn-primary">
              <Save className="h-4 w-4" />
              Guardar preferencias
            </button>
          </div>
        </form>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="card p-5 sm:p-6">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-50 text-rose-600 ring-1 ring-rose-100">
              <KeyRound className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-900">Sesión y seguridad</h2>
              <p className="mt-0.5 text-sm text-slate-500">
                Cierra la sesión de este dispositivo cuando termines de trabajar.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm font-semibold text-rose-700 transition hover:bg-rose-100"
          >
            <LogOut className="h-4 w-4" />
            Cerrar sesión
          </button>
        </section>

        <section className="card p-5 sm:p-6">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-600 ring-1 ring-slate-200">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-900">Acerca del sistema</h2>
              <p className="mt-0.5 text-sm text-slate-500">
                Plataforma de apoyo para la declaración de IVA y anexos F-07 en El Salvador.
              </p>
            </div>
          </div>
          <dl className="mt-5 space-y-2 border-t border-slate-100 pt-4 text-sm">
            <div className="flex items-center justify-between gap-4">
              <dt className="text-slate-500">Versión</dt>
              <dd className="font-medium text-slate-800">1.0.0</dd>
            </div>
            <div className="flex items-center justify-between gap-4">
              <dt className="text-slate-500">Marco normativo</dt>
              <dd className="font-medium text-slate-800">F-07 · Ministerio de Hacienda</dd>
            </div>
          </dl>
        </section>
      </div>

      <p className="pb-2 text-center text-xs text-slate-400">
        Sistema de Declaración de IVA · La información fiscal es responsabilidad del contribuyente.
      </p>
    </div>
  );
}
