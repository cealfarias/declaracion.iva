const DEFAULT_FILENAME = 'export.csv';

function filenameFromDisposition(disposition) {
  if (!disposition) return null;

  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match) {
    try {
      return decodeURIComponent(utf8Match[1].trim()).split(/[\\/]/).pop();
    } catch {
      // Continúa con el formato filename="..." si el UTF-8 no es válido.
    }
  }

  const plainMatch = disposition.match(/filename="?([^";]+)"?/i);
  return plainMatch ? plainMatch[1].trim().split(/[\\/]/).pop() : null;
}

async function readErrorDetail(response) {
  try {
    const body = await response.text();
    if (!body) return '';
    try {
      const parsed = JSON.parse(body);
      return typeof parsed?.detail === 'string' ? parsed.detail : '';
    } catch {
      return body.slice(0, 200);
    }
  } catch {
    return '';
  }
}

/**
 * Descarga un archivo protegido enviando el JWT en el header Authorization.
 * Convierte la respuesta en Blob y dispara una descarga temporal; nunca
 * navega a la URL de la API.
 */
export async function downloadAuthenticatedFile({ url, token, fallbackFilename = DEFAULT_FILENAME }) {
  if (!token) {
    throw new Error('No hay una sesión activa. Vuelve a iniciar sesión para descargar el archivo.');
  }

  let response;
  try {
    response = await fetch(url, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'text/csv, application/octet-stream, */*',
      },
    });
  } catch {
    throw new Error('No se pudo conectar con el servidor para descargar el archivo.');
  }

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    if (response.status === 401) {
      throw new Error('Tu sesión expiró o no es válida. Vuelve a iniciar sesión.');
    }
    if (response.status === 403) {
      throw new Error(detail || 'No tienes permisos para exportar este período.');
    }
    if (response.status === 404) {
      throw new Error(detail || 'No hay datos disponibles para exportar en este período.');
    }
    throw new Error(detail || `No se pudo generar el archivo (HTTP ${response.status}).`);
  }

  const blob = await response.blob();
  if (!blob.size) {
    throw new Error('El servidor devolvió un archivo vacío.');
  }

  const filename =
    filenameFromDisposition(response.headers.get('Content-Disposition')) || fallbackFilename;
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename;
  link.rel = 'noopener';
  link.style.display = 'none';
  document.body.appendChild(link);
  link.click();
  link.remove();

  // Dar tiempo al navegador a iniciar la descarga antes de liberar el Blob.
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1500);

  return filename;
}
