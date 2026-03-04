# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import logging

from sqlalchemy import select  # usado para with_for_update e queries
from sqlalchemy.orm import Session

from app import db

# === MODELOS DO SEU PROJETO (ajuste caminho se necessário) ===
from app.models_sqla import (
    Peca,
)  # deve ter: codigo_pneumark, tipo ("peca"/"conjunto"), estoque_atual

# Movimentação é opcional. Se você criar depois, basta descomentar o import e os usos.
try:
    from app.models_sqla import (
        MovimentacaoEstoque,
    )  # id, timestamp, tipo_mov, codigo_peca, quantidade, referencia, usuario
except Exception:
    MovimentacaoEstoque = None  # opcional

# === SERVICE QUE VOCÊ JÁ TEM ===
from app.services.montagem.capacidade_service import calcular_capacidade_modelo

# Onde está a BOM (estrutura por conjunto)
from app.models_sqla import EstruturaMaquina  # BOM está nessa tabela

logger = logging.getLogger(__name__)


# =============================
# Exceções específicas
# =============================
# ====================================================================
# [BLOCO] CLASSE
# [NOME] FaltaItem
# [RESPONSABILIDADE] Estrutura de dados para representar falta de item de estoque durante validação da BOM
# ====================================================================
@dataclass
class FaltaItem:
    codigo_peca: str
    necessario: float
    disponivel: float


# ====================================================================
# [FIM BLOCO] FaltaItem
# ====================================================================


# ====================================================================
# [BLOCO] CLASSE
# [NOME] EstoqInsuficiente
# [RESPONSABILIDADE] Exceção para indicar estoque insuficiente em um ou mais itens da BOM
# ====================================================================
class EstoqInsuficiente(Exception):
    def __init__(self, faltas: List[FaltaItem]):
        self.faltas = faltas
        super().__init__("Estoque insuficiente para 1+ itens da BOM.")


# ====================================================================
# [FIM BLOCO] EstoqInsuficiente
# ====================================================================


# ====================================================================
# [BLOCO] CLASSE
# [NOME] BomIndisponivel
# [RESPONSABILIDADE] Exceção para indicar ausência/indisponibilidade de BOM para o modelo/conjunto
# ====================================================================
class BomIndisponivel(Exception):
    pass


# ====================================================================
# [FIM BLOCO] BomIndisponivel
# ====================================================================


# Para a movimentação do produto acabado via mapeamento modelo→conjunto
# ====================================================================
# [BLOCO] CLASSE
# [NOME] ProdutoAcabadoInvalido
# [RESPONSABILIDADE] Exceção de validação para operações de estoque do produto acabado (FG)
# ====================================================================
class ProdutoAcabadoInvalido(Exception):
    """Erros de validação do produto acabado (mapeamento/conjunto ausente)."""

    pass


# ====================================================================
# [FIM BLOCO] ProdutoAcabadoInvalido
# ====================================================================

# =============================
# Mapeamento modelo → código do conjunto (BOM/FG)
# (idealmente isso pode viver em um 'resolver' central)
# =============================
MODEL_TO_CONJUNTO: Dict[str, str] = {
    "PM2100": "7-000",
    "PM2200": "2-000",
    "PM700": "28-000",
    "PM25": "PM0025",
}


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _resolver_conjunto_por_modelo
# [RESPONSABILIDADE] Resolver o código do conjunto (FG) correspondente ao modelo via mapeamento local
# ====================================================================
def _resolver_conjunto_por_modelo(modelo: str) -> str:
    code = MODEL_TO_CONJUNTO.get((modelo or "").strip())
    if not code:
        raise ProdutoAcabadoInvalido(
            f"Sem mapeamento de conjunto para modelo '{modelo}'."
        )
    return code


# ====================================================================
# [FIM BLOCO] _resolver_conjunto_por_modelo
# ====================================================================


