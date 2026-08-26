import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function Terminos() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, login } = useAuth();
  const [accepted, setAccepted] = useState(false);
  const [loading, setLoading] = useState(false);
  
  const fromGuard = location.state?.fromGuard || false;

  const handleAccept = async () => {
    if (!accepted) return;
    setLoading(true);
    try {
      await axios.post(`${API_URL}/api/v1/auth/aceptar-terminos`, { usuario_id: user.id });
      // Update local storage and context
      const userData = JSON.parse(localStorage.getItem('user'));
      if (userData) {
        userData.terminos_aceptados = true;
        localStorage.setItem('user', JSON.stringify(userData));
        login(userData, localStorage.getItem('token'));
      }
      navigate('/dashboard');
    } catch (error) {
      console.error("Error aceptando términos:", error);
      alert("Hubo un error al guardar tu aceptación. Intenta nuevamente.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f8fafc', padding: '3rem 1rem' }}>
      <div style={{ maxWidth: '800px', margin: '0 auto', backgroundColor: 'white', padding: '2rem', borderRadius: '1rem', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}>
        
        <h1 style={{ fontSize: '1.875rem', fontWeight: 'bold', color: '#0f172a', marginBottom: '0.5rem' }}>Términos de Referencia y Condiciones</h1>
        <p style={{ color: '#64748b', marginBottom: '2rem' }}>Última actualización: 26 de Agosto de 2026</p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', color: '#334155', lineHeight: '1.6' }}>
          <p>
            Bienvenido al <strong>Sistema de Declaraciones de IVA SaaS</strong> (en adelante, "la Plataforma"). Al registrar su empresa y utilizar nuestros servicios, usted acepta estar sujeto a los siguientes Términos de Referencia y Condiciones de Servicio. Si no está de acuerdo con alguna parte de estos términos, no podrá acceder a la Plataforma.
          </p>

          <section>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#0f172a', marginBottom: '0.5rem' }}>1. Naturaleza del Servicio</h3>
            <p>La Plataforma es un software alojado en la nube (SaaS - Software as a Service) diseñado para proveer a las empresas y contadores herramientas automatizadas para la clasificación, validación y procesamiento de Documentos Tributarios Electrónicos (DTEs), generación automática de anexos de Compras y Ventas (F07), y conciliación de liquidación mensual de impuestos. La Plataforma actúa exclusivamente como una herramienta informática para agilizar sus procesos tributarios.</p>
          </section>

          <section>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#0f172a', marginBottom: '0.5rem' }}>2. Cumplimiento Legal y Normativo</h3>
            <p>La Plataforma ha sido desarrollada alineada a las mejores prácticas y regulaciones fiscales, incluyendo:</p>
            <ul style={{ paddingLeft: '1.5rem', listStyleType: 'disc', marginTop: '0.5rem' }}>
              <li><strong>Validación del Ministerio de Hacienda:</strong> El sistema procesa exclusivamente archivos JSON estructurados bajo la normativa de Facturación Electrónica vigente (DTEs), rechazando proactivamente documentos inválidos o que no correspondan a la clasificación fiscal de su empresa.</li>
              <li><strong>Ley del IVA:</strong> La Plataforma clasifica automáticamente transacciones de Comprobantes de Crédito Fiscal (03), Facturas de Consumidor Final (01), y Notas de Crédito/Débito, asegurando la separación correcta de operaciones gravadas, exentas y cálculo del 13%.</li>
              <li><strong>No sustitución Profesional:</strong> La Plataforma automatiza los cálculos y consolida anexos, pero NO sustituye el criterio fiscal, análisis y declaración final que debe realizar su profesional contable autorizado ante las entidades correspondientes.</li>
            </ul>
          </section>

          <section>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#0f172a', marginBottom: '0.5rem' }}>3. Licenciamiento y Modelos de Uso</h3>
            <p>La Plataforma se ofrece bajo diferentes modalidades de licencia, las cuales pueden variar según el plan elegido:</p>
            <ul style={{ paddingLeft: '1.5rem', listStyleType: 'disc', marginTop: '0.5rem' }}>
              <li><strong>Versión Gratuita (Freeware con Publicidad):</strong> El uso de la plataforma puede ser gratuito sujeto a la visualización de anuncios publicitarios de terceros y límites en la cantidad de comprobantes o transacciones procesadas mensualmente.</li>
              <li><strong>Período de Prueba (Trial de 30 Días):</strong> Podrá disponer de un período de prueba gratuito de 30 días con todas las funciones Premium habilitadas (procesamiento ilimitado, integración completa con Gmail, y soporte de facturas y créditos fiscales sin límite). Transcurrido este tiempo, deberá adquirir una suscripción Premium o su cuenta pasará automáticamente a la versión gratuita con restricciones.</li>
              <li><strong>Suscripciones Premium:</strong> Versiones libres de publicidad, con procesamiento de DTEs ilimitado, importación masiva avanzada, y soporte técnico preferencial.</li>
            </ul>
          </section>

          <section>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#0f172a', marginBottom: '0.5rem' }}>4. Integración con Plataformas de Terceros (Gmail)</h3>
            <p>La Plataforma ofrece una herramienta opcional para importar automáticamente archivos JSON de DTEs desde su cuenta de Gmail. Al utilizar esta herramienta:</p>
            <ul style={{ paddingLeft: '1.5rem', listStyleType: 'disc', marginTop: '0.5rem' }}>
              <li>Usted otorga permiso de lectura estrictamente limitado a los correos electrónicos para extraer archivos adjuntos de extensión JSON.</li>
              <li>La Plataforma no almacena el contenido de sus mensajes personales, contraseñas, ni se comunica en su nombre. Los tokens de acceso son temporales y se utilizan bajo demanda exclusivamente para la extracción de documentos tributarios.</li>
            </ul>
          </section>

          <section>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#0f172a', marginBottom: '0.5rem' }}>5. Privacidad y Confidencialidad de los Datos</h3>
            <ul style={{ paddingLeft: '1.5rem', listStyleType: 'disc', marginTop: '0.5rem' }}>
              <li><strong>Aislamiento de Datos (Multi-Tenant):</strong> Garantizamos que la información tributaria y los DTEs importados de su empresa están estrictamente aislados y son inaccesibles para otras empresas que utilicen la Plataforma.</li>
              <li><strong>Propiedad de los Datos:</strong> Usted retiene todos los derechos sobre la información financiera procesada. La Plataforma únicamente actúa como medio tecnológico para su visualización y consolidación.</li>
            </ul>
          </section>

          <section>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#0f172a', marginBottom: '0.5rem' }}>6. Copias de Seguridad y Respaldo de Datos (Backups)</h3>
            <div style={{ backgroundColor: '#fffbeb', border: '1px solid #fde68a', borderRadius: '0.5rem', padding: '1rem', marginTop: '1rem', marginBottom: '1rem' }}>
              <p style={{ color: '#92400e', fontWeight: 'bold', marginBottom: '0.5rem' }}>⚠️ CLÁUSULA IMPORTANTE — Léase detenidamente</p>
              <p style={{ color: '#b45309', fontSize: '0.875rem' }}>El contenido de esta sección establece las responsabilidades del usuario final respecto al respaldo y recuperación de su información tributaria procesada en la Plataforma.</p>
            </div>
            <ul style={{ paddingLeft: '1.5rem', listStyleType: 'disc', marginTop: '0.5rem' }}>
              <li><strong>Responsabilidad Exclusiva del Usuario:</strong> El usuario final (contador, administrador o representante) es el único y exclusivo responsable de realizar, gestionar y verificar las copias de seguridad de toda la información generada en la Plataforma (exportaciones CSV, listados consolidados de compras/ventas, DTEs importados).</li>
              <li><strong>Exoneración de Responsabilidad:</strong> demiempresa, sus desarrolladores y asociados no se hacen responsables bajo ninguna circunstancia por la pérdida, eliminación accidental o inaccesibilidad de datos derivada de la falta de respaldos por parte del usuario, incluyendo eliminaciones manuales solicitadas al sistema, errores humanos, accesos no autorizados a su cuenta, o fallas técnicas.</li>
              <li><strong>Herramientas de Exportación:</strong> La Plataforma pone a disposición del usuario herramientas para exportar sus anexos de IVA y registros históricos. Es responsabilidad exclusiva del usuario descargar estos reportes mes a mes para su custodia contable física o en servidores propios.</li>
            </ul>
          </section>

          <section>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#0f172a', marginBottom: '0.5rem' }}>7. Aceptación y Modificación de los Términos</h3>
            <p>Al registrarse y hacer uso del Sistema de Declaraciones de IVA, el usuario declara haber leído, comprendido y aceptado la totalidad de estas cláusulas. El desconocimiento de estos términos no exime al usuario de su cumplimiento.</p>
            <p style={{ marginTop: '0.5rem' }}>Nos reservamos el derecho de modificar, actualizar o revisar estos Términos de Referencia en cualquier momento para adaptarlos a nuevas normativas tributarias (disposiciones del Ministerio de Hacienda), mejoras tecnológicas o cambios en nuestros modelos de licenciamiento. Toda modificación sustancial será notificada a través de la Plataforma. Cuando ocurran dichas actualizaciones, el acceso continuo a los servicios requerirá que el usuario revise y acepte explícitamente los nuevos términos. El uso continuado del sistema tras la aceptación constituirá su conformidad con las condiciones actualizadas.</p>
          </section>
        </div>

        {fromGuard && (
          <div style={{ marginTop: '3rem', borderTop: '1px solid #e2e8f0', paddingTop: '2rem' }}>
            <label style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem', cursor: 'pointer' }}>
              <input 
                type="checkbox" 
                checked={accepted} 
                onChange={(e) => setAccepted(e.target.checked)}
                style={{ marginTop: '0.25rem', width: '1.25rem', height: '1.25rem' }}
              />
              <span style={{ fontSize: '1rem', color: '#1e293b', fontWeight: '500' }}>
                He leído, comprendido y acepto en su totalidad los Términos de Referencia y Condiciones de Servicio, en especial la cláusula sobre la responsabilidad exclusiva del usuario en el respaldo de datos.
              </span>
            </label>
            
            <button 
              onClick={handleAccept}
              disabled={!accepted || loading}
              style={{ 
                marginTop: '2rem', 
                width: '100%', 
                padding: '1rem', 
                backgroundColor: accepted ? '#0284c7' : '#94a3b8', 
                color: 'white', 
                fontWeight: 'bold', 
                borderRadius: '0.5rem', 
                cursor: accepted ? 'pointer' : 'not-allowed',
                border: 'none',
                transition: 'background-color 0.2s'
              }}
            >
              {loading ? 'Procesando...' : 'Aceptar Términos y Continuar'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
