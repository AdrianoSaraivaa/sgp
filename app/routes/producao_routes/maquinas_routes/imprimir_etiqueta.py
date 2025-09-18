
# app/routes/producao_routes/maquinas_routes/imprimir_etiqueta.py
from __future__ import annotations
import io
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from flask import Blueprint, request, jsonify, send_file, abort

from app import db
# Use the SQLAlchemy models instead of the dataclasses. Import from the
# auto-generated models_sqla package to ensure that ``.query`` is available.
from app.models_sqla import Montagem, LabelReprintLog

# Dependências de imagem/QR
from PIL import Image, ImageDraw, ImageFont
import qrcode
import qrcode.constants

# PDF é opcional; se não tiver reportlab, seguimos com PNG
try:
    from reportlab.lib.pagesizes import mm
    from reportlab.pdfgen import canvas as pdf_canvas
    REPORTLAB_OK = True
except Exception:
    REPORTLAB_OK = False

imprimir_etiqueta_bp = Blueprint(
    "imprimir_etiqueta_bp",
    __name__,
    url_prefix="/producao/etiqueta"
)

# ----------------------------------------------------------------------
# CONFIG PADRÃO DA ETIQUETA (PASSO 1)
# ----------------------------------------------------------------------
# --- CONFIG PADRÃO DA ETIQUETA ---
DPI_DEFAULT = 300                  # Elgin L42 = 203 dpi (8 dpmm)
LABEL_W_MM  = 40                   # 40 x 25 mm  (igual ao BarTender)
LABEL_H_MM  = 25

# Conversões p/ pixels no DPI da impressora
LABEL_W_PX = int(LABEL_W_MM / 25.4 * DPI_DEFAULT)
LABEL_H_PX = int(LABEL_H_MM / 25.4 * DPI_DEFAULT)

