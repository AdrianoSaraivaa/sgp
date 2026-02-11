from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app import db

# ⚠️ Usar sempre os MODELOS ORM (SQLAlchemy)
try:
    from app.models_sqla import Peca  # type: ignore
except Exception:
    Peca = None  # type: ignore

try:
    from app.models_sqla import GPROPAlert as GPRopAlert  # type: ignore
except Exception:
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
    code = getattr(peca, "codigo_pneumark", None) or ""
    try:
        from app.services.producao.capacidade_service import model_code_from_conjunto  # type: ignore

        mc = model_code_from_conjunto(code)
        if mc:
            return mc
    except Exception:
        pass
    return str(code or "").strip()


def _get_capacidade(model_code: str) -> Optional[int]:
    try:
        from app.services.producao.capacidade_service import calcular_capacidade_modelo  # type: ignore

        cap = calcular_capacidade_modelo(model_code)
        return int(cap) if cap is not None else None
    except Exception:
        return None


def _eval_rop_for_conjunto(peca: "Peca") -> Dict[str, Any]:
    atual = _coalesce_int(getattr(peca, "estoque_atual", 0), 0)
    min_ = _coalesce_int(getattr(peca, "estoque_minimo", 0), 0)
    max_ = _coalesce_int(getattr(peca, "estoque_maximo", 0), 0)
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
    needs: List[Dict[str, Any]] = []
    if Peca is None:
        logger.warning("[ROP] Model Peca indisponível; retornando lista vazia.")
        return needs

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

    needs.sort(key=lambda x: int(x.get("sugerido") or 0), reverse=True)
    return needs


def build_needs_banner(needs: List[Dict[str, Any]]) -> str:
    if not needs:
        return ""
    parts = []
    for row in needs:
        model = row.get("model_code") or row.get("codigo_conjunto")
        qtd = row.get("sugerido") or 0
        if model and qtd:
            parts.append(f"{model} +{qtd}")
    return f"Montar: {' • '.join(parts)}" if parts else ""


def get_rop_needs_and_banner(session) -> Dict[str, Any]:
    needs = list_rop_needs(session)
    banner = build_needs_banner(needs)
    return {"needs": needs, "needs_banner": banner}


def handle_rop_on_change(
    peca_conjunto: "Peca", session, force_email: bool = False
) -> None:
    if GPRopAlert is None:
        logger.warning(
            "[ROP] GPRopAlert indisponível; enviando e-mail sem deduplicacao."
        )
    st = _eval_rop_for_conjunto(peca_conjunto)

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
        alert_obj = None

    try:
        entered_alert = bool(st["in_alert"])
        should_email = False

        if alert_obj is not None:
            if entered_alert and not bool(getattr(alert_obj, "in_alert", False)):
                alert_obj.in_alert = True
                alert_obj.updated_at = datetime.utcnow()
                should_email = True
            elif entered_alert and force_email:
                should_email = True
            elif not entered_alert and bool(getattr(alert_obj, "in_alert", False)):
                alert_obj.in_alert = False
                alert_obj.updated_at = datetime.utcnow()
                should_email = False

            session.commit()
        else:
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
    try:
        from app.services.montagem.notifications.email_service import send_email  # type: ignore
    except Exception as e:
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

    to = "producao@pneumark.com.br"
    try:
        send_email(to=to, subject=assunto, body=corpo)
        logger.info(f"[ROP][EMAIL] Enviado para {to}: {assunto}")
    except Exception as e:
        logger.error(f"[ROP][EMAIL] Falha ao enviar: {e}")
