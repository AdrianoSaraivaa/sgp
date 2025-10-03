from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app import db

# ⚠️ Usar sempre os MODELOS ORM (SQLAlchemy)
# Peca vem de models_sqla (não do dataclass).
try:
    from app.models_sqla import Peca  # type: ignore
except Exception:  # pragma: no cover
    Peca = None  # type: ignore

# Deduplicação de alertas (historiza entradas/saídas do alerta)
try:
    # Corrigido para usar models_sqla
    from app.models_sqla import GPROPAlert as GPRopAlert  # type: ignore
except Exception:  # pragma: no cover
    GPRopAlert = None  # type: ignore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _coalesce_int(value: Optional[int], default: int = 0) -> int:
    try:
        return int(value) if value is not None else default
    except Exception:
        return default


def _infer_model_code_from_peca(peca: "Peca") -> str:
    """
    Tenta inferir o model_code a partir da peça "conjunto".
    Preferimos usar um mapeamento central (capacidade_service), se existir.
    Fallback: usa o próprio código_pneumark.
    """
    code = getattr(peca, "codigo_pneumark", None) or ""
    # Tenta buscar via capacidade_service (fonte única, se implementado)
    try:
        from app.services.producao.capacidade_service import model_code_from_conjunto  # type: ignore

        mc = model_code_from_conjunto(code)
        if mc:
            return mc
    except Exception:
        pass
    return str(code or "").strip()


def _get_capacidade(model_code: str) -> Optional[int]:
    """Retorna uma capacidade inteira (unidades/periodo) se o serviço existir; caso contrário, None."""
    try:
        from app.services.producao.capacidade_service import calcular_capacidade_modelo  # type: ignore

        cap = calcular_capacidade_modelo(model_code)
        if cap is None:
            return None
        try:
            return int(cap)
        except Exception:
            return None
    except Exception:
        return None


def _eval_rop_for_conjunto(peca: "Peca") -> Dict[str, Any]:
    """Calcula o estado ROP para uma peça do tipo 'conjunto'."""
    atual = _coalesce_int(getattr(peca, "estoque_atual", 0), 0)
    min_ = _coalesce_int(getattr(peca, "estoque_minimo", 0), 0)  # Corrigido nome do campo
    max_ = _coalesce_int(getattr(peca, "estoque_maximo", 0), 0)  # Corrigido nome do campo

    ponto_pedido = _coalesce_int(getattr(peca, "ponto_pedido", 0), 0)
    in_alert = atual <= ponto_pedido
    sugerido = max(0, max_ - atual) if in_alert else 0

    model_code = _infer_model_code_from_peca(peca)
    return {
        "peca_id": getattr(peca, "id", None),
        "codigo_conjunto": getattr(peca, "codigo_pneumark", ""),
        "descricao": getattr(peca, "descricao", ""),
        "model_code": model_code,
        "atual": atual,
        "min": min_,
        "max": max_,
        "ponto_pedido": ponto_pedido,
        "in_alert": in_alert,
        "sugerido": sugerido,
    }


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def list_rop_needs(session) -> List[Dict[str, Any]]:
    """
    Retorna necessidades de produção por modelo (quantas montar), no formato:
        [ {model_code, atual, min, max, sugerido, codigo_conjunto, descricao} ]
    Regra: se estoque_atual <= estoque_min -> sugerido = max(0, estoque_max - estoque_atual); senão 0.
    """
    needs: List[Dict[str, Any]] = []

    if Peca is None:
        logger.warning("[ROP] Model Peca indisponível; retornando lista vazia.")
        return needs

    # Consulta somente peças do tipo 'conjunto' (máquinas acabadas)
    conjuntos: List[Peca] = (
        session.query(Peca)
        .filter(Peca.tipo == "conjunto")  # type: ignore[attr-defined]
        .all()
    )

    for conj in conjuntos:
        st = _eval_rop_for_conjunto(conj)
        if st["sugerido"] > 0:
            needs.append(
                {
                    "model_code": st["model_code"],
                    "atual": st["atual"],
                    "min": st["min"],
                    "max": st["max"],
                    "sugerido": st["sugerido"],
                    "codigo_conjunto": st["codigo_conjunto"],
                    "descricao": st["descricao"],
                }
            )

    # Ordena por maior necessidade primeiro
    needs.sort(key=lambda x: int(x.get("sugerido") or 0), reverse=True)
    return needs