# =============================
# Helpers de BOM / produto acabado
# =============================
# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _extrair_bom_capacidade
# [RESPONSABILIDADE] Extrair lista (codigo_peca, qtd_por_unidade) do payload retornado pelo capacidade_service
# ====================================================================
def _extrair_bom_capacidade(data: dict) -> List[Tuple[str, float]]:
    """
    Espera:
    {
      "produto_acabado": { "modelo": "...", "codigo_conjunto": "7-000", ...},
      "bom": [ { "codigo_peca": "MTR-001", "quantidade": 2 }, ... ]
    }
    Retorna lista [(codigo_peca, qtd_por_unidade), ...]
    """
    if not data or "bom" not in data:
        raise BomIndisponivel("Payload de capacidade sem 'bom'.")

    bom_raw = data["bom"]
    out: List[Tuple[str, float]] = []
    for item in bom_raw:
        cod = str(item.get("codigo_peca") or "").strip()
        qtd = float(item.get("quantidade") or 0)
        if cod and qtd > 0:
            out.append((cod, qtd))
    if not out:
        raise BomIndisponivel("BOM vazia após parse.")
    return out


# ====================================================================
# [FIM BLOCO] _extrair_bom_capacidade
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] _extrair_codigo_conjunto
# [RESPONSABILIDADE] Extrair codigo_conjunto do payload de capacidade com fallback para compatibilidade
# ====================================================================
def _extrair_codigo_conjunto(data: dict, modelo: str) -> str:
    """
    Pega produto_acabado.codigo_conjunto; fallback: usa 'modelo' (não ideal).
    (Mantido para compatibilidade com suas reservas/estornos de componentes.)
    """
    try:
        pac = data.get("produto_acabado") or {}
        cod = str(pac.get("codigo_conjunto") or "").strip()
        if cod:
            return cod
    except Exception:
        pass
    logger.warning(
        "Não achei produto_acabado.codigo_conjunto; usando modelo como fallback."
    )
    return (modelo or "").strip()


# ====================================================================
# [FIM BLOCO] _extrair_codigo_conjunto
# ====================================================================


# =============================
# Funções públicas — Componentes (Reserva/Estorno)
# =============================
# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] reservar_componentes_para_montagem
# [RESPONSABILIDADE] Reservar componentes da BOM no estoque para uma quantidade de unidades em montagem
# ====================================================================
def reservar_componentes_para_montagem(
    modelo: str,
    quantidade_unidades: int,
    usuario: str = "Sistema",
    referencia: Optional[str] = None,
    session: Optional[Session] = None,
) -> None:
    """
    Na abertura da ordem/serial: baixa do estoque os componentes da BOM × quantidade_unidades.
    NÃO depende da chave 'bom' do capacidade_service.
    Lê a BOM direto da tabela EstruturaMaquina usando o codigo_conjunto.
    """
    if quantidade_unidades <= 0:
        return

    sess = session or db.session

    # 1) Descobrir o código do conjunto (produto acabado) via capacidade_service
    #    Se não vier, caímos no fallback usando o próprio 'modelo' como código.
    try:
        data_cap = calcular_capacidade_modelo(
            modelo
        )  # pode não ter 'bom', só queremos o codigo_conjunto
        codigo_conjunto = _extrair_codigo_conjunto(data_cap, modelo)
    except Exception:
        codigo_conjunto = (modelo or "").strip()

    if not codigo_conjunto:
        raise BomIndisponivel(
            f"Não foi possível identificar o código do conjunto para o modelo '{modelo}'."
        )

    # 2) Carregar a BOM direto no DB: todas as linhas de EstruturaMaquina para esse conjunto
    itens_bom = (
        sess.execute(
            select(EstruturaMaquina).where(
                EstruturaMaquina.codigo_maquina == codigo_conjunto
            )
        )
        .scalars()
        .all()
    )

    if not itens_bom:
        raise BomIndisponivel(
            f"Nenhum item de BOM encontrado em EstruturaMaquina para '{codigo_conjunto}' (modelo '{modelo}')."
        )

    # Monta lista [(codigo_peca, qtd_por_unidade)]
    bom: List[Tuple[str, float]] = []
    for it in itens_bom:
        try:
            qtd = float(it.quantidade or 0)
        except Exception:
            qtd = 0.0
        cod = (it.codigo_peca or "").strip()
        if cod and qtd > 0:
            bom.append((cod, qtd))

    if not bom:
        raise BomIndisponivel(
            f"BOM vazia em EstruturaMaquina para '{codigo_conjunto}'."
        )

    # 3) Carregar e travar as peças necessárias
    pecas_locked: Dict[str, Peca] = {}
    for codigo_peca, _ in bom:
        p: Optional[Peca] = sess.execute(
            select(Peca).where(Peca.codigo_pneumark == codigo_peca).with_for_update()
        ).scalar_one_or_none()
        if not p:
            raise BomIndisponivel(
                f"Peça '{codigo_peca}' não cadastrada (Peca.codigo_pneumark)."
            )
        pecas_locked[codigo_peca] = p  # type: ignore

    # 4) Validar saldos
    faltas: List[FaltaItem] = []
    for codigo_peca, qtd_un in bom:
        total = float(qtd_un) * quantidade_unidades
        disponivel = float(pecas_locked[codigo_peca].estoque_atual or 0)
        if disponivel < total:
            faltas.append(
                FaltaItem(
                    codigo_peca=codigo_peca, necessario=total, disponivel=disponivel
                )
            )
    if faltas:
        raise EstoqInsuficiente(faltas)

    # 5) Abater do estoque
    for codigo_peca, qtd_un in bom:
        total = float(qtd_un) * quantidade_unidades
        p = pecas_locked[codigo_peca]
        p.estoque_atual = float(p.estoque_atual or 0) - total
        sess.add(p)

        # Se você tiver MovimentacaoEstoque no futuro, pode registrar aqui.


