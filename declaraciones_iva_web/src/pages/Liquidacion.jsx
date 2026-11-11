import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { useAssistant } from '../contexts/AssistantContext';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function Liquidacion() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const mes = queryParams.get("mes");
  const anio = queryParams.get("anio");
  
  const { token, activeEmpresa } = useAuth();
  const { enqueueMessages } = useAssistant();
  
  const [data, setData] = useState(null);
  const [auditoria164, setAuditoria164] = useState({ estado: 'pendiente', respaldo: null });
  const [diferenciasServidor, setDiferenciasServidor] = useState([]);
  const [ajustesHistoricosLocales, setAjustesHistoricosLocales] = useState(false);
  const [inventarioHistorico, setInventarioHistorico] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const [editRemanente, setEditRemanente] = useState(false);
  const [remanenteInput, setRemanenteInput] = useState("");
  const [editDevoluciones, setEditDevoluciones] = useState(false);
  const [devNetoInput, setDevNetoInput] = useState("");
  const [devCredInput, setDevCredInput] = useState("");
  const [showAjustes, setShowAjustes] = useState(false);
  const [ajustes, setAjustes] = useState({
    retenciones_recibidas: "0.00",
    percepciones_recibidas: "0.00",
    anticipo_cuenta_2: "0.00",
    retenciones_efectuadas: "0.00",
    percepciones_efectuadas: "0.00"
  });

  useEffect(() => {
    if (!token) return;
    if (!activeEmpresa) {
      navigate('/dashboard');
    }
  }, [token, activeEmpresa, navigate]);

  useEffect(() => {
    if (activeEmpresa && mes && anio) {
      fetchLiquidacion();
    }
  }, [activeEmpresa, mes, anio]);

  const getOmittedFromStorage = () => {
    try {
      const stored = localStorage.getItem(`omitted_compras_${activeEmpresa?.id}_${mes}_${anio}`);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  };

  const getRemanenteManualStorage = () => {
    try {
      const stored = localStorage.getItem(`remanente_manual_${activeEmpresa?.id}_${mes}_${anio}`);
      return stored !== null ? parseFloat(stored) : null;
    } catch {
      return null;
    }
  };

  const getDevolucionesManualStorage = () => {
    try {
      const stored = localStorage.getItem(`devoluciones_manual_${activeEmpresa?.id}_${mes}_${anio}`);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  };

  const saveDevoluciones = (netoVal, credVal) => {
    const neto = Number(String(netoVal).trim());
    const credito = Number(String(credVal).trim());
    if (
      String(netoVal).trim() === "" || String(credVal).trim() === "" ||
      !Number.isFinite(neto) || !Number.isFinite(credito) ||
      neto < 0 || credito < 0
    ) {
      enqueueMessages([{ text: "Ingrese importes válidos, no negativos, para las devoluciones.", type: "error" }]);
      return;
    }
    try {
      localStorage.setItem(`devoluciones_manual_${activeEmpresa?.id}_${mes}_${anio}`, JSON.stringify({
        neto,
        credito
      }));
    } catch (errorStorage) {
      console.error("No se pudieron guardar las devoluciones en este navegador.", errorStorage);
      enqueueMessages([{ text: "No se guardaron las devoluciones: el almacenamiento del navegador no está disponible.", type: "error" }]);
      return;
    }
    setEditDevoluciones(false);
    enqueueMessages([{ text: "Devoluciones guardadas solo en este navegador; todavía no se han registrado en PostgreSQL.", type: "success" }]);
    fetchLiquidacion();
  };

  const fetchLiquidacion = async () => {
    setLoading(true);
    setData(null);
    setAuditoria164({ estado: 'pendiente', respaldo: null });
    try {
      const [liqRes, comprasRes, ventasCfRes, ventasCcfRes, anuladosRes] = await Promise.all([
        axios.get(`${API_URL}/api/v1/liquidacion/${activeEmpresa.id}?mes=${mes}&anio=${anio}`),
        axios.get(`${API_URL}/api/v1/compras/${activeEmpresa.id}?mes=${mes}&anio=${anio}`),
        axios.get(`${API_URL}/api/v1/ventas-cf/list/${activeEmpresa.id}?mes=${mes}&anio=${anio}`),
        axios.get(`${API_URL}/api/v1/ventas-contribuyentes/list/${activeEmpresa.id}?mes=${mes}&anio=${anio}`),
        axios.get(`${API_URL}/api/v1/anulados/list/${activeEmpresa.id}?mes=${mes}&anio=${anio}`)
      ]);
      // Consulta independiente: un error de auditoría no altera los importes fiscales.
      try {
        const auditoriaRes = await axios.get(
          `${API_URL}/api/v1/liquidacion/${activeEmpresa.id}/excedente-impuesto-anterior-auditoria?mes=${mes}&anio=${anio}`
        );
        setAuditoria164({
          estado: auditoriaRes.data.auditoria_disponible ? 'disponible' : (auditoriaRes.data.consistencia === 'saldo_sin_auditoria' ? 'saldo_sin_auditoria' : 'sin_respaldo'),
          respaldo: auditoriaRes.data.respaldo ?? null
        });
      } catch (errorAuditoria) {
        setAuditoria164({
          estado: errorAuditoria.response?.status === 409
            ? 'discrepancia'
            : [401, 403].includes(errorAuditoria.response?.status) ? 'sin_autorizacion' : 'error',
          respaldo: null
        });
      }
      const res = liqRes.data;
      // Conservar cifras originales para detectar divergencias con los ajustes del navegador.
      const cifrasServidor = {
        debito: Number(res.totales?.debito || 0),
        credito: Number(res.totales?.credito || 0),
        impuesto: Number(res.impuesto_a_pagar || 0),
        remanente: Number(res.remanente_siguiente || 0),
        remanenteAnterior: Number(res.remanente_anterior || 0)
      };
      const comprasList = comprasRes.data || [];
      const ventasCfList = ventasCfRes.data || [];
      const ventasCcfList = ventasCcfRes.data || [];
      const anuladosList = anuladosRes.data || [];

      // 1. Identificar códigos de generación anulados
      const setAnulados = new Set();
      anuladosList.forEach(a => {
        const cg = (a.codigo_generacion || "").trim();
        if (cg) {
          setAnulados.add(cg.toUpperCase());
          setAnulados.add(cg.replace(/-/g, "").toUpperCase());
        }
      });

      // 2. Filtrar ventas CF excluyendo las anuladas y omitidas
      let anuladosCfCount = 0;
      let brutoCfValido = 0;
      ventasCfList.forEach(v => {
        const cg = (v.codigo_generacion || "").trim();
        const cgClean = cg.replace(/-/g, "").toUpperCase();
        const isAnulado = setAnulados.has(cg.toUpperCase()) || setAnulados.has(cgClean);
        if (isAnulado) {
          anuladosCfCount++;
        } else if (!v.omitido) {
          brutoCfValido += (v.ventas_gravadas || 0);
        }
      });

      const netoCfValido = Number((brutoCfValido / 1.13).toFixed(2));
      const debitoCfValido = Number((brutoCfValido - netoCfValido).toFixed(2));

      // 3. Filtrar ventas CCF excluyendo las anuladas y omitidas
      let anuladosCcfCount = 0;
      let netoCcfValido = 0;
      let debitoCcfValido = 0;
      ventasCcfList.forEach(v => {
        const nd = (v.numero_documento || "").trim();
        const nr = (v.numero_resolucion || "").trim();
        const isAnulado = setAnulados.has(nd.toUpperCase()) || setAnulados.has(nd.replace(/-/g, "").toUpperCase()) ||
                          setAnulados.has(nr.toUpperCase()) || setAnulados.has(nr.replace(/-/g, "").toUpperCase());
        if (isAnulado) {
          anuladosCcfCount++;
        } else if (!v.omitido) {
          netoCcfValido += (v.ventas_gravadas || 0);
          debitoCcfValido += (v.debito_fiscal || 0);
        }
      });

      // Para períodos ordinarios, el backend es la única fuente de importes fiscales.
      // Conservar temporalmente la ruta heredada solo cuando existan ajustes
      // locales explícitos o los casos históricos aún pendientes de migración.
      const mesNumero = Number(mes);
      const anioNumero = Number(anio);
      const mesPrevio = mesNumero === 1 ? "12" : String(mesNumero - 1).padStart(2, "0");
      const anioPrevio = mesNumero === 1 ? anioNumero - 1 : anioNumero;
      let remanentePrevioLocal = null;
      try {
        remanentePrevioLocal = localStorage.getItem(
          `remanente_siguiente_${activeEmpresa?.id}_${mesPrevio}_${anioPrevio}`
        );
      } catch (errorStorage) {
        console.warn("No se pudo consultar el remanente histórico local.", errorStorage);
      }
      const tieneAjustesLegados =
        getOmittedFromStorage() !== null ||
        getDevolucionesManualStorage() !== null ||
        getRemanenteManualStorage() !== null ||
        (activeEmpresa?.id === 2 && anio === "2026" && ["01", "02", "03"].includes(mes));

      res.anulados_cf_count = anuladosCfCount;
      res.anulados_ccf_count = anuladosCcfCount;

      // Inventario de solo lectura: no migra, elimina ni transmite localStorage.
      const inventario = [];
      const omitidasGuardadas = getOmittedFromStorage();
      const devolucionesGuardadas = getDevolucionesManualStorage();
      const remanenteGuardado = getRemanenteManualStorage();
      if (omitidasGuardadas !== null) {
        inventario.push("Compras omitidas guardadas en este navegador: " +
          (Array.isArray(omitidasGuardadas) ? omitidasGuardadas.length : "formato no reconocido"));
      }
      if (devolucionesGuardadas !== null) {
        const netoLocal = Number(devolucionesGuardadas?.neto);
        const creditoLocal = Number(devolucionesGuardadas?.credito);
        const netoDte = Number(res.compras?.devoluciones_neto);
        const creditoDte = Number(res.compras?.devoluciones_credito);
        const datosCompletos = [
          devolucionesGuardadas?.neto, devolucionesGuardadas?.credito,
          res.compras?.devoluciones_neto, res.compras?.devoluciones_credito
        ].every(valor => valor !== null && valor !== undefined && valor !== "");
        if (datosCompletos && [netoLocal, creditoLocal, netoDte, creditoDte].every(Number.isFinite)) {
          const importesDifieren = Math.round(netoLocal * 100) !== Math.round(netoDte * 100) ||
            Math.round(creditoLocal * 100) !== Math.round(creditoDte * 100);
          inventario.push(
            `Devoluciones — navegador: neto ${netoLocal.toFixed(2)}, crédito ${creditoLocal.toFixed(2)}; ` +
            `DTE 05 del servidor: neto ${netoDte.toFixed(2)}, crédito ${creditoDte.toFixed(2)}. ` +
            (importesDifieren
              ? "DISCREPANCIA: los importes no coinciden; requiere conciliación documental."
              : "Importes coincidentes, sin aceptación fiscal todavía.") +
            " Comparación informativa: no se suman ni se migran automáticamente."
          );
        } else {
          inventario.push("Devoluciones manuales guardadas: faltan importes o hay formatos inválidos; no se supone que el valor ausente sea cero.");
        }
      }
      if (remanenteGuardado !== null) inventario.push("Remanente anterior manual guardado en este navegador");
      if (remanentePrevioLocal !== null) {
        const valorPrevio = Number(remanentePrevioLocal);
        const valorServidor = cifrasServidor.remanenteAnterior;
        inventario.push(Number.isFinite(valorPrevio)
          ? `Remanente del mes anterior guardado localmente: ${valorPrevio.toFixed(2)}; remanente anterior del servidor: ${valorServidor.toFixed(2)} (sin modificación automática)`
          : "Remanente del mes anterior guardado localmente con formato no válido");
      }
      if (activeEmpresa?.id === 2 && anio === "2026" && ["01", "02", "03"].includes(mes)) {
        inventario.push("Reglas históricas especiales de 2026 pendientes de conciliación");
      }
      const claveRemanenteAnterior = `remanente_siguiente_${activeEmpresa?.id}_${mes}_${anio}`;
      try {
        if (localStorage.getItem(claveRemanenteAnterior) !== null) {
          inventario.push("Copia local del remanente siguiente (no se modifica)");
        }
      } catch (storageError) {
        inventario.push("No se pudo inspeccionar la copia local del remanente");
      }
      setInventarioHistorico(inventario);
      setAjustesHistoricosLocales(tieneAjustesLegados || remanentePrevioLocal !== null);
      if (tieneAjustesLegados) {
      res.ventas_cf = {
        neto: netoCfValido,
        debito: debitoCfValido
      };
      res.ventas_ccf = {
        neto: Number(netoCcfValido.toFixed(2)),
        debito: Number(debitoCcfValido.toFixed(2))
      };
      res.anulados_cf_count = anuladosCfCount;
      res.anulados_ccf_count = anuladosCcfCount;

      const totalDebito = Number((debitoCfValido + debitoCcfValido).toFixed(2));

      // 4. Recalcular compras del mes excluyendo omitidos y segregando Devoluciones sobre Compras (DTE 05)
      let netoComprasGravadas = 0; // Casilla 80
      let creditoComprasGravadas = 0; // Casilla 130
      let devolucionesNeto = 0; // Casilla 81
      let devolucionesCredito = 0; // Casilla 131

      if (comprasList.length > 0) {
        const stored = getOmittedFromStorage();
        const defaultRejected = (activeEmpresa?.id === 2 && mes === "01" && anio === "2026") ? [245, 246] : [];
        const activeOmitted = stored !== null ? stored : defaultRejected;

        const activas = comprasList.filter(c => {
          const isOmitido = stored !== null
            ? stored.includes(c.id)
            : (Boolean(c.omitido) || defaultRejected.includes(c.id));
          return !isOmitido;
        });

        activas.forEach(c => {
          const tipo = (c.tipo_documento || "03").trim();
          const grav = (c.compras_internas_gravadas || 0) + (c.internaciones_gravadas_bienes || 0) + (c.importaciones_gravadas_bienes || 0) + (c.importaciones_gravadas_servicios || 0);
          const cred = (c.credito_fiscal || 0);
          if (tipo === "05") {
            devolucionesNeto += grav;
            devolucionesCredito += cred;
          } else {
            netoComprasGravadas += grav;
            creditoComprasGravadas += cred;
          }
        });
      }

      // Comprobar si hay ajustes manuales guardados de devoluciones
      const devManual = getDevolucionesManualStorage();
      if (devManual) {
        if (devManual.neto !== undefined) devolucionesNeto = parseFloat(devManual.neto) || 0;
        if (devManual.credito !== undefined) devolucionesCredito = parseFloat(devManual.credito) || 0;
      } else if (activeEmpresa?.id === 2 && mes === "02" && anio === "2026" && devolucionesNeto === 0) {
        // En Febrero 2026, según el F-07 oficial presentado a Hacienda:
        // Casilla 80 = 2,910.84 | Casilla 130 = 378.41
        // Casilla 81 = 738.44  | Casilla 131 = 96.00
        netoComprasGravadas = 2910.84;
        creditoComprasGravadas = 378.41;
        devolucionesNeto = 738.44;
        devolucionesCredito = 96.00;
      }

      netoComprasGravadas = Number(netoComprasGravadas.toFixed(2));
      creditoComprasGravadas = Number(creditoComprasGravadas.toFixed(2));
      devolucionesNeto = Number(devolucionesNeto.toFixed(2));
      devolucionesCredito = Number(devolucionesCredito.toFixed(2));

      const netoTotalCompras = Number((netoComprasGravadas - devolucionesNeto).toFixed(2)); // Casilla 100
      const creditoNetoCompras = Number((creditoComprasGravadas - devolucionesCredito).toFixed(2)); // Casilla 130 - Casilla 131

      res.compras = {
        neto_gravadas: netoComprasGravadas,
        credito_gravadas: creditoComprasGravadas,
        devoluciones_neto: devolucionesNeto,
        devoluciones_credito: devolucionesCredito,
        neto: netoTotalCompras,
        credito: creditoNetoCompras
      };
      res.totales = {
        debito: totalDebito,
        credito: creditoNetoCompras
      };

      // 5. Corregir remanente anterior (Casilla 110)
      const manualStored = getRemanenteManualStorage();
      if (manualStored !== null) {
        res.remanente_anterior = manualStored;
      } else if (mes === "02" && anio === "2026" && activeEmpresa.id === 2) {
        // En Febrero 2026, el remanente oficial que viene de Enero 2026 presentado en MH es 63.16
        res.remanente_anterior = 63.16;
      } else if (mes === "03" && anio === "2026" && activeEmpresa.id === 2) {
        // En Marzo 2026, el remanente oficial que viene de Febrero 2026 es 62.56
        res.remanente_anterior = 62.56;
      } else {
        // Cascada automática: consultar el remanente siguiente del mes cronológico anterior
        const curM = parseInt(mes, 10);
        const curA = parseInt(anio, 10);
        const prevM = curM === 1 ? 12 : curM - 1;
        const prevA = curM === 1 ? curA - 1 : curA;
        const prevMStr = prevM < 10 ? `0${prevM}` : `${prevM}`;
        const prevStored = localStorage.getItem(`remanente_siguiente_${activeEmpresa?.id}_${prevMStr}_${prevA}`);
        if (prevStored !== null && !isNaN(parseFloat(prevStored))) {
          res.remanente_anterior = parseFloat(prevStored);
        }
      }

      // 6. Recalcular liquidación F-07 con las cifras cuadradas
      const deb = res.totales?.debito || 0;
      const cred = res.totales?.credito || 0;
      const dif = Number((deb - cred).toFixed(2));
      const remAnterior = res.remanente_anterior || 0;
      
      let impuestoAPagar = 0;
      let remanenteSiguiente = 0;

      if (dif > 0) {
        const impDet = dif;
        const remAplicado = Math.min(impDet, remAnterior);
        const remNoUtilizado = Number((remAnterior - remAplicado).toFixed(2));
        const subtotal = Number((impDet - remAplicado).toFixed(2));
        const retRec = parseFloat(res.retenciones_recibidas || 0);
        const perRec = parseFloat(res.percepciones_recibidas || 0);
        const ant2 = parseFloat(res.anticipo_cuenta_2 || 0);
        const totalDed = retRec + perRec + ant2;
        const retEfe = parseFloat(res.retenciones_efectuadas || 0);
        const perEfe = parseFloat(res.percepciones_efectuadas || 0);
        const totalTerc = retEfe + perEfe;
        impuestoAPagar = Number(Math.max(0, subtotal - totalDed + totalTerc).toFixed(2));
        remanenteSiguiente = remNoUtilizado;
      } else {
        const excedente = Math.abs(dif);
        remanenteSiguiente = Number((excedente + remAnterior).toFixed(2));
        const retEfe = parseFloat(res.retenciones_efectuadas || 0);
        const perEfe = parseFloat(res.percepciones_efectuadas || 0);
        impuestoAPagar = Number((retEfe + perEfe).toFixed(2));
      }

      res.impuesto_a_pagar = impuestoAPagar;
      res.remanente_siguiente = remanenteSiguiente;
      }

      // No crear nuevos remanentes locales: el arrastre ordinario se obtiene del backend.
      // Las copias históricas existentes se conservan sin modificarlas.

      const cifrasPantalla = {
        debito: Number(res.totales?.debito || 0),
        credito: Number(res.totales?.credito || 0),
        impuesto: Number(res.impuesto_a_pagar || 0),
        remanente: Number(res.remanente_siguiente || 0),
        remanenteAnterior: Number(res.remanente_anterior || 0)
      };
      const nombres = { debito: "Débito fiscal", credito: "Crédito fiscal", impuesto: "Impuesto a pagar", remanente: "Remanente siguiente", remanenteAnterior: "Remanente anterior" };
      setDiferenciasServidor(Object.keys(cifrasServidor)
        .filter(campo => Math.abs(cifrasServidor[campo] - cifrasPantalla[campo]) > 0.009)
        .map(campo => ({ nombre: nombres[campo], servidor: cifrasServidor[campo], pantalla: cifrasPantalla[campo] })));
      setData(res);
      setRemanenteInput(res.remanente_anterior !== undefined ? res.remanente_anterior.toString() : "0.00");
      setAjustes({
        retenciones_recibidas: (res.retenciones_recibidas || 0).toString(),
        percepciones_recibidas: (res.percepciones_recibidas || 0).toString(),
        anticipo_cuenta_2: (res.anticipo_cuenta_2 || 0).toString(),
        retenciones_efectuadas: (res.retenciones_efectuadas || 0).toString(),
        percepciones_efectuadas: (res.percepciones_efectuadas || 0).toString()
      });
    } catch (error) {
      console.error("No se pudo cargar el conjunto completo de documentos para liquidación.", error);
      setData(null);
      setAjustesHistoricosLocales(false);
      setInventarioHistorico([]);
      setDiferenciasServidor([]);
      enqueueMessages([{ text: "No se pudo cargar la liquidación completa. No se muestran cálculos parciales; revise la conexión y vuelva a intentar.", type: "error" }]);
    } finally {
      setLoading(false);
    }
  };

  const saveRemanente = async () => {
    const val = Number(remanenteInput);
    if (!Number.isFinite(val) || val < 0) {
      enqueueMessages([{ text: "Ingrese un remanente válido, mayor o igual a cero.", type: "error" }]);
      return;
    }
    try {
      // PostgreSQL debe confirmar el guardado antes de actualizar el estado local.
      await axios.post(`${API_URL}/api/v1/liquidacion/${activeEmpresa.id}/remanente`, null, {
        params: { mes, anio, remanente: val }
      });
      // Conservar la preferencia manual histórica solo después de confirmar el servidor.
      try {
        localStorage.setItem(`remanente_manual_${activeEmpresa?.id}_${mes}_${anio}`, val.toString());
      } catch (storageError) {
        console.warn("No se pudo guardar la copia local del remanente.", storageError);
      }
      setEditRemanente(false);
      enqueueMessages([{ text: `Remanente anterior actualizado a $${val.toFixed(2)}.`, type: "success" }]);
      await fetchLiquidacion();
    } catch (error) {
      console.error("Error al guardar remanente en el servidor.", error);
      enqueueMessages([{ text: "No se guardó el remanente en el servidor. Revise la conexión e intente nuevamente.", type: "error" }]);
    }
  };

  const saveAjustes = async () => {
    try {
      const entradas = {
        remanente_anterior: remanenteInput,
        retenciones_recibidas: ajustes.retenciones_recibidas,
        percepciones_recibidas: ajustes.percepciones_recibidas,
        anticipo_cuenta_2: ajustes.anticipo_cuenta_2,
        retenciones_efectuadas: ajustes.retenciones_efectuadas,
        percepciones_efectuadas: ajustes.percepciones_efectuadas
      };
      const payload = {};
      for (const [campo, entrada] of Object.entries(entradas)) {
        const texto = String(entrada ?? "").trim();
        const valor = Number(texto);
        if (!texto || !Number.isFinite(valor) || valor < 0 || !/^\\d+(?:\\.\\d{1,2})?$/.test(texto)) {
          enqueueMessages([{ text: `Importe inválido en ${campo}. Ingrese un número no negativo con hasta dos decimales.`, type: "error" }]);
          return;
        }
        payload[campo] = valor;
      }
      await axios.post(`${API_URL}/api/v1/liquidacion/${activeEmpresa.id}/ajustes?mes=${mes}&anio=${anio}`, payload);
      enqueueMessages([{ text: "Ajustes de liquidación guardados.", type: "success" }]);
      setShowAjustes(false);
      fetchLiquidacion();
    } catch (error) {
      enqueueMessages([{ text: "Error al guardar los ajustes.", type: "error" }]);
    }
  };

  if (!activeEmpresa) return null;

  // Nunca presentar una declaración de importes cero cuando el servidor no
  // entregó todos los datos. Cero fiscal válido requiere una respuesta completa.
  if (loading || !data) {
    return (
      <main className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
        <section role={loading ? "status" : "alert"} className="w-full max-w-lg rounded-xl bg-white border border-slate-200 p-6 shadow-sm">
          <h1 className="text-xl font-bold text-slate-900">Liquidación de Impuestos F-07</h1>
          <p className="mt-2 text-slate-700">
            {loading
              ? "Cargando los documentos y cálculos del período. Espere antes de revisar o imprimir."
              : "No se pudo cargar la liquidación completa. Por seguridad, no se muestran importes ni se permite imprimir una declaración incompleta."}
          </p>
          {!loading && (
            <div className="mt-5 flex flex-wrap gap-3">
              <button type="button" onClick={() => fetchLiquidacion()} className="rounded-lg bg-indigo-600 px-4 py-2 text-white hover:bg-indigo-700">
                Reintentar carga
              </button>
              <button type="button" onClick={() => navigate("/dashboard")} className="rounded-lg border border-slate-300 px-4 py-2 text-slate-800 hover:bg-slate-100">
                Volver al panel
              </button>
            </div>
          )}
        </section>
      </main>
    );
  }

  // Cálculos detallados F-07
  const debito = data?.totales?.debito || 0;
  const credito = data?.totales?.credito || 0;
  const difPeriodo = Number((debito - credito).toFixed(2));
  
  const impDeterminado = data?.liquidacion?.impuesto_determinado !== undefined 
    ? data.liquidacion.impuesto_determinado 
    : (difPeriodo > 0 ? difPeriodo : 0);

  const excedenteCredito = data?.liquidacion?.excedente_credito !== undefined 
    ? data.liquidacion.excedente_credito 
    : (difPeriodo < 0 ? Math.abs(difPeriodo) : 0);

  const remAnterior = data?.remanente_anterior || 0;
  
  const remAplicado = data?.liquidacion?.remanente_aplicado !== undefined
    ? data.liquidacion.remanente_aplicado
    : Math.min(impDeterminado, remAnterior);

  const remNoUtilizado = data?.liquidacion?.remanente_no_utilizado !== undefined
    ? data.liquidacion.remanente_no_utilizado
    : Math.max(0, Number((remAnterior - remAplicado).toFixed(2)));

  const retRecibidas = parseFloat(ajustes.retenciones_recibidas) || 0;
  const perRecibidas = parseFloat(ajustes.percepciones_recibidas) || 0;
  const antCuenta2 = parseFloat(ajustes.anticipo_cuenta_2) || 0;
  const totalDeducciones = Number((retRecibidas + perRecibidas + antCuenta2).toFixed(2));

  const retEfectuadas = parseFloat(ajustes.retenciones_efectuadas) || 0;
  const perEfectuadas = parseFloat(ajustes.percepciones_efectuadas) || 0;
  const totalTerceros = Number((retEfectuadas + perEfectuadas).toFixed(2));

  const impuestoAPagar = data?.impuesto_a_pagar || 0;
  const remanenteSiguiente = data?.remanente_siguiente || 0;

  return (
    <div className="bg-slate-50 min-h-screen pb-12 font-sans">
      {data?.estado_normativo_f07?.conciliacion_completa === false && (
        <div role="alert" className="max-w-4xl mx-auto mt-4 px-4 sm:px-6 lg:px-8">
          <div className="rounded-lg border border-amber-400 bg-amber-50 p-4 text-amber-950">
            <p className="font-bold">F-07 pendiente de conciliación normativa</p>
            <p className="text-sm mt-1">{data.estado_normativo_f07.advertencia}</p>
            <p className="text-sm mt-1">Los importes de remanente y excedente mostrados son provisionales y requieren validación antes de presentar una declaración.</p>
          </div>
        </div>
      )}
      {data?.casillas_f07_preliminares && (
        <section aria-label="Conciliación de casillas F-07" className="max-w-4xl mx-auto mt-4 px-4 sm:px-6 lg:px-8">
          <div className="rounded-lg border border-slate-300 bg-white p-4">
            <h2 className="font-bold text-slate-900">Conciliación de saldos F-07 (preliminar)</h2>
            <p className="text-sm text-slate-700 mt-1">La casilla 155 corresponde al crédito fiscal; la 167 corresponde a un excedente de impuesto diferente. Los valores pendientes no equivalen a cero.</p>
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
              {[
                ["110", "Crédito fiscal anterior"],
                ["155", "Crédito fiscal siguiente"],
                ["164", "Excedente de impuesto anterior"],
                ["167", "Excedente de impuesto siguiente"],
                ["168", "Impuesto a pagar"],
                ["203", "Ajustes del impuesto"]
              ].map(([casilla, descripcion]) => {
                const importe = data.casillas_f07_preliminares[casilla];
                const disponible = typeof importe === "number" && Number.isFinite(importe);
                return (
                  <div key={casilla} className="rounded-md bg-slate-50 p-3">
                    <dt className="text-sm text-slate-700">Casilla {casilla} — {descripcion}</dt>
                    <dd className="font-semibold text-slate-900 mt-1">
                      {disponible ? `${importe.toFixed(2)} (provisional)` : "Pendiente de conciliación"}
                    </dd>
                  </div>
                );
              })}
            </dl>
          </div>
        </section>
      )}
      {data?.casillas_f07_preliminares && (
        <section aria-label="Respaldo documental de casilla 164" className="max-w-4xl mx-auto mt-4 px-4 sm:px-6 lg:px-8">
          <div className="rounded-lg border border-slate-300 bg-white p-4">
            <h2 className="font-bold text-slate-900">Trazabilidad de la casilla 164</h2>
            <p role="status" className="mt-2 text-sm font-semibold text-amber-900">Estado fiscal: pendiente de revisión y aceptación. La coincidencia documental no significa aprobación del F-07.</p>
            {auditoria164.estado === 'disponible' && auditoria164.respaldo ? (
              <div>
                <p className="mt-2 text-sm font-semibold text-slate-800">Respaldo registrado y coincidente con el saldo almacenado.</p>
                <dl className="mt-2 text-sm text-slate-800 space-y-1">
                <div><dt className="inline font-semibold">Origen: </dt><dd className="inline">{auditoria164.respaldo.origen}</dd></div>
                <div><dt className="inline font-semibold">Referencia: </dt><dd className="inline">{auditoria164.respaldo.referencia}</dd></div>
                <div><dt className="inline font-semibold">Importe registrado: </dt><dd className="inline">{Number(auditoria164.respaldo.importe).toFixed(2)}</dd></div>
                <div><dt className="inline font-semibold">Usuario de registro: </dt><dd className="inline">{auditoria164.respaldo.usuario_id}</dd></div>
                <div><dt className="inline font-semibold">Fecha de registro: </dt><dd className="inline">{auditoria164.respaldo.registrado_en || 'No disponible'}</dd></div>
                </dl>
              </div>
            ) : (
              <p role="status" className="text-sm mt-2 text-amber-900">
                {auditoria164.estado === 'saldo_sin_auditoria'
                  ? 'Existe un saldo 164 registrado sin respaldo auditado. Requiere conciliación documental.'
                  : auditoria164.estado === 'sin_respaldo'
                  ? 'No existe respaldo auditado para este período; esto no significa que el saldo sea cero.'
                  : auditoria164.estado === 'discrepancia'
                    ? 'ALERTA: discrepancia entre el saldo 164 y su respaldo auditado. No presente la declaración hasta conciliar los importes y documentos.'
                  : auditoria164.estado === 'sin_autorizacion'
                    ? 'No se pudo verificar el respaldo de la casilla 164 por falta de autorización o sesión válida. No presente la declaración sin verificar el acceso y conciliar el saldo.'
                  : auditoria164.estado === 'error'
                    ? 'No fue posible consultar el respaldo de la casilla 164. Verifique la conexión o la disponibilidad de la migración.'
                    : 'Consultando respaldo documental…'}
              </p>
            )}
            <p className="text-xs text-slate-600 mt-2">El respaldo documenta el origen del saldo; no certifica por sí mismo la conciliación normativa del F-07.</p>
          </div>
        </section>
      )}
      {ajustesHistoricosLocales && (
        <div role="status" className="max-w-4xl mx-auto mt-4 px-4 sm:px-6 lg:px-8">
          <div className="rounded-lg border border-amber-400 bg-amber-50 p-4 text-amber-950">
            <p className="font-bold">Liquidación con ajustes históricos locales</p>
            <p className="text-sm mt-1">Esta liquidación utiliza datos o reglas históricas del navegador que todavía no han sido conciliados con PostgreSQL. Aunque no aparezcan diferencias numéricas, confirme los importes antes de presentar el F-07. No borre los datos del navegador hasta completar la migración.</p>
            <p className="font-semibold text-sm mt-3">Inventario de ajustes detectados para este período:</p>
            <ul className="mt-1 list-disc pl-5 text-sm">
              {inventarioHistorico.map((detalle, indice) => <li key={indice}>{detalle}</li>)}
            </ul>
          </div>
        </div>
      )}
      {diferenciasServidor.length > 0 && (
        <div role="alert" className="max-w-4xl mx-auto mt-4 px-4 sm:px-6 lg:px-8">
          <div className="rounded-lg border border-amber-400 bg-amber-50 p-4 text-amber-950">
            <p className="font-bold">Atención: diferencias entre servidor y pantalla</p>
            <p className="text-sm mt-1">Los ajustes históricos o cálculos locales modifican importes recibidos del servidor. Revise estos valores antes de presentar una declaración.</p>
            <ul className="mt-2 list-disc pl-5 text-sm">
              {diferenciasServidor.map(item => (
                <li key={item.nombre}>{item.nombre}: servidor ${item.servidor.toFixed(2)}; pantalla ${item.pantalla.toFixed(2)}</li>
              ))}
            </ul>
          </div>
        </div>
      )}
      {/* Header */}
      <div className="bg-indigo-600 border-b border-indigo-700 sticky top-0 z-30 shadow-md">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <button 
                onClick={() => navigate("/dashboard")}
                className="text-indigo-100 hover:text-white transition p-1 rounded-lg hover:bg-indigo-500/50"
                title="Volver al Dashboard"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
              </button>
              <div>
                <h1 className="text-xl font-bold text-white flex items-center">
                  Liquidación de Impuestos F-07
                  <span className="ml-3 text-xs bg-indigo-500 text-indigo-100 px-2 py-0.5 rounded-full font-normal border border-indigo-400">
                    Ministerio de Hacienda El Salvador
                  </span>
                </h1>
                <p className="text-sm text-indigo-200">
                  Empresa: <span className="font-semibold text-white">{activeEmpresa.razon_social}</span> | Período: <span className="font-medium text-white">{mes}/{anio}</span>
                </p>
              </div>
            </div>
            
            <div className="flex items-center space-x-3">
              <button 
                onClick={() => {
                  if (!data || loading) {
                    enqueueMessages([{ text: "Espere a que se cargue la liquidación completa antes de imprimir.", type: "error" }]);
                    return;
                  }
                  if (['discrepancia', 'sin_autorizacion', 'error', 'pendiente'].includes(auditoria164.estado) || ajustesHistoricosLocales || diferenciasServidor.length > 0 || data?.estado_normativo_f07?.conciliacion_completa === false) {
                    const confirmar = window.confirm(
                      "ATENCIÓN: esta liquidación puede contener una discrepancia documental de la casilla 164, ajustes históricos locales o diferencias pendientes de conciliación. " +
                      "El cálculo puede estar pendiente de conciliación normativa. La impresión no equivale a una declaración verificada. ¿Desea imprimirla de todos modos?"
                    );
                    if (!confirmar) return;
                  }
                  window.print();
                }}
                disabled={!data || loading}
                aria-label="Imprimir liquidación F-07"
                title={!data || loading ? "Espere a que se cargue la liquidación" : "Imprimir liquidación"}
                className="bg-indigo-500 hover:bg-indigo-400 text-white px-4 py-2 rounded-lg text-sm font-medium transition shadow-sm flex items-center border border-indigo-400 cursor-pointer"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" /></svg>
                Imprimir
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {loading || !data ? (
          <div className="flex flex-col items-center justify-center py-20 text-slate-500 space-y-3">
            <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
            <span>Calculando liquidación del impuesto...</span>
          </div>
        ) : (
          <div className="space-y-6">
            
            {/* Débito Fiscal */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
              <div className="bg-sky-50 px-6 py-4 border-b border-sky-100 flex justify-between items-center">
                <h2 className="text-base font-bold text-sky-900 flex items-center">
                  <span className="w-7 h-7 rounded-lg bg-sky-600 text-white flex items-center justify-center mr-3 text-xs font-bold">1</span>
                  Operaciones de Venta (Débito Fiscal)
                </h2>
                <span className="text-xs bg-sky-200/70 text-sky-800 font-semibold px-2.5 py-1 rounded">
                  Casilla 150 F-07
                </span>
              </div>
              <div className="p-0">
                <table className="w-full text-sm text-left text-slate-600">
                  <thead className="bg-slate-50 text-slate-500 uppercase text-xs">
                    <tr>
                      <th className="px-6 py-3 font-semibold">Concepto</th>
                      <th className="px-6 py-3 font-semibold text-right w-40">Valor Neto</th>
                      <th className="px-6 py-3 font-semibold text-right w-40">Débito Fiscal</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    <tr className="hover:bg-slate-50">
                      <td className="px-6 py-3 font-medium text-slate-700">
                        <div className="flex items-center space-x-2">
                          <span>Ventas a Consumidor Final (Facturas Electrónicas / Físicas)</span>
                          {data.anulados_cf_count > 0 && (
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-700 border border-rose-300">
                              {data.anulados_cf_count} anulado{data.anulados_cf_count > 1 ? 's' : ''} excluido{data.anulados_cf_count > 1 ? 's' : ''}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-3 text-right">${data.ventas_cf.neto.toFixed(2)}</td>
                      <td className="px-6 py-3 text-right font-medium text-slate-900">${data.ventas_cf.debito.toFixed(2)}</td>
                    </tr>
                    <tr className="hover:bg-slate-50">
                      <td className="px-6 py-3 font-medium text-slate-700">
                        <div className="flex items-center space-x-2">
                          <span>Ventas a Contribuyentes (Comprobantes de Crédito Fiscal CCF)</span>
                          {data.anulados_ccf_count > 0 && (
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-700 border border-rose-300">
                              {data.anulados_ccf_count} anulado{data.anulados_ccf_count > 1 ? 's' : ''} excluido{data.anulados_ccf_count > 1 ? 's' : ''}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-3 text-right">${data.ventas_ccf.neto.toFixed(2)}</td>
                      <td className="px-6 py-3 text-right font-medium text-slate-900">${data.ventas_ccf.debito.toFixed(2)}</td>
                    </tr>
                  </tbody>
                  <tfoot className="bg-sky-50/70 font-bold border-t border-sky-100">
                    <tr>
                      <td className="px-6 py-3 text-sky-900 text-right" colSpan="2">TOTAL DÉBITO FISCAL (Casilla 150):</td>
                      <td className="px-6 py-3 text-right text-sky-900 text-lg">${debito.toFixed(2)}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>

            {/* Crédito Fiscal */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
              <div className="bg-amber-50 px-6 py-4 border-b border-amber-100 flex justify-between items-center">
                <h2 className="text-base font-bold text-amber-900 flex items-center">
                  <span className="w-7 h-7 rounded-lg bg-amber-600 text-white flex items-center justify-center mr-3 text-xs font-bold">2</span>
                  Operaciones de Compra (Crédito Fiscal)
                </h2>
                <span className="text-xs bg-amber-200/70 text-amber-800 font-semibold px-2.5 py-1 rounded">
                  Renglones 30, 32 y 42 F-07
                </span>
              </div>
              <div className="p-0">
                <table className="w-full text-sm text-left text-slate-600">
                  <thead className="bg-slate-50 text-slate-500 uppercase text-xs">
                    <tr>
                      <th className="px-6 py-3 font-semibold">Concepto</th>
                      <th className="px-6 py-3 font-semibold text-right w-40">Valor Neto</th>
                      <th className="px-6 py-3 font-semibold text-right w-40">Crédito Fiscal</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    <tr className="hover:bg-slate-50">
                      <td className="px-6 py-3 font-medium text-slate-700">
                        Compras Internas Gravadas (Casilla 80 / Casilla 130)
                      </td>
                      <td className="px-6 py-3 text-right font-medium text-slate-900">
                        ${(data.compras.neto_gravadas !== undefined ? data.compras.neto_gravadas : data.compras.neto).toFixed(2)}
                      </td>
                      <td className="px-6 py-3 text-right font-medium text-slate-900">
                        ${(data.compras.credito_gravadas !== undefined ? data.compras.credito_gravadas : data.compras.credito).toFixed(2)}
                      </td>
                    </tr>
                    <tr className="hover:bg-slate-50 bg-rose-50/40">
                      <td className="px-6 py-3 font-medium text-rose-800">
                        <div className="flex items-center justify-between">
                          <span>(-) Devoluciones, Rebajas y Deducciones s/ Compras (Casilla 81 / Casilla 131)</span>
                          <button
                            type="button"
                            onClick={() => {
                              setDevNetoInput((data.compras.devoluciones_neto || 0).toString());
                              setDevCredInput((data.compras.devoluciones_credito || 0).toString());
                              setEditDevoluciones(!editDevoluciones);
                            }}
                            className="text-rose-600 hover:text-rose-800 p-1 hover:bg-rose-100 rounded transition ml-2 text-xs font-semibold inline-flex items-center space-x-1 cursor-pointer"
                            title="Ajustar devoluciones sobre compras"
                          >
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
                            <span>{editDevoluciones ? "Cerrar" : "Editar"}</span>
                          </button>
                        </div>
                      </td>
                      <td className="px-6 py-3 text-right text-rose-700 font-mono font-medium">
                        -${(data.compras.devoluciones_neto || 0).toFixed(2)}
                      </td>
                      <td className="px-6 py-3 text-right text-rose-700 font-mono font-bold">
                        -${(data.compras.devoluciones_credito || 0).toFixed(2)}
                      </td>
                    </tr>
                    {editDevoluciones && (
                      <tr className="bg-amber-50/80 border-t border-b border-amber-200">
                        <td className="px-6 py-2.5 text-xs text-amber-900 font-medium">
                          Modificar Casillas 81 (Neto) y 131 (Crédito Fiscal) de Devoluciones:
                        </td>
                        <td className="px-6 py-2.5 text-right">
                          <input
                            type="number"
                            step="0.01"
                            value={devNetoInput}
                            onChange={(e) => setDevNetoInput(e.target.value)}
                            placeholder="Valor Neto (81)"
                            className="w-28 border border-amber-300 rounded px-2 py-1 text-right text-xs focus:ring-2 focus:ring-amber-500 bg-white"
                          />
                        </td>
                        <td className="px-6 py-2.5 text-right">
                          <div className="flex items-center justify-end space-x-2">
                            <input
                              type="number"
                              step="0.01"
                              value={devCredInput}
                              onChange={(e) => setDevCredInput(e.target.value)}
                              placeholder="Crédito (131)"
                              className="w-28 border border-amber-300 rounded px-2 py-1 text-right text-xs focus:ring-2 focus:ring-amber-500 bg-white"
                            />
                            <button
                              type="button"
                              onClick={() => saveDevoluciones(devNetoInput, devCredInput)}
                              className="bg-amber-600 text-white px-2.5 py-1 rounded text-xs font-bold hover:bg-amber-700 cursor-pointer"
                            >
                              OK
                            </button>
                          </div>
                        </td>
                      </tr>
                    )}
                  </tbody>
                  <tfoot className="bg-amber-50/70 font-bold border-t border-amber-100">
                    <tr>
                      <td className="px-6 py-3 text-amber-900 text-right">SUMA DE COMPRAS (Casilla 100):</td>
                      <td className="px-6 py-3 text-right text-amber-900 font-bold">${data.compras.neto.toFixed(2)}</td>
                      <td className="px-6 py-3 text-right text-amber-900 text-lg">${credito.toFixed(2)}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>

            {/* Liquidación Formal del Impuesto F-07 */}
            <div className="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden">
              <div className="bg-slate-800 px-6 py-4 flex justify-between items-center text-white">
                <h2 className="text-lg font-bold flex items-center">
                  <svg className="w-5 h-5 mr-2 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>
                  Determinación y Liquidación del Impuesto (F-07)
                </h2>
                <span className="text-xs bg-slate-700 text-slate-300 px-3 py-1 rounded-full font-medium border border-slate-600">
                  Ley de IVA Arts. 64-66
                </span>
              </div>
              
              <div className="p-6 space-y-6">

                {/* Paso A: Comparación de Operaciones del Período */}
                <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 space-y-3">
                  <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 flex items-center justify-between">
                    <span>Paso 1: Resultado de Operaciones del Período</span>
                    <span className="text-slate-400 font-normal">Débito vs. Crédito</span>
                  </div>

                  <div className="flex justify-between items-center text-sm text-slate-700">
                    <span className="flex items-center">
                      <span className="w-5 h-5 rounded-full bg-sky-100 text-sky-800 flex items-center justify-center text-xs font-bold mr-2">+</span>
                      Total Débito Fiscal del Período (Casilla 150)
                    </span>
                    <span className="font-semibold text-slate-900">${debito.toFixed(2)}</span>
                  </div>

                  <div className="flex justify-between items-center text-sm text-slate-700">
                    <span className="flex items-center">
                      <span className="w-5 h-5 rounded-full bg-amber-100 text-amber-800 flex items-center justify-center text-xs font-bold mr-2">-</span>
                      Total Crédito Fiscal Neto de Compras (Casilla 130 - Casilla 131)
                    </span>
                    <span className="font-semibold text-slate-900">${credito.toFixed(2)}</span>
                  </div>

                  {/* Subtotal del Período */}
                  <div className="pt-3 border-t border-slate-200">
                    {impDeterminado > 0 ? (
                      <div className="bg-amber-50/80 border border-amber-200 rounded-lg p-3 flex justify-between items-center">
                        <div>
                          <div className="font-bold text-amber-900 text-sm flex items-center">
                            Impuesto Determinado del Período (Casilla 160)
                            <span className="ml-2 text-xs bg-amber-200 text-amber-800 px-2 py-0.5 rounded font-normal">
                              Débito {'>'} Crédito
                            </span>
                          </div>
                          <p className="text-xs text-amber-700 mt-0.5">
                            Las ventas superaron a las compras por ${(debito - credito).toFixed(2)}. Este es el impuesto base generado en el mes.
                          </p>
                        </div>
                        <span className="text-lg font-bold text-amber-900 ml-4">${impDeterminado.toFixed(2)}</span>
                      </div>
                    ) : excedenteCredito > 0 ? (
                      <div className="bg-sky-50/80 border border-sky-200 rounded-lg p-3 flex justify-between items-center">
                        <div>
                          <div className="font-bold text-sky-900 text-sm flex items-center">
                            Excedente de Crédito Fiscal del Período (Casilla 155)
                            <span className="ml-2 text-xs bg-sky-200 text-sky-800 px-2 py-0.5 rounded font-normal">
                              Crédito {'>'} Débito
                            </span>
                          </div>
                          <p className="text-xs text-sky-700 mt-0.5">
                            Las compras superaron a las ventas por ${(credito - debito).toFixed(2)}. Saldo a favor originado en el mes.
                          </p>
                        </div>
                        <span className="text-lg font-bold text-sky-900 ml-4">${excedenteCredito.toFixed(2)}</span>
                      </div>
                    ) : (
                      <div className="bg-slate-100 rounded-lg p-3 flex justify-between items-center text-sm font-medium text-slate-700">
                        <span>Diferencia de Operaciones del Período</span>
                        <span>$0.00</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Paso B: Aplicación del Remanente del Mes Anterior */}
                <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 space-y-3">
                  <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 flex items-center justify-between">
                    <span>Paso 2: Aplicación del Remanente de Crédito Fiscal Anterior</span>
                    <span className="text-slate-400 font-normal">Casilla 110 F-07</span>
                  </div>

                  <div className="flex justify-between items-center text-sm text-slate-700">
                    <div className="flex items-center">
                      <span className="font-medium text-slate-800">Remanente de Crédito Fiscal del Mes Anterior (Casilla 110)</span>
                      <button 
                        onClick={() => setEditRemanente(!editRemanente)} 
                        className="ml-2 text-indigo-600 hover:text-indigo-800 p-1 hover:bg-indigo-50 rounded transition"
                        title="Modificar remanente anterior"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
                      </button>
                    </div>

                    {editRemanente ? (
                      <div className="flex items-center space-x-2">
                        <span className="text-slate-500">$</span>
                        <input 
                          type="number" 
                          step="0.01" 
                          value={remanenteInput} 
                          onChange={(e) => setRemanenteInput(e.target.value)}
                          onKeyDown={(e) => e.key === 'Enter' && saveRemanente()}
                          autoFocus
                          className="w-24 border border-indigo-300 rounded px-2 py-1 text-right text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                        />
                        <button onClick={saveRemanente} className="bg-indigo-600 text-white px-2.5 py-1 rounded text-xs font-bold hover:bg-indigo-700 cursor-pointer">OK</button>
                        <button onClick={() => setEditRemanente(false)} className="bg-slate-200 text-slate-700 px-2 py-1 rounded text-xs cursor-pointer">✕</button>
                      </div>
                    ) : (
                      <span className="font-semibold text-slate-900">${remAnterior.toFixed(2)}</span>
                    )}
                  </div>

                  {/* Desglose de Compensación */}
                  {impDeterminado > 0 ? (
                    <div className="space-y-2 pt-2 border-t border-slate-200 text-sm">
                      <div className="flex justify-between items-center text-slate-600">
                        <span className="flex items-center pl-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 mr-2"></span>
                          (-) Remanente aplicado para absorber Impuesto Determinado:
                        </span>
                        <span className="font-medium text-emerald-700">-${remAplicado.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between items-center text-slate-600">
                        <span className="flex items-center pl-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-slate-400 mr-2"></span>
                          Remanente de meses anteriores no utilizado:
                        </span>
                        <span className="font-medium text-slate-700">${remNoUtilizado.toFixed(2)}</span>
                      </div>
                    </div>
                  ) : (
                    <div className="pt-2 border-t border-slate-200 text-xs text-slate-500 pl-2">
                      Al no existir impuesto determinado en el mes, el remanente anterior (${remAnterior.toFixed(2)}) se acumula íntegro al saldo a favor.
                    </div>
                  )}
                </div>

                {/* Paso C: Ajustes F-07 (Retenciones / Percepciones / Anticipos) - Opcional */}
                <div className="border border-slate-200 rounded-xl overflow-hidden">
                  <button 
                    type="button" 
                    onClick={() => setShowAjustes(!showAjustes)}
                    className="w-full bg-slate-100 hover:bg-slate-200/80 px-4 py-2.5 text-xs font-bold text-slate-700 flex justify-between items-center transition"
                  >
                    <span className="flex items-center">
                      <svg className="w-4 h-4 mr-1.5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" /></svg>
                      Ajustes Adicionales F-07 (Retenciones 1%, Percepciones 1%, Anticipo 2%)
                      {(totalDeducciones > 0 || totalTerceros > 0) && (
                        <span className="ml-2 bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full font-bold">Activo</span>
                      )}
                    </span>
                    <span>{showAjustes ? "Ocultar ▲" : "Configurar / Ver ▼"}</span>
                  </button>

                  {showAjustes && (
                    <div className="p-4 bg-white space-y-4 text-sm">
                      <p className="text-xs text-slate-500">
                        Si en este período tus clientes te efectuaron retenciones de IVA (1%), tus proveedores te percibieron (1%) o pagaste anticipo a cuenta del 2%, regístralos aquí:
                      </p>
                      
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-xs font-semibold text-slate-600 mb-1">
                            (-) IVA Retenido por Clientes (Casilla 161)
                          </label>
                          <input 
                            type="number" 
                            step="0.01" 
                            value={ajustes.retenciones_recibidas}
                            onChange={(e) => setAjustes({...ajustes, retenciones_recibidas: e.target.value})}
                            className="w-full border border-slate-300 rounded px-3 py-1.5 text-right text-sm"
                            placeholder="0.00"
                          />
                        </div>

                        <div>
                          <label className="block text-xs font-semibold text-slate-600 mb-1">
                            (-) IVA Percibido por Proveedores (Casilla 162)
                          </label>
                          <input 
                            type="number" 
                            step="0.01" 
                            value={ajustes.percepciones_recibidas}
                            onChange={(e) => setAjustes({...ajustes, percepciones_recibidas: e.target.value})}
                            className="w-full border border-slate-300 rounded px-3 py-1.5 text-right text-sm"
                            placeholder="0.00"
                          />
                        </div>

                        <div>
                          <label className="block text-xs font-semibold text-slate-600 mb-1">
                            (-) Anticipo a Cuenta del 2% (Casilla 163)
                          </label>
                          <input 
                            type="number" 
                            step="0.01" 
                            value={ajustes.anticipo_cuenta_2}
                            onChange={(e) => setAjustes({...ajustes, anticipo_cuenta_2: e.target.value})}
                            className="w-full border border-slate-300 rounded px-3 py-1.5 text-right text-sm"
                            placeholder="0.00"
                          />
                        </div>

                        <div>
                          <label className="block text-xs font-semibold text-slate-600 mb-1">
                            (+) Retenciones/Percepciones a Terceros a Enterar
                          </label>
                          <input 
                            type="number" 
                            step="0.01" 
                            value={ajustes.retenciones_efectuadas}
                            onChange={(e) => setAjustes({...ajustes, retenciones_efectuadas: e.target.value})}
                            className="w-full border border-slate-300 rounded px-3 py-1.5 text-right text-sm"
                            placeholder="0.00"
                          />
                        </div>
                      </div>

                      <div className="flex justify-end pt-2">
                        <button 
                          onClick={saveAjustes}
                          className="bg-indigo-600 text-white text-xs font-bold px-4 py-2 rounded-lg hover:bg-indigo-700 transition"
                        >
                          Guardar Ajustes
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {/* Paso D: Tarjetas de Resultado Final */}
                <div className="pt-4 border-t-2 border-slate-200">
                  {impuestoAPagar > 0 ? (
                    <div className="bg-red-50 p-5 rounded-xl border border-red-200 space-y-2">
                      <div className="flex justify-between items-center">
                        <div>
                          <span className="text-red-900 font-extrabold text-lg flex items-center">
                            <span className="w-3 h-3 rounded-full bg-red-600 mr-2"></span>
                            Total Impuesto a Pagar (F-07 Casilla 165)
                          </span>
                          <p className="text-xs text-red-700 mt-0.5">
                            Monto a cancelar en mandamiento de pago del Ministerio de Hacienda.
                          </p>
                        </div>
                        <span className="text-red-700 font-black text-3xl">${impuestoAPagar.toFixed(2)}</span>
                      </div>
                      <div className="text-xs text-red-600 border-t border-red-200/60 pt-2 flex justify-between">
                        <span>Remanente para período siguiente:</span>
                        <span className="font-bold">$0.00</span>
                      </div>
                    </div>
                  ) : (
                    <div className="bg-emerald-50 p-5 rounded-xl border border-emerald-200 space-y-2">
                      <div className="flex justify-between items-center">
                        <div>
                          <span className="text-emerald-900 font-extrabold text-lg flex items-center">
                            <span className="w-3 h-3 rounded-full bg-emerald-600 mr-2"></span>
                            Remanente de Crédito Fiscal para el Siguiente Mes
                          </span>
                          <p className="text-xs text-emerald-700 mt-0.5">
                            Saldo a favor que se trasladará a la Casilla 110 del período {String(Number(mes) === 12 ? 1 : Number(mes) + 1).padStart(2, '0')}/{Number(mes) === 12 ? Number(anio) + 1 : anio}.
                          </p>
                        </div>
                        <span className="text-emerald-700 font-black text-3xl">${remanenteSiguiente.toFixed(2)}</span>
                      </div>
                      
                      <div className="text-xs text-emerald-800 border-t border-emerald-200/70 pt-2 flex justify-between items-center">
                        <span>
                          {impDeterminado > 0 ? (
                            <>
                              Conciliación: Remanente anterior (${remAnterior.toFixed(2)}) menos ${remAplicado.toFixed(2)} absorbido en este mes = <strong className="font-bold">${remanenteSiguiente.toFixed(2)}</strong>.
                            </>
                          ) : (
                            <>
                              Conciliación: Excedente del mes (${excedenteCredito.toFixed(2)}) + Remanente anterior (${remAnterior.toFixed(2)}) = <strong className="font-bold">${remanenteSiguiente.toFixed(2)}</strong>.
                            </>
                          )}
                        </span>
                        <span className="font-bold bg-emerald-200/80 text-emerald-900 px-2 py-0.5 rounded">
                          Impuesto a Pagar: $0.00
                        </span>
                      </div>
                    </div>
                  )}
                </div>
                
              </div>
            </div>
            
          </div>
        )}
      </div>
    </div>
  );
}
