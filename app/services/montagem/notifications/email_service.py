# -*- coding: utf-8 -*-
"""
Envio de e-mail via Outlook (COM) — simples e sem SMTP.
Requisitos: Windows, Outlook instalado e perfil configurado.
Opcional: defina OUTLOOK_DISPLAY_ONLY=1 para abrir a janela de e-mail
          em vez de enviar automaticamente.
Fallback: se Outlook falhar e houver SMTP configurado, tenta SMTP.
"""

import os
import sys

def _send_via_outlook(to: str, subject: str, body: str, cc=None, bcc=None) -> bool:
    import win32com.client as win32  # requer pywin32
    outlook = win32.Dispatch("Outlook.Application")
    mail = outlook.CreateItem(0)  # 0 = olMailItem

    mail.To = to
    if cc:
        mail.CC = ", ".join(cc) if isinstance(cc, (list, tuple)) else str(cc)
    if bcc:
        mail.BCC = ", ".join(bcc) if isinstance(bcc, (list, tuple)) else str(bcc)

    mail.Subject = subject
    mail.Body = body

    # Se quiser só pré-abrir a janela, defina OUTLOOK_DISPLAY_ONLY=1
    display_only = os.getenv("OUTLOOK_DISPLAY_ONLY", "0") == "1"
    if display_only:
        mail.Display(False)  # abre a janela do Outlook
    else:
        mail.Send()          # envia direto
    return True


def _send_via_smtp(to: str, subject: str, body: str, cc=None, bcc=None) -> bool:
    """Fallback SMTP (usa as mesmas envs que você já tinha; opcional)."""
    import smtplib
    from email.mime.text import MIMEText

    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "25"))
    user = os.getenv("SMTP_USER")
    pwd  = os.getenv("SMTP_PASS")
    from_addr = os.getenv("SMTP_FROM", "sgp@pneumark.com.br")
    use_tls = os.getenv("SMTP_STARTTLS", "1") == "1"

    if not host:
        return False  # sem SMTP configurado

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to

    rcpts = [to]
    if cc:
        if isinstance(cc, (list, tuple)):
            msg["Cc"] = ", ".join(cc); rcpts += list(cc)
        else:
            msg["Cc"] = cc; rcpts.append(cc)
    if bcc:
        rcpts += (list(bcc) if isinstance(bcc, (list, tuple)) else [bcc])

    with smtplib.SMTP(host, port, timeout=15) as s:
        if use_tls:
            try: s.starttls()
            except Exception: pass
        if user:
            s.login(user, pwd or "")
        s.sendmail(from_addr, rcpts, msg.as_string())
    return True


def send_email(to: str, subject: str, body: str, *, cc=None, bcc=None):
    """
    API usada pelo restante do sistema.
    1) Tenta Outlook (COM).
    2) Se falhar e existir SMTP configurado, tenta SMTP.
    3) Se nada der, apenas loga o conteúdo (não quebra o fluxo).
    """
    # 1) Outlook
    try:
        ok = _send_via_outlook(to, subject, body, cc=cc, bcc=bcc)
        if ok:
            return True
    except Exception as e:
        print(f"[EMAIL][Outlook] Falha: {e}", file=sys.stderr)

    # 2) SMTP (opcional)
    try:
        ok = _send_via_smtp(to, subject, body, cc=cc, bcc=bcc)
        if ok:
            return True
    except Exception as e:
        print(f"[EMAIL][SMTP] Falha: {e}", file=sys.stderr)

    # 3) Fallback (não interrompe a aplicação)
    print(
        "[EMAIL][FAKE] Sem Outlook/SMTP. Conteúdo abaixo:\n"
        f"TO: {to}\nSUBJECT: {subject}\n\n{body}\n",
        file=sys.stderr
    )
    return False
