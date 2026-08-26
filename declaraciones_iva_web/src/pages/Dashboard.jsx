import React from 'react';

function Dashboard() {
  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#8a1c2a', color: 'white', padding: '10px 20px' }}>
        <h2>MINISTERIO DE HACIENDA</h2>
        <div>
          <span>Nombre: Usuario</span>
          <button style={{ marginLeft: '10px', background: 'transparent', color: 'white', border: '1px solid white', cursor: 'pointer' }}>SALIR</button>
        </div>
      </header>
      <main style={{ padding: '40px', textAlign: 'center' }}>
        <h1>Bienvenido al cascarón de Declaraciones de IVA</h1>
        <p>Todo el código ha sido eliminado permanentemente por solicitud.</p>
      </main>
    </div>
  );
}

export default Dashboard;