# ====================================================================
# [FIM BLOCO] reservar_componentes_para_montagem
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] estornar_reserva_componentes
# [RESPONSABILIDADE] Estornar a reserva de componentes da BOM no estoque quando a ordem/serial for cancelada
# ====================================================================
def estornar_reserva_componentes(
    modelo: str,
    quantidade_unidades: int,
    usuario: str = "Sistema",
    referencia: Optional[str] = None,
    session: Optional[Session] = None,
) -> None:
    """
    Caso a ordem/serial seja cancelada antes da conclusão: devolve a reserva ao estoque.
    - Soma BOM × quantidade_unidades em estoque_atual.
    - (Opcional) registra movimentação tipo 'entrada' motivo 'ESTORNO_RESERVA'.
    """
    if quantidade_unidades <= 0:
        return

    sess = session or db.session
    cap = calcular_capacidade_modelo(modelo)
    bom = _extrair_bom_capacidade(cap)

    pecas_locked: Dict[str, Peca] = {}
    for codigo_peca, _ in bom:
        p: Optional[Peca] = sess.execute(
            select(Peca).where(Peca.codigo_pneumark == codigo_peca).with_for_update()
        ).scalar_one_or_none()
        if not p:
            logger.warning(
                f"Peça '{codigo_peca}' não encontrada no estorno; ignorando."
            )
            continue
        pecas_locked[codigo_peca] = p  # type: ignore

    for codigo_peca, qtd_un in bom:
        total = float(qtd_un) * quantidade_unidades
        p = pecas_locked.get(codigo_peca)
        if not p:
            continue
        p.estoque_atual = float(p.estoque_atual or 0) + total
        sess.add(p)

        if MovimentacaoEstoque is not None:
            try:
                mov = MovimentacaoEstoque(
                    tipo_mov="entrada",
                    codigo_peca=codigo_peca,
                    quantidade=total,
                    referencia=referencia,
                    usuario=usuario,
                )
                sess.add(mov)
            except Exception as e:
                logger.warning(
                    f"Falha ao registrar movimentação de entrada (estorno) para {codigo_peca}: {e}"
                )


# ====================================================================
# [FIM BLOCO] estornar_reserva_componentes
# ====================================================================


