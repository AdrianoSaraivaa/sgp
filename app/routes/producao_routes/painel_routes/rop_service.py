# app/routes/producao_routes/painel_routes/rop_service.py

from __future__ import annotations
from datetime import datetime
from typing import List, Dict, Any, Optional

# Tentativa de import “suave” — se falhar, tratamos no código.
try:
    from app.models.estoque_models.peca import Peca  # ORM
except Exception:  # noqa
    Peca = None  # type: ignore

# E-mail (se existir)
try:
    from app.services.montagem.notifications.email_service import send_email
except Exception:  # noqa
    def send_email(*args, **kwargs):
        print("[ROP][EMAIL] send_email indisponível; simulando envio.")

def _log(msg: str) -> None:
    print(f"[ROP_SERVICE] {msg}")

# ------------------------
# Helpers
# ------------------------
def _is_conjunto(peca) -> bool:
    try:
        t = getattr(peca, "tipo", "") or ""
        return str(t).strip().lower() == "conjunto"
    except Exception:
        return False

def _get_capacidade(modelo: str) -> Optional[int]:
    """
    Tenta consultar a capacidade do modelo. Se não existir o serviço, ignora.
    Retorna int (capacidade por período) ou None se indisponível.
    """
    try:
        from app.services.montagem.capacidade_service import calcular_capacidade_modelo
        cap = calcular_capacidade_modelo(modelo)
        if isinstance(cap, dict) and "capacidade" in cap:
            return int(cap["capacidade"])
        if isinstance(cap, (int, float)):
            return int(cap)
    except Exception:
        pass
    return None

def _eval_rop_for_conjunto(conj) -> Dict[str, Any]:
    """
    Regra:
      - ALERTA quando estoque_atual <= ponto_pedido e estoque_maximo > estoque_atual
      - sugerida = estoque_maximo - estoque_atual (se > 0)
    """
    estoque_atual  = int(getattr(conj, "estoque_atual", 0) or 0)
    ponto_pedido   = int(getattr(conj, "ponto_pedido", 0) or 0)
    estoque_maximo = int(getattr(conj, "estoque_maximo", 0) or 0)

    in_alert = (estoque_atual <= ponto_pedido and estoque_maximo > estoque_atual)
    sugerida = (estoque_maximo - estoque_atual) if in_alert else 0
    if sugerida < 0:
        sugerida = 0

    modelo_cod = getattr(conj, "codigo_pneumark", None) or getattr(conj, "descricao", None) or ""
    capacidade = _get_capacidade(str(modelo_cod))
    cap_zero = (capacidade == 0) if capacidade is not None else False

    return {
        "in_alert": in_alert,
        "sugerida": int(sugerida),
        "estoque_atual": estoque_atual,
        "ponto_pedido": ponto_pedido,
        "estoque_maximo": estoque_maximo,
        "capacidade_zero": cap_zero,
    }

# ------------------------
# API para o Painel (consumida por /producao/gp/needs)
# ------------------------
def list_rop_needs(session) -> List[Dict[str, Any]]:
    """
    Lista NECESSIDADES para o painel.
    Apenas itens Peca.tipo == "conjunto" que estejam em alerta.
    Sem exceção vazar (retorna [] em caso de falha).
    """
    needs: List[Dict[str, Any]] = []

    # Se a model Peca não carregou, não derruba a app
    if Peca is None:
        _log("Model Peca indisponível; retornando lista vazia.")
        return needs

    # SQLAlchemy pode estar em versão/config distinta — tentamos e caímos no seguro.
    try:
        conjuntos = session.query(Peca).filter(getattr(Peca, "tipo") == "conjunto").all()  # type: ignore
    except Exception as e:
        _log(f"Erro consultando Peca: {repr(e)}")
        return needs

    for conj in conjuntos:
        try:
            if not _is_conjunto(conj):
                continue
            st = _eval_rop_for_conjunto(conj)
            if st["in_alert"] and st["sugerida"] > 0:
                needs.append({
                    "modelo": getattr(conj, "codigo_pneumark", None) or getattr(conj, "descricao", None) or f"Conjunto {getattr(conj, 'id', '')}",
                    "codigo": getattr(conj, "codigo_pneumark", None),
                    "necessaria": int(st["sugerida"]),
                    "estoque_atual": st["estoque_atual"],
                    "ponto_pedido": st["ponto_pedido"],
                    "estoque_maximo": st["estoque_maximo"],
                    "capacidade_zero": st["capacidade_zero"],
                })
        except Exception as e:
            _log(f"Falha ao processar conjunto id={getattr(conj, 'id', '?')}: {e}")

    return needs

