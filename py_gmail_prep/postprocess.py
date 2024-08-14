import os
import shutil
import sys
import json
import base64
import datetime
from email import message_from_file
from email.message import EmailMessage

from bs4 import BeautifulSoup

DEBUG = False

RESPONSE_ADDRESS_FILTERS = sys.argv[1:]

print("lista de casillas validas", RESPONSE_ADDRESS_FILTERS)


def normalize_header(header_value):
    if header_value:
        header_value = header_value.replace('\n', '').replace('\r', '').strip()
    return header_value

def get_message_body(msg):
    print(msg['id'])
    if 'data' in msg['payload']['body']:
        return base64.urlsafe_b64decode(msg['payload']['body']['data'].encode('ASCII')).decode('utf-8')
    else:
        return get_message_part(msg['payload'])


def normalize_body(body_html):
    soup = BeautifulSoup(body_html, features="html.parser")

    # remove html tags
    for script in soup(["script", "style"]):
        script.extract()

    plain_text = soup.get_text()
    return plain_text


def get_message_part(parts):
        # si el mensaje es multipart, recorrer las partes y extraer el texto plano
        for part in parts.get('parts', []):
            print(part['mimeType'])
            if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                return base64.urlsafe_b64decode(part['body']['data'].encode('ASCII')).decode('utf-8')
            if part['mimeType'] == 'multipart/alternative':
                # recursivamente buscar la parte de texto:
                return get_message_part(part)


def get_message_headers(msg):
    # armar un diccionario con los encabezados, filtrando los interesantes:
    headers = {}
    for header in msg["payload"]["headers"]:
        if header["name"] in ("In-Reply-To", "From", "Date", "Message-ID", "Subject", "To", "Return-Path"):
            headers[header["name"]] = normalize_header(header["value"])
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


def parse_gmail(file_path):

    msg = json.load(open(file_path))
    folder = os.path.join("threads", msg["threadId"])
    os.makedirs(folder, exist_ok=True)

    msg_str = get_message_body(msg)
    if msg_str:
        headers = get_message_headers(msg)

        # ignorar mensajes sin publicar
        if "Google Groups: mensaje pendiente" in headers["Subject"]:
            return

        # limpiar el cuerpo del mensaje para eliminar el texto citado
        clean_body = normalize_body(remove_cited_text(msg_str.strip()))

        timestamp = datetime.datetime.fromtimestamp(float(msg['internalDate'])/1000.).strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{msg['historyId']}_{msg['id']}.eml"
        print(file_path, filename, clean_body)

        email = create_rfc822_message(headers, clean_body)

        with open(os.path.join(folder, filename), "w") as f:
            f.write(email)
  
    else:
        print(f'No se pudo extraer el cuerpo del mensaje con ID: {file_path}')


def remove_cited_text(body):
    # lista de posibles indicadores de texto citado
    citation_markers = [
        "On ", "En ", "Le ", "El ", "wrote:", "escribió:", "escribio:", "ha scritto:", "a écrit:", "schrieb:"
    ]
    # dividir el cuerpo en líneas
    lines = body.splitlines()

    # recorrer las líneas en orden inverso y buscar un marcador de citación
    prev = ""
    for i in reversed(range(len(lines))):
        line = lines[i].strip()
        if any(line.startswith(marker) for marker in citation_markers):
            if any(l.endswith(marker) for marker in citation_markers for l in (line, prev)):
                # si se encuentra un marcador, eliminar todo el texto desde esa línea en adelante
                return '\n'.join(lines[:i])
        prev = line

    # si no se encuentra ningún marcador, devolver el cuerpo tal cual
    return body


def main():
    rfc822_dir = 'emails/'  # directorio con los archivos RFC822
    json_output = 'training_data.json'  # archivo de salida JSON

    emails = []
    errores = 0
    ok = 0
    for filename in os.listdir(rfc822_dir):
        if (filename in sys.argv[1:]) or (not sys.argv[1:] and filename.endswith('.json')):
            file_path = os.path.join(rfc822_dir, filename)
            try:
                emails.append(parse_gmail(file_path))
            except Exception as ex:
                errores += 1
                print("Error al procesar", file_path, ex)
            else:
                ok += 1
    
    print("procesados", ok)
    print("errores", errores)


if __name__ == '__main__':
    main()
