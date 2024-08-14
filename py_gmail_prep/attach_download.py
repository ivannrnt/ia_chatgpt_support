import os.path
import sys
import base64
import json
import base64

import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# configuración de los permisos de la API de Gmail
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_message_images(service, msg, folder):

    for part in msg['payload'].get('parts', []):
        print(part['mimeType'])
        if part['mimeType'].startswith('image/'):
            filename = part.get('filename')
            if filename:
                os.makedirs(folder, exist_ok=True)
                print("found", filename)
                if 'data' in part['body']:
                    data = part['body']['data']
                else:
                    attach_id = part['body']['attachmentId']
                    attach = service.users().messages().attachments().get(userId='me', messageId=msg['id'], id=attach_id).execute()
                    data = attach['data']
                bin_data = base64.urlsafe_b64decode(data.encode('UTF-8'))
                print(len(bin_data))

                with open(os.path.join(folder, filename), 'wb') as f:
                    f.write(bin_data)


def parse_gmail(service, file_path):

    msg = json.load(open(file_path))
    folder = os.path.join("attachs", msg["id"])
    msg_img = get_message_images(service, msg, folder)


def main():
    rfc822_dir = 'emails/'  # directorio con los archivos RFC822

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
            import webbrowser
            chrome_path="C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
            webbrowser.register('chrome', None,webbrowser.BackgroundBrowser(chrome_path))
            creds = flow.run_local_server(port=0, browser='chrome')  # Asignar a creds aquí
        # guardar las credenciales para la próxima ejecución
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    # conectar con la API de Gmail
    service = build('gmail', 'v1', credentials=creds)

    emails = []
    errores = 0
    ok = 0
    for filename in os.listdir(rfc822_dir):
        if (filename in sys.argv[1:]) or (not sys.argv[1:] and filename.endswith('.json')):
            file_path = os.path.join(rfc822_dir, filename)
            try:
                emails.append(parse_gmail(service, file_path))
            except Exception as ex:
                errores += 1
                print("Error al procesar", file_path, ex)
            else:
                ok += 1
    
    print("procesados", ok)
    print("errores", errores)


if __name__ == '__main__':
    main()
