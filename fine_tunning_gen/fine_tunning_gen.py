import os
import sys
import json
from email import message_from_file

DEBUG = False

RESPONSE_ADDRESS_FILTERS = sys.argv[1:]

print("lista de casillas validas", RESPONSE_ADDRESS_FILTERS)


def normalize_header(header_value):
    if header_value:
        header_value = header_value.replace('\n', '').replace('\r', '').strip()
    return header_value

def parse_email(file_path):
    print (file_path)
    with open(file_path, 'r', encoding='utf-8') as f:
        msg = message_from_file(f)

    headers = {k: v for k, v in msg.items()}
    body = ""
    if msg.is_multipart():
        for part in msg.get_payload():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode(part.get_content_charset(), 'ignore')
                break
    else:
        body = msg.get_payload(decode=True).decode(msg.get_content_charset(), 'ignore')

    # limpiar el cuerpo del mensaje para eliminar el texto citado
    clean_body = remove_cited_text(body.strip())

    return {
        'filename': file_path,
        'message_id': normalize_header(headers.get('Message-ID')),
        'in_reply_to':  normalize_header(headers.get('In-Reply-To')),
        'from': headers.get('From'),
        'to': headers.get('To'),
        'subject': headers.get('Subject'),
        'date': headers.get('Date'),
        'body': clean_body
    }

def remove_cited_text(body):
    # lista de posibles indicadores de texto citado
    citation_markers = [
        "On ", "En ", "Le ", "El ", "wrote:", "escribió:", "ha scritto:", "a écrit:", "schrieb:"
    ]
    # dividir el cuerpo en líneas
    lines = body.splitlines()

    # recorrer las líneas en orden inverso y buscar un marcador de citación
    for i in reversed(range(len(lines))):
        line = lines[i].strip()
        if any(line.startswith(marker) for marker in citation_markers):
            # si se encuentra un marcador, eliminar todo el texto desde esa línea en adelante
            return '\n'.join(lines[:i])

    # si no se encuentra ningún marcador, devolver el cuerpo tal cual
    return body


def build_conversations(emails):
    email_dict = {email['message_id']: email for email in emails}
    conversations = []

    for response in emails:
        in_reply_to = response['in_reply_to']
        print("buscando mensaje orginal para ", in_reply_to)
        responder = response["from"]
        if not in_reply_to or not any([address for address in RESPONSE_ADDRESS_FILTERS if address in responder]):
            print("descartando email pregunta porque no es de una direccion válida", responder)
            continue
        if in_reply_to in email_dict:
            print ("encontrado mensaje original")
            original = email_dict[in_reply_to]
            inquirer = original["from"]
            if any([address for address in RESPONSE_ADDRESS_FILTERS if address in inquirer]):
                print("descartando email original porque no es de una direccion válida", inquirer)
                continue
            question = original['body']
            answer = response['body']
            conversations.append({
                'prompt': question,
                'completion': answer,
            })
            if DEBUG:
                conversations[-1].update({
                    'question': original["filename"],
                    'answer': response["filename"],
                    'sender': responder,
                    'from': [address for address in RESPONSE_ADDRESS_FILTERS if address in response["from"]],
                    'to': [address for address in RESPONSE_ADDRESS_FILTERS if address in original["from"]],
                    'customer': inquirer,
                })


    return conversations


def main():
    rfc822_dir = 'emails/'  # directorio con los archivos RFC822
    json_output = 'training_data.json'  # archivo de salida JSON

    emails = []
    for filename in os.listdir(rfc822_dir):
        if filename.endswith('.eml'):
            file_path = os.path.join(rfc822_dir, filename)
            emails.append(parse_email(file_path))

    conversations = build_conversations(emails)

    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2)

    print(f"Archivo JSON generado: {json_output}")


if __name__ == '__main__':
    main()