# =============================
# Produto Acabado — Entrada e Estorno (+/- no FG via mapeamento)
# =============================
# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] registrar_conclusao_produto_acabado
# [RESPONSABILIDADE] Registrar entrada de produto acabado (conjunto) no estoque com base no modelo
# ====================================================================
def registrar_conclusao_produto_acabado(
    modelo: str,
    quantidade: int,
    usuario: str,
    referencia: Optional[str] = None,
    session: Optional[Session] = None,
) -> str:
    """
    Dá ENTRADA (+quantidade) no estoque do CONJUNTO correspondente ao modelo.
    - Usa o mapeamento MODEL_TO_CONJUNTO (não depende de capacidade_service).
    - Deve rodar DENTRO da mesma transação de quem chama (passar session=db.session).
    - Não faz commit aqui.
    Retorna o codigo_pneumark do produto acabado.
    """
    if quantidade is None or int(quantidade) <= 0:
        raise ProdutoAcabadoInvalido(
            "Quantidade inválida para entrada de produto acabado."
        )

    sess = session or db.session
    codigo_conjunto = _resolver_conjunto_por_modelo(modelo)

    # trava a linha do conjunto
    fg: Optional[Peca] = sess.execute(
        select(Peca)
        .where(
            Peca.codigo_pneumark == codigo_conjunto,
            Peca.tipo == "conjunto",
        )
        .with_for_update()
    ).scalar_one_or_none()

    if not fg:
        raise ProdutoAcabadoInvalido(
            f"Conjunto '{codigo_conjunto}' (modelo {modelo}) não encontrado (tipo='conjunto')."
        )

    fg.estoque_atual = float(fg.estoque_atual or 0) + float(int(quantidade))
    sess.add(fg)

    # (Opcional) registrar movimentação
    if MovimentacaoEstoque is not None:
        try:
            mov = MovimentacaoEstoque(
                tipo_mov="entrada",
                codigo_peca=codigo_conjunto,
                quantidade=float(int(quantidade)),
                referencia=referencia,
                usuario=usuario,
            )
            sess.add(mov)
        except Exception as e:
            logger.warning(
                f"Falha ao registrar movimentação de entrada (FG) para {codigo_conjunto}: {e}"
            )

    return codigo_conjunto


# ====================================================================
# [FIM BLOCO] registrar_conclusao_produto_acabado
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] estornar_conclusao_produto_acabado
# [RESPONSABILIDADE] Estornar conclusão de produto acabado (conjunto) no estoque com base no modelo
# ====================================================================
def estornar_conclusao_produto_acabado(
    modelo: str,
    quantidade: int,
    usuario: str,
    referencia: Optional[str] = None,
    session: Optional[Session] = None,
) -> str:
    """
    Faz ESTORNO (-quantidade) no estoque do CONJUNTO correspondente ao modelo.
    - Usa o mapeamento MODEL_TO_CONJUNTO.
    - Deve rodar DENTRO da mesma transação de quem chama (passar session=db.session).
    - Não faz commit aqui.
    Retorna o codigo_pneumark do produto acabado.
    """
    if quantidade is None or int(quantidade) <= 0:
        raise ProdutoAcabadoInvalido(
            "Quantidade inválida para estorno de produto acabado."
        )

    sess = session or db.session
    codigo_conjunto = _resolver_conjunto_por_modelo(modelo)

    fg: Optional[Peca] = sess.execute(
        select(Peca)
        .where(
            Peca.codigo_pneumark == codigo_conjunto,
            Peca.tipo == "conjunto",
        )
        .with_for_update()
    ).scalar_one_or_none()

    if not fg:
        raise ProdutoAcabadoInvalido(
            f"Conjunto '{codigo_conjunto}' (modelo {modelo}) não encontrado (tipo='conjunto')."
        )

    novo = float(fg.estoque_atual or 0) - float(int(quantidade))
    # Política: não deixar negativo. Se preferir, troque por raise ProdutoAcabadoInvalido(...)
    fg.estoque_atual = novo if novo >= 0 else 0.0
    sess.add(fg)

    # (Opcional) registrar movimentação
    if MovimentacaoEstoque is not None:
        try:
            mov = MovimentacaoEstoque(
                tipo_mov="estorno",
                codigo_peca=codigo_conjunto,
                quantidade=float(int(quantidade)),
                referencia=referencia,
                usuario=usuario,
            )
            sess.add(mov)
        except Exception as e:
            logger.warning(
                f"Falha ao registrar movimentação de estorno (FG) para {codigo_conjunto}: {e}"
            )

    return codigo_conjunto


# ====================================================================
# [FIM BLOCO] estornar_conclusao_produto_acabado
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# CLASSE: FaltaItem
# CLASSE: EstoqInsuficiente
# CLASSE: BomIndisponivel
# CLASSE: ProdutoAcabadoInvalido
# FUNÇÃO: _resolver_conjunto_por_modelo
# FUNÇÃO: _extrair_bom_capacidade
# FUNÇÃO: _extrair_codigo_conjunto
# FUNÇÃO: reservar_componentes_para_montagem
# FUNÇÃO: estornar_reserva_componentes
# FUNÇÃO: registrar_conclusao_produto_acabado
# FUNÇÃO: estornar_conclusao_produto_acabado
# ====================================================================
