"""
AI Outreach Bot — generates hyper-personalized cold emails using Claude
and creates Gmail drafts automatically.

Usage:
    python outreach.py leads.csv --sender "Tu Nombre" --context "somos una agencia de diseño"
"""

import anthropic
import base64
import csv
import os
import sys
import argparse
import json
from email.mime.text import MIMEText

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]


def load_leads(csv_path: str) -> list[dict]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def generate_email(client: anthropic.Anthropic, lead: dict, sender_context: str) -> dict:
    prompt = f"""Eres un experto en cold email. Escribe un email de outreach profesional pero humano.

Remitente: {sender_context}

Destinatario:
- Nombre: {lead.get('nombre', lead.get('name', 'amigo'))}
- Empresa: {lead.get('empresa', lead.get('company', ''))}
- Rol: {lead.get('rol', lead.get('role', ''))}
- Contexto extra: {lead.get('contexto', lead.get('context', ''))}

Reglas:
- Máximo 4 párrafos cortos
- Primera línea debe enganchar sin ser falsa
- No uses "espero que este email te encuentre bien"
- No seas robot, sé directo y auténtico
- Termina con un CTA claro y fácil de responder
- Asunto del email: corto, intrigante, sin clickbait

Responde SOLO con JSON válido con este formato exacto:
{{"subject": "...", "body": "..."}}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    # strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def get_gmail_service():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        print(
            "\n[!] Instala las dependencias de Gmail:\n"
            "    pip install google-auth google-auth-oauthlib google-api-python-client\n"
        )
        sys.exit(1)

    creds = None
    token_path = "token.json"
    creds_path = "credentials.json"

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, GMAIL_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_path):
                print(
                    "\n[!] No se encontró credentials.json\n"
                    "    Descarga tu OAuth credentials desde Google Cloud Console\n"
                    "    y guárdalas como 'credentials.json' en este directorio.\n"
                    "    Guía: https://developers.google.com/gmail/api/quickstart/python\n"
                )
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def create_draft(service, to_email: str, subject: str, body: str) -> str:
    msg = MIMEText(body)
    msg["to"] = to_email
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
    return draft["id"]


def main():
    parser = argparse.ArgumentParser(description="AI Outreach Bot")
    parser.add_argument("leads", help="CSV con los contactos")
    parser.add_argument(
        "--sender",
        default=os.getenv("SENDER_CONTEXT", "yo"),
        help="Quién eres / contexto del remitente",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo imprime los emails, no crea borradores en Gmail",
    )
    parser.add_argument(
        "--output",
        default="emails_generados.json",
        help="Guarda los emails generados en este archivo",
    )
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[!] Falta ANTHROPIC_API_KEY en las variables de entorno")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    leads = load_leads(args.leads)

    if not leads:
        print("[!] El CSV está vacío o mal formateado")
        sys.exit(1)

    gmail_service = None
    if not args.dry_run:
        print("[*] Conectando con Gmail...")
        gmail_service = get_gmail_service()

    results = []
    print(f"\n[*] Generando emails para {len(leads)} contactos...\n")

    for i, lead in enumerate(leads, 1):
        email_addr = lead.get("email", lead.get("correo", ""))
        name = lead.get("nombre", lead.get("name", f"contacto #{i}"))

        print(f"  [{i}/{len(leads)}] {name} <{email_addr}>", end=" ... ", flush=True)

        try:
            generated = generate_email(client, lead, args.sender)
            subject = generated["subject"]
            body = generated["body"]

            draft_id = None
            if gmail_service and email_addr:
                draft_id = create_draft(gmail_service, email_addr, subject, body)
                status = f"borrador creado (id: {draft_id})"
            elif args.dry_run:
                status = "dry-run"
            else:
                status = "sin email, solo generado"

            print(f"OK — {status}")
            results.append(
                {
                    "lead": lead,
                    "subject": subject,
                    "body": body,
                    "draft_id": draft_id,
                    "status": status,
                }
            )

        except Exception as e:
            print(f"ERROR — {e}")
            results.append({"lead": lead, "error": str(e)})

    # save results
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    ok = sum(1 for r in results if "error" not in r)
    print(f"\n[✓] {ok}/{len(leads)} emails generados — guardados en {args.output}")
    if gmail_service:
        print("[✓] Abre Gmail → Borradores para revisar y enviar")


if __name__ == "__main__":
    main()
