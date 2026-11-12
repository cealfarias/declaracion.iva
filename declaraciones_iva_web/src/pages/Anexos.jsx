import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowRight,
  Ban,
  Building2,
  CalendarDays,
  Calculator,
  FileSpreadsheet,
  Percent,
  Receipt,
  ShoppingCart,
  Users,
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

const TONES = {
  blue: 'bg-blue-50 text-blue-600 ring-1 ring-blue-100',
  emerald: 'bg-emerald-50 text-emerald-600 ring-1 ring-emerald-100',
  amber: 'bg-amber-50 text-amber-600 ring-1 ring-amber-100',
  rose: 'bg-rose-50 text-rose-600 ring-1 ring-rose-100',
  violet: 'bg-violet-50 text-violet-600 ring-1 ring-violet-100',
};

const ANEXOS = [
  {
    title: 'Libro de Compras',
    badge: 'Anexo 3',
    description: 'Compras internas, importaciones, sujetos excluidos y crédito fiscal del período.',
    to: '/compras',
    icon: ShoppingCart,
    tone: 'blue',
  },
  {
    title: 'Ventas a Contribuyentes',
    badge: 'F-07',
    description: 'Comprobantes de crédito fiscal, notas de crédito y débito emitidos.',
    to: '/ventas-contribuyentes',
    icon: Receipt,
    tone: 'emerald',
  },
  {
    title: 'Ventas Consumidor Final',
    badge: 'F-07',
    description: 'Facturas de consumidor final emitidas y su débito fiscal correspondiente.',
    to: '/consumidor-final',
    icon: Users,
    tone: 'amber',
  },
  {
    title: 'Documentos Invalidados',
    badge: 'Anexo',
    description: 'Eventos de invalidación validados con Hacienda para excluirlos del cálculo.',
    to: '/anulados',
    icon: Ban,
    tone: 'rose',
  },
  {
    title: 'Retenciones 1%',
    badge: 'Casilla 162',
    description: 'DTE 07 y retención de IVA efectuada al declarante durante el período.',
    to: '/retenciones',
    icon: Percent,
    tone: 'violet',
  },
];

export default function Anexos() {
  const { activeEmpresa } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const currentDate = new Date();

  const [mes, setMes] = useState(
    searchParams.get('mes') ||
      localStorage.getItem('dashboard_mes') ||
      String(currentDate.getMonth() + 1).padStart(2, '0')
  );
  const [anio, setAnio] = useState(
    searchParams.get('anio') ||
      localStorage.getItem('dashboard_anio') ||
      String(currentDate.getFullYear())
  );

  useEffect(() => {
    localStorage.setItem('dashboard_mes', mes);
  }, [mes]);

  useEffect(() => {
    localStorage.setItem('dashboard_anio', anio);
  }, [anio]);

  const periodQuery = `?mes=${encodeURIComponent(mes)}&anio=${encodeURIComponent(anio)}`;
  const openAnexo = (to) => {
    if (!activeEmpresa) return;
    navigate(`${to}${periodQuery}`);
  };

  return (
    <div className="space-y-6 animate-fade-in-up">
      <section className="card p-5 sm:p-6">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="min-w-0">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-blue-700 ring-1 ring-blue-100">
              <FileSpreadsheet className="h-3.5 w-3.5" />
              Generador
            </span>
            <h2 className="mt-3 text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">
              Anexos F-07 del período
            </h2>
            <p className="mt-1 max-w-2xl text-sm text-slate-500">
              Selecciona el período fiscal y abre el libro que necesitas. Cada anexo conserva sus versiones
              originales y modificatorias.
            </p>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              {activeEmpresa ? (
                <>
                  <span className="inline-flex min-w-0 items-center gap-1.5 rounded-lg bg-slate-50 px-2.5 py-1.5 text-xs font-medium text-slate-600 ring-1 ring-slate-200">
                    <Building2 className="h-3.5 w-3.5 shrink-0 text-slate-400" />
                    <span className="truncate">{activeEmpresa.razon_social}</span>
                  </span>
                  <span className="rounded-lg bg-slate-50 px-2.5 py-1.5 text-xs text-slate-500 ring-1 ring-slate-200">
                    NIT {activeEmpresa.nit}
                  </span>
                </>
              ) : (
                <span className="text-xs font-medium text-amber-700">
                  Selecciona una empresa para habilitar los anexos.
                </span>
              )}
            </div>
          </div>

          <div className="flex shrink-0 flex-col gap-3 sm:flex-row sm:items-end">
            <div>
              <label htmlFor="anexos-mes" className="mb-1 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                <CalendarDays className="h-3.5 w-3.5" />
                Mes
              </label>
              <select
                id="anexos-mes"
                value={mes}
                onChange={(event) => setMes(event.target.value)}
                className="input-base min-w-[150px]"
              >
                {MONTHS.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="anexos-anio" className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                Año
              </label>
              <input
                id="anexos-anio"
                type="number"
                min="2000"
                max="2100"
                value={anio}
                onChange={(event) => setAnio(event.target.value)}
                className="input-base w-[110px]"
              />
            </div>
          </div>
        </div>
      </section>

      {!activeEmpresa && (
        <section className="flex flex-col gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-amber-900">Aún no hay una empresa activa</p>
            <p className="mt-0.5 text-sm text-amber-800">
              Para generar anexos primero debes seleccionar o registrar una empresa.
            </p>
          </div>
          <button type="button" onClick={() => navigate('/dashboard')} className="btn-primary shrink-0">
            <Building2 className="h-4 w-4" />
            Ir a mis empresas
          </button>
        </section>
      )}

      <section aria-label="Anexos disponibles" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {ANEXOS.map(({ title, badge, description, to, icon: Icon, tone }) => (
          <article
            key={to}
            className={`group flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition ${
              activeEmpresa ? 'hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-md' : 'opacity-70'
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className={`flex h-11 w-11 items-center justify-center rounded-xl ${TONES[tone]}`}>
                <Icon className="h-5 w-5" />
              </div>
              <span className="rounded-full bg-slate-50 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500 ring-1 ring-slate-200">
                {badge}
              </span>
            </div>
            <h3 className="mt-4 text-base font-semibold text-slate-900">{title}</h3>
            <p className="mt-1 flex-1 text-sm leading-relaxed text-slate-500">{description}</p>
            <button
              type="button"
              onClick={() => openAnexo(to)}
              disabled={!activeEmpresa}
              className="mt-5 inline-flex items-center gap-1.5 self-start text-sm font-semibold text-blue-700 transition hover:text-blue-800 disabled:cursor-not-allowed disabled:text-slate-400"
            >
              Abrir anexo
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </button>
          </article>
        ))}
      </section>

      <section className="overflow-hidden rounded-xl bg-gradient-to-r from-slate-900 via-slate-900 to-blue-950 p-6 text-white shadow-sm sm:p-7">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-white/10 ring-1 ring-white/15">
              <Calculator className="h-6 w-6 text-blue-200" />
            </div>
            <div>
              <h3 className="text-lg font-semibold">Liquidación de Impuestos F-07</h3>
              <p className="mt-1 max-w-2xl text-sm text-slate-300">
                Consolida compras, ventas, retenciones y remanentes para determinar el pago a cuenta o el
                remanente del período.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => openAnexo('/liquidacion')}
            disabled={!activeEmpresa}
            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg bg-white px-4 py-2.5 text-sm font-bold text-slate-900 shadow-sm transition hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Abrir liquidación
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </section>
    </div>
  );
}