def handle_rop_on_change(
    peca_conjunto: "Peca", session, force_email: bool = False
) -> None:
    """
    Deve ser chamado sempre que o estoque de um CONJUNTO mudar (ex.: após montar máquinas).
    - Atualiza/Cria registro em gp_rop_alerts para deduplicação.
    - Dispara e-mail ao entrar em alerta (estoque_atual <= estoque_min) — 1 vez por entrada, ou se force_email=True.
    - Ao sair do alerta (estoque_atual > estoque_min), zera a flag in_alert.
    """
    if GPRopAlert is None:
        logger.warning(
            "[ROP] GPRopAlert indisponível; enviando e-mail sem deduplicação, se necessário."
        )
    st = _eval_rop_for_conjunto(peca_conjunto)

    # Se não está em alerta e não existe histórico, nada a fazer além de garantir limpeza se já houve alerta
    try:
        alert_obj = None
        if GPRopAlert:
            alert_obj = (
                session.query(GPRopAlert)
                .filter_by(peca_id=getattr(peca_conjunto, "id"))
                .one_or_none()
            )
            if alert_obj is None:
                alert_obj = GPRopAlert(
                    peca_id=getattr(peca_conjunto, "id"), in_alert=False
                )
                session.add(alert_obj)
                session.flush()
    except Exception as e:
        logger.exception(f"[ROP] Falha ao consultar/criar GPRopAlert: {e}")
        # Prossegue sem deduplicação
        alert_obj = None

    try:
        entered_alert = bool(st["in_alert"])
        should_email = False

        if alert_obj is not None:
            # Transições
            if entered_alert and not bool(getattr(alert_obj, "in_alert", False)):
                # Entrou em alerta agora
                alert_obj.in_alert = True
                alert_obj.updated_at = datetime.utcnow()
                should_email = True
            elif entered_alert and force_email:
                # Já estava em alerta mas queremos forçar reenvio
                should_email = True
            elif not entered_alert and bool(getattr(alert_obj, "in_alert", False)):
                # Saiu do alerta
                alert_obj.in_alert = False
                alert_obj.updated_at = datetime.utcnow()
                should_email = False  # não envia e-mail ao sair

            session.commit()
        else:
            # Sem objeto de deduplicação: decide e-mail baseado apenas no estado atual
            should_email = entered_alert or force_email

        if should_email:
            _send_rop_email(peca_conjunto, st)
    except Exception as e:
        session.rollback()
        logger.exception(f"[ROP] Erro ao atualizar estado/dispatch de e-mail: {e}")


# ---------------------------------------------------------------------------
# E-mail
# ---------------------------------------------------------------------------


def _send_rop_email(peca_conjunto: "Peca", st: Dict[str, Any]) -> None:
    """Envia e-mail de alerta de ponto de pedido para CONJUNTO."""
    try:
        from app.services.montagem.notifications.email_service import send_email  # type: ignore
    except Exception as e:  # pragma: no cover
        logger.error(f"[ROP][EMAIL] Serviço de e-mail indisponível: {e}")
        return

    model_code = st.get("model_code") or _infer_model_code_from_peca(peca_conjunto)
    capacidade = _get_capacidade(model_code)
    cap_line = ""
    if capacidade is not None and capacidade <= 0:
        cap_line = (
            "\nObservação: capacidade de produção atual está ZERO para este modelo."
        )

    assunto = f"[Produção] Ponto de pedido — {model_code}"
    corpo = (
        f"Modelo: {model_code}\n"
        f"Código conjunto: {st.get('codigo_conjunto')}\n"
        f"Descrição: {st.get('descricao')}\n"
        f"Estoque atual: {st.get('atual')}\n"
        f"Estoque mínimo: {st.get('min')}\n"
        f"Estoque máximo: {st.get('max')}\n"
        f"Sugerido montar: {st.get('sugerido')}{cap_line}\n"
        "\nAcione o PCP para programar a montagem."
    )

    # Destinatário padrão; pode ser tornado configurável via ENV
    to = "producao@pneumark.com.br"
    try:
        send_email(to=to, subject=assunto, body=corpo)
        logger.info(f"[ROP][EMAIL] Enviado para {to}: {assunto}")
    except Exception as e:
        logger.error(f"[ROP][EMAIL] Falha ao enviar: {e}")