# ------------------------
# Integração (disparo de e-mail 1x por entrada em alerta)
# ------------------------
def handle_rop_on_change(conjunto, session, *, force_email: bool = False) -> None:
    """
    Chamar SEMPRE que um CONJUNTO tiver mudança de parâmetros/estoque.
    Envia e-mail UMA VEZ quando entra em alerta.
    """
    # Guard
    if not _is_conjunto(conjunto):
        return

    # Estado atual
    st = _eval_rop_for_conjunto(conjunto)

    # Registro de deduplicação
    try:
        from app.models.producao_models.painel_models.alerts import GPRopAlert
    except Exception:
        _log("GPRopAlert indisponível; pulando deduplicação de e-mail.")
        if st["in_alert"] or force_email:
            _send_rop_email(conjunto, st)
        return

    alert = session.query(GPRopAlert).filter_by(peca_id=getattr(conjunto, "id")).one_or_none()
    if alert is None:
        alert = GPRopAlert(peca_id=getattr(conjunto, "id"), in_alert=False)
        session.add(alert)
        session.flush()

    entering_alert = st["in_alert"] and (not alert.in_alert)
    leaving_alert  = (not st["in_alert"]) and alert.in_alert

    if entering_alert or force_email:
        _send_rop_email(conjunto, st)
        alert.in_alert = True
        alert.last_sent_at = datetime.utcnow()

    if leaving_alert:
        alert.in_alert = False

    try:
        session.commit()
    except Exception as e:
        session.rollback()
        _log(f"Commit falhou em handle_rop_on_change: {e}")

def _send_rop_email(conjunto, st: Dict[str, Any]) -> None:
    modelo = getattr(conjunto, "codigo_pneumark", None) or getattr(conjunto, "descricao", None) or f"Conjunto {getattr(conjunto, 'id', '')}"
    to = "producao@pneumark.com.br"

    qtde = int(st.get("sugerida", 0))
    estoque_atual  = st.get("estoque_atual", 0)
    ponto_pedido   = st.get("ponto_pedido", 0)
    estoque_maximo = st.get("estoque_maximo", 0)

    assunto = f"[Produção] Ponto de pedido — {modelo}"
    obs_cap = ""
    if st.get("capacidade_zero"):
        obs_cap = "\nObservação: Capacidade atual indisponível (ver gargalos/capacidade)."

    corpo = (
        f"Boa tarde!\n\n"
        f"O estoque de Máquinas do modelo {modelo} atingiu o ponto de pedido.\n\n"
        f"Parâmetros:\n"
        f"- Estoque Atual: {estoque_atual}\n"
        f"- Ponto de Pedido: {ponto_pedido}\n"
        f"- Estoque Máximo: {estoque_maximo}\n\n"
        f"Ação solicitada:\n"
        f"- Montar {qtde} unidade(s) do modelo {modelo}.\n"
        f"  (Cálculo: Estoque Máximo - Estoque Atual)\n\n"
        f"A partir deste e-mail o prazo começa a ser contado.{obs_cap}\n\n"
        f"Obrigado,\n"
        f"SGP • Pneumark\n"
    )

    try:
        send_email(to=to, subject=assunto, body=corpo)
        _log(f"E-mail enviado para {to} ({assunto})")
    except Exception as e:
        _log(f"[EMAIL] Falha ao enviar: {e}")
