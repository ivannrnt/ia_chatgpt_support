import os.path
import sys
import base64
import json
from email.message import EmailMessage
import base64

import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# configuración de los permisos de la API de Gmail
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
LABEL = sys.argv[1]


def get_message_body(msg):
    print(msg['id'])
    if 'data' in msg['payload']['body']:
        return base64.urlsafe_b64decode(msg['payload']['body']['data'].encode('ASCII')).decode('utf-8')
    else:
        return get_message_part(msg['payload'])


def get_message_part(parts):
        # si el mensaje es multipart, recorrer las partes y extraer el texto plano
        for part in parts.get('parts', []):
            print(part['mimeType'])
            if part['mimeType'] == 'text/plain':
                return base64.urlsafe_b64decode(part['body']['data'].encode('ASCII')).decode('utf-8')
            if part['mimeType'] == 'multipart/alternative':
                # recursivamente buscar la parte de texto:
                return get_message_part(part)
            breakpoint()


def get_message_headers(msg):
    # armar un diccionario con los encabezados, filtrando los interesantes:
    headers = {}
    for header in msg["payload"]["headers"]:
        if header["name"] in ("In-Reply-To", "From", "Date", "Message-ID", "Subject", "To", "Return-Path"):
            headers[header["name"]] = header["value"]
    return headers


def create_rfc822_message(headers, body):
    # crear un nuevo mensaje de correo
    msg = EmailMessage()

    # agregar los encabezados
    for key, value in headers.items():
        if key.lower() not in ['content-transfer-encoding', 'content-type']:
            msg[key] = value
    # agregar el cuerpo del mensaje
    msg.set_content(body)

    # devolver el mensaje como una cadena en formato RFC822
    return msg.as_string()


def main():
    creds = None
    # archivo token.json que guarda los tokens de acceso y actualización
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # si no hay credenciales válidas, solicita al usuario que inicie sesión
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0, browser='chrome')  # Asignar a creds aquí
        # guardar las credenciales para la próxima ejecución
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    # conectar con la API de Gmail
    service = build('gmail', 'v1', credentials=creds)

    # obtener todas las etiquetas y sus IDs
    labels = service.users().labels().list(userId='me').execute()
    print("Etiquetas disponibles:")
    for label in labels['labels']:
        print(f"Label name: {label['name']} - Label ID: {label['id']}")
        # etiqueta que deseas buscar
        if label['name'] == LABEL:
            label_id = label['id']
            break
    else:
        raise RuntimeError("Etiqueta no encontrada")
    
    # llamada a la API para obtener los mensajes con la etiqueta
    results = service.users().messages().list(userId='me', labelIds=[label_id]).execute()
    messages = results.get('messages', [])

    if not messages:
        print('No se encontraron mensajes.')
    else:
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            with open(f"{msg['id']}.json", "w") as f:
                json.dump(msg, f)
            msg_str = get_message_body(msg)
            if msg_str:
                print(msg_str) 
                headers = get_message_headers(msg)
                # ignorar mensajes sin publicar
                if "Google Groups: mensaje pendiente" in headers["Subject"]:
                    continue
                email = create_rfc822_message(headers, msg_str)
                with open(f"{msg['id']}.eml", "w") as f:
                    f.write(email)
            else:
                print(f'No se pudo extraer el cuerpo del mensaje con ID: {message["id"]}')


if __name__ == '__main__':
    main()