# Tamanhos relativos
QR_SIZE_PX = int(LABEL_H_PX * 0.80)     # QR = 80% da altura (mais seguro pra leitura)
MARGIN_PX  = max(2, LABEL_H_PX // 40)   # margens mínimas

# Tipografia (mais fina, boa legibilidade a 203 dpi)
FONT_PX    = max(10, int(LABEL_H_PX * 0.09))  # ~10% da altura

# Salvar arte final em 1-bit? (às vezes fica mais nítido; teste no seu driver)
SAVE_1BIT_BW = False

TEXT_OFFSET_MM = -1.0  # valor negativo aproxima, positivo afasta
TEXT_OFFSET_PX = int(TEXT_OFFSET_MM / 25.4 * DPI_DEFAULT)



# Pastas de saída (serão criadas se não existirem)
STATIC_DIR  = Path("app/static")
QRCODES_DIR = STATIC_DIR / "qrcodes"
LABELS_DIR  = STATIC_DIR / "labels"
for d in (STATIC_DIR, QRCODES_DIR, LABELS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------
# UTIL
# ----------------------------------------------------------------------
def ensure_dirs():
    QRCODES_DIR.mkdir(parents=True, exist_ok=True)
    LABELS_DIR.mkdir(parents=True, exist_ok=True)

def _load_font(size_px: int) -> ImageFont.FreeTypeFont:
    """
    Tenta Arial do Windows; depois alternativas; por fim, bitmap default.
    (PASSO 1: garantir TTF para não “estourar/borrar”)
    """
    candidates = [
        "C:/Windows/Fonts/arial.ttf",  # caminho padrão no Windows
        "arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        str(Path.cwd() / "arial.ttf"),
    ]
    for fp in candidates:
        try:
            return ImageFont.truetype(fp, size_px)
        except Exception:
            continue
    return ImageFont.load_default()

def get_assembly_by_id(assembly_id: str) -> Optional[dict]:
    """
    Busca do BD (por id ou serial). Se não achar, aceita via querystring (modelo/serial/dt/usuario).
    """
    m = None
    if assembly_id.isdigit():
        m = Montagem.query.get(int(assembly_id))
    else:
        m = Montagem.query.filter_by(serial=assembly_id).first()

    if m:
        return {
            "id": m.id,
            "modelo": m.modelo,
            "serial": m.serial,
            "dt_obj": m.data_hora,
            "usuario": m.usuario,
            "label_printed": m.label_printed,
            "label_print_count": m.label_print_count,
        }

    # Fallback para testes via querystring
    modelo = request.args.get("modelo")
    serial = request.args.get("serial")
    dt = request.args.get("dt")
    usuario = request.args.get("usuario", "Operador")
    if not (modelo and serial):
        return None
    if dt:
        try:
            dt_obj = datetime.fromisoformat(dt.replace("T", " "))
        except Exception:
            try:
                dt_obj = datetime.strptime(dt, "%d/%m/%Y %H:%M")
            except Exception:
                dt_obj = datetime.now()
    else:
        dt_obj = datetime.now()
    return {
        "id": assembly_id,
        "modelo": modelo.strip(),
        "serial": str(serial).strip(),
        "dt_obj": dt_obj,
        "usuario": usuario.strip(),
        "label_printed": False,
        "label_print_count": 0,
    }

# ----------------------------------------------------------------------
# COMPOSIÇÃO DA ETIQUETA
# ----------------------------------------------------------------------




def _compose_png(modelo: str, serial: str, dt_obj: datetime) -> Image.Image:
    """
    Monta a etiqueta final em PNG (40x25 mm @ 203dpi) com:
    - QR (somente o serial)
    - Texto: modelo, serial, data/hora (pt-BR)
    """
    # Gera QR com qualidade equilibrada
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=2,     # pequeno; escalamos para QR_SIZE_PX
        border=2,       # quiet zone mínima
    )
    qr.add_data(serial)
    qr.make(fit=True)
    qr_img_small = qr.make_image(fill_color="black", back_color="white").convert("L")

    # Escala do QR para o tamanho exato, preservando nitidez
    qr_img = qr_img_small.resize((QR_SIZE_PX, QR_SIZE_PX), Image.NEAREST)

    # Canvas da etiqueta
    etq = Image.new("L", (LABEL_W_PX, LABEL_H_PX), color=255)
    draw = ImageDraw.Draw(etq)

    # Posiciona QR à esquerda, centralizado verticalmente
    qr_x = MARGIN_PX
    qr_y = (LABEL_H_PX - QR_SIZE_PX) // 2
    etq.paste(qr_img, (qr_x, qr_y))

    # Área de texto à direita do QR
    text_x = qr_x + QR_SIZE_PX + MARGIN_PX + TEXT_OFFSET_PX
    text_w = LABEL_W_PX - text_x - MARGIN_PX

    # Fonte
    font = _load_font(FONT_PX)

    # Linhas
    dt_str = dt_obj.strftime("%d/%m/%Y %H:%M")
    lines = [modelo, serial, dt_str]

    # Altura de linha com leve leading
    if hasattr(font, "getmetrics"):
        ascent, descent = font.getmetrics()
    else:
        ascent, descent = (FONT_PX, 0)
    line_h = ascent + descent + max(1, FONT_PX // 6)

    total_text_h = len(lines) * line_h
    start_y = max(MARGIN_PX, (LABEL_H_PX - total_text_h) // 2)

    # Render básico (sem quebra automática)
    y = start_y
    for line in lines:
        # Se quiser proteção contra overflow horizontal, pode reduzir fonte quando for maior que text_w
        draw.text((text_x, y), line, font=font, fill=0)
        y += line_h

    return etq









def _output_png(modelo: str, serial: str, dt_obj: datetime) -> Tuple[Path, Path]:
    """
    Gera PNG do QR e PNG da etiqueta final, salva em disco.
    Retorna (qr_path, label_path)
    """
    ensure_dirs()

    ano = dt_obj.strftime("%Y")
    (QRCODES_DIR / ano).mkdir(exist_ok=True, parents=True)
    (LABELS_DIR / ano).mkdir(exist_ok=True, parents=True)

    # QR “solto” para rastreabilidade
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(serial)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("L")

    qr_path = QRCODES_DIR / ano / f"{serial}.png"
    qr_img.save(qr_path, "PNG", optimize=True, dpi=(DPI_DEFAULT, DPI_DEFAULT))

    # Etiqueta final
    
    etq_img = _compose_png(modelo, serial, dt_obj)
    label_path = LABELS_DIR / ano / f"{modelo}_{serial}.png"

    # Força conversão para preto e branco 1-bit (texto sai bem nítido, sem borrado)
    etq_bw = etq_img.convert("1")
    etq_bw.save(label_path, "PNG",
                optimize=True,
                dpi=(DPI_DEFAULT, DPI_DEFAULT))

    return qr_path, label_path








def _output_pdf_from_png(label_png: Path) -> bytes:
    """
    Converte a etiqueta PNG em um PDF no tamanho exato (40x25mm).
    Use o PDF no preview e imprima em 'Tamanho real (100%)' para evitar scaling.
    """
    if not REPORTLAB_OK:
        raise RuntimeError("reportlab indisponível")

    w_pt = LABEL_W_MM * mm
    h_pt = LABEL_H_MM * mm

    buffer = io.BytesIO()
    c = pdf_canvas.Canvas(buffer, pagesize=(w_pt, h_pt))
    c.drawImage(str(label_png), 0, 0, width=w_pt, height=h_pt,
                preserveAspectRatio=False, mask='auto')
    c.showPage()
    c.save()
    return buffer.getvalue()



















# ----------------------------------------------------------------------
# ROTAS
# ----------------------------------------------------------------------
@imprimir_etiqueta_bp.route("/<assembly_id>/preview", methods=["GET"])
def preview_label(assembly_id):
    """
    Gera/mostra a etiqueta. Se reportlab estiver disponível, prioriza PDF (tamanho exato).
    Caso contrário, retorna PNG com DPI correto.
    """
    data = get_assembly_by_id(assembly_id)
    if not data:
        return abort(400, "Parâmetros insuficientes (modelo/serial).")

    modelo = data["modelo"]
    serial = data["serial"]
    dt_obj = data["dt_obj"]

    # Gera arquivos (salva para rastreabilidade)
    _, label_png = _output_png(modelo, serial, dt_obj)

    # Se o usuário pedir explicitamente ?format=png, honramos.
    out_format = request.args.get("format", "").lower()

    if REPORTLAB_OK and out_format != "png":
        # Prioriza PDF quando possível (tamanho exato 40 x 25 mm)
        pdf_bytes = _output_pdf_from_png(label_png)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            download_name=f"{modelo}_{serial}.pdf",
            as_attachment=False,
        )

    # PNG (com DPI correto)
    return send_file(
        str(label_png),
        mimetype="image/png",
        download_name=f"{modelo}_{serial}.png",
        as_attachment=False,
    )

@imprimir_etiqueta_bp.route("/<assembly_id>/confirmar", methods=["POST"])
def confirmar_primeira_impressao(assembly_id):
    payload = request.get_json() or {}
    usuario = (payload.get("usuario") or "Operador").strip()

    # Carrega montagem real
    m = None
    if assembly_id.isdigit():
        m = Montagem.query.get(int(assembly_id))
    else:
        m = Montagem.query.filter_by(serial=assembly_id).first()

    if not m:
        return abort(404, "Montagem não encontrada.")
    if m.status == "CANCELADA":
        return abort(409, "Montagem cancelada; não é possível confirmar impressão.")
    if m.label_printed:
        return abort(409, "Etiqueta já havia sido confirmada. Use reimpressão.")

    # marca impressa
    m.label_printed = True
    m.label_printed_at = datetime.utcnow()
    m.label_printed_by = usuario
    m.label_print_count = max(1, (m.label_print_count or 0) + 1)  # primeira impressão conta 1
    db.session.commit()

    return jsonify({"ok": True, "message": "Impressão confirmada.", "assembly_id": m.id})

@imprimir_etiqueta_bp.route("/<assembly_id>/reimprimir", methods=["POST", "GET"])
def reimprimir_label(assembly_id):
    if request.method == "GET":
        resp = preview_label(assembly_id)
        if hasattr(resp, "headers"):
            resp.headers["X-Reprint-Preview"] = "1"
        return resp

    # POST
    payload = request.get_json() or {}
    motivo = (payload.get("motivo") or "").strip()
    usuario = (payload.get("usuario") or "Operador").strip()
    if not motivo:
        return abort(400, "Motivo da reimpressão é obrigatório.")

    m = None
    if assembly_id.isdigit():
        m = Montagem.query.get(int(assembly_id))
    else:
        m = Montagem.query.filter_by(serial=assembly_id).first()

    if not m:
        return abort(404, "Montagem não encontrada.")

    # Se nunca confirmou, trate como primeira (mas pedimos usar confirmar)
    if not m.label_printed:
        return abort(409, "Etiqueta ainda não confirmada. Confirme a primeira impressão.")

    # registra log + incrementa contador
    log = LabelReprintLog(montagem_id=m.id, motivo=motivo, reprint_by=usuario)
    m.label_print_count = (m.label_print_count or 1) + 1
    db.session.add(log)
    db.session.commit()

    return jsonify({"ok": True, "message": "Reimpressão registrada.", "assembly_id": m.id})
