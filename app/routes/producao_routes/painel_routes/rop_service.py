from datetime import datetime
from typing import List, Dict, Any, Optional

from app.models.estoque_models.peca import Peca
from app.models.producao_models.painel_models.alerts import GPRopAlert
from app.services.montagem.notifications.email_service import send_email


# ------------------------
# Helpers
# ------------------------
def _is_conjunto(peca: Peca) -> bool:
    return bool(peca and (peca.tipo or "").strip().lower() == "conjunto")


def _get_capacidade(modelo: str) -> Optional[int]:
    """
    Tenta consultar a capacidade do modelo. Se não existir o serviço, ignora.
    Retorna int (capacidade por período) ou None se indisponível.
    """
    try:
        # Ajuste este import se seu serviço tiver outro caminho/assinatura
        from app.services.montagem.capacidade_service import calcular_capacidade_modelo
        cap = calcular_capacidade_modelo(modelo)
        if isinstance(cap, dict) and "capacidade" in cap:
            return int(cap["capacidade"])
        if isinstance(cap, (int, float)):
            return int(cap)
    except Exception:
        pass
    return None


def _eval_rop_for_conjunto(conj: Peca) -> Dict[str, Any]:
    """
    Regra de disparo:
      - Consideramos ALERTA quando estoque_atual <= ponto_pedido
      - Quantidade sugerida = estoque_maximo - estoque_atual (se > 0)
    """
    estoque_atual  = int(conj.estoque_atual or 0)
    ponto_pedido   = int(conj.ponto_pedido or 0)
    estoque_maximo = int(conj.estoque_maximo or 0)

    in_alert = (estoque_atual <= ponto_pedido and estoque_maximo > estoque_atual)
    sugerida = max(estoque_maximo - estoque_atual, 0) if in_alert else 0

    capacidade = _get_capacidade(conj.codigo_pneumark or conj.descricao or "")
    cap_zero = (capacidade == 0) if capacidade is not None else False

    return {
        "in_alert": in_alert,
        "sugerida": sugerida,
        "estoque_atual": estoque_atual,
        "ponto_pedido": ponto_pedido,
        "estoque_maximo": estoque_maximo,
        "capacidade_zero": cap_zero,
    }


# ------------------------
# API para o Painel
# ------------------------
def list_rop_needs(session) -> List[Dict[str, Any]]:
    """
    Lista NECESSIDADES (read-only) para o painel.
    Apenas itens Peca.tipo == "conjunto" que estejam em alerta.
    """
    needs: List[Dict[str, Any]] = []
    conjuntos: List[Peca] = session.query(Peca).filter(Peca.tipo == "conjunto").all()

    for conj in conjuntos:
        st = _eval_rop_for_conjunto(conj)
        if st["in_alert"] and st["sugerida"] > 0:
            needs.append({
                "modelo": conj.codigo_pneumark or conj.descricao or f"Conjunto {conj.id}",
                "codigo": conj.codigo_pneumark,
                "necessaria": int(st["sugerida"]),
                "estoque_atual": st["estoque_atual"],
                "ponto_pedido": st["ponto_pedido"],
                "estoque_maximo": st["estoque_maximo"],
                "capacidade_zero": st["capacidade_zero"],
            })
    return needs


# ------------------------
# Integração (disparo de e-mail 1x por entrada em alerta)
# ------------------------
def handle_rop_on_change(conjunto: Peca, session, *, force_email: bool = False) -> None:
    """
    Chamar SEMPRE que um CONJUNTO tiver:
      - mudança de estoque_atual / ponto_pedido / estoque_maximo, OU
      - entrada de produto acabado (finalização de ordem).
    Envia e-mail UMA VEZ quando transita para estado de alerta.
    """
    if not _is_conjunto(conjunto):
        return

    st = _eval_rop_for_conjunto(conjunto)

    # Registro de deduplicação (1 linha por conjunto)
    alert = session.query(GPRopAlert).filter_by(peca_id=conjunto.id).one_or_none()
    if alert is None:
        alert = GPRopAlert(peca_id=conjunto.id, in_alert=False)
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

    session.commit()


def _send_rop_email(conjunto: Peca, st: Dict[str, Any]) -> None:
    modelo = conjunto.codigo_pneumark or conjunto.descricao or f"Conjunto {conjunto.id}"
    to = "producao@pneumark.com.br"

    qtde = int(st["sugerida"])
    estoque_atual  = st["estoque_atual"]
    ponto_pedido   = st["ponto_pedido"]
    estoque_maximo = st["estoque_maximo"]

    assunto = f"[Produção] Ponto de pedido — {modelo}"
    obs_cap = ""
    if st.get("capacidade_zero"):
        obs_cap = "\nObservação: Capacidade atual indisponível (ver gargalos/capacidade)."

    corpo = f"""Boa tarde!

O estoque de Máquinas do modelo {modelo} atingiu o ponto de pedido.

Parâmetros:
- Estoque Atual: {estoque_atual}
- Ponto de Pedido: {ponto_pedido}
- Estoque Máximo: {estoque_maximo}

Ação solicitada:
- Montar {qtde} unidade(s) do modelo {modelo}.
  (Cálculo: Estoque Máximo - Estoque Atual)

A partir deste e-mail o prazo começa a ser contado.{obs_cap}

Obrigado,
SGP • Pneumark
"""
    try:
        send_email(to=to, subject=assunto, body=corpo)
    except Exception as e:
        # Não quebrar fluxo se SMTP falhar
        print(f"[ROP][EMAIL] Falha ao enviar e-mail: {e}")
