import base64
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import calendar

def fetch_dtes_from_gmail(access_token: str, anio: int, mes: int, nit: str = None):
    """
    Se conecta a Gmail usando un Access Token de usuario.
    Busca correos en el mes y año dado que contengan archivos adjuntos .json.
    Retorna una lista de diccionarios con el contenido parseado de los JSON.
    """
    creds = Credentials(token=access_token)
    service = build('gmail', 'v1', credentials=creds)

    # Determinar el mes siguiente para el before (exclusivo)
    if mes == 12:
        next_anio = anio + 1
        next_mes = 1
    else:
        next_anio = anio
        next_mes = mes + 1
        
    start_date = f"{anio}/{mes:02d}/01"
    end_date = f"{next_anio}/{next_mes:02d}/01"
    
    # Query de búsqueda solo por adjuntos JSON y fechas
    query = f"has:attachment filename:json after:{start_date} before:{end_date}"

    print(f"Buscando en Gmail con query: {query}")
    
    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])
    
    dtes_extraidos = []
    
    if not messages:
        return dtes_extraidos

    for msg in messages:
        # Obtener el mensaje completo
        msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
        payload = msg_data.get('payload', {})
        parts = payload.get('parts', [])
        
        # Buscar en partes y subpartes
        attachments = _get_attachments(parts, service, msg['id'])
        
        for att_data in attachments:
            try:
                # El adjunto viene en base64 urlsafe
                file_data = base64.urlsafe_b64decode(att_data).decode('utf-8')
                dte_json = json.loads(file_data)
                
                # Si es un DTE válido (a veces viene anidado en {"dteJson": {...}})
                if "dteJson" in dte_json and isinstance(dte_json["dteJson"], dict):
                    dte_json = dte_json["dteJson"]
                    
                if "identificacion" in dte_json:
                    dtes_extraidos.append(dte_json)
            except Exception as e:
                print(f"Error procesando adjunto de Gmail: {str(e)}")
                continue
                
    return dtes_extraidos

def _get_attachments(parts, service, msg_id):
    attachments = []
    for part in parts:
        if part.get('filename') and part.get('filename').endswith('.json'):
            if 'data' in part['body']:
                attachments.append(part['body']['data'])
            elif 'attachmentId' in part['body']:
                att_id = part['body']['attachmentId']
                att_obj = service.users().messages().attachments().get(
                    userId='me', messageId=msg_id, id=att_id
                ).execute()
                attachments.append(att_obj['data'])
        elif 'parts' in part:
            attachments.extend(_get_attachments(part['parts'], service, msg_id))
    return attachments
