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
LABEL = sys.argv[1]


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
            import webbrowser
            chrome_path="C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
            webbrowser.register('chrome', None,webbrowser.BackgroundBrowser(chrome_path))
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
    next_page_token = ""
    ok = 0
    while True:
        results = service.users().messages().list(userId='me', labelIds=[label_id],  maxResults=100, pageToken=next_page_token).execute()
        messages = results.get('messages', [])

        if not messages:
            print('No se encontraron mensajes.')
            break
        else:
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id']).execute()
                ok += 1
                print(ok, msg['id'])
                with open(os.path.join("emails", f"{msg['id']}.json"), "w") as f:
                    json.dump(msg, f)

        if('nextPageToken' in results or next_page_token==''):
            next_page_token = results['nextPageToken']
        else:
            break


if __name__ == '__main__':
    main()
