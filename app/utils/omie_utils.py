"""
Utilitários para integração com OMIE ERP.
Implementa funções para requisições de compra e exportações.
"""

import os
import json
import logging
import requests
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
from io import BytesIO

from app import db
from app.models_sqla import Peca, Fornecedor, FornecedoresPorPeca, OmieRequisicao

logger = logging.getLogger(__name__)

# Configurações OMIE (via variáveis de ambiente)
OMIE_APP_KEY = os.environ.get("OMIE_APP_KEY", "")
OMIE_APP_SECRET = os.environ.get("OMIE_APP_SECRET", "")
OMIE_BASE_URL = os.environ.get("OMIE_BASE_URL", "https://app.omie.com.br/api/v1/")

def _get_omie_headers() -> Dict[str, str]:
    """Retorna headers padrão para requisições OMIE."""
    return {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

def _make_omie_request(endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Faz uma requisição para a API OMIE.
    
    Args:
        endpoint: Endpoint da API (ex: "produtos/requisicao/")
        data: Dados da requisição
        
    Returns:
        Resposta da API OMIE
        
    Raises:
        Exception: Se a requisição falhar
    """
    if not OMIE_APP_KEY or not OMIE_APP_SECRET:
        raise Exception("Credenciais OMIE não configuradas (OMIE_APP_KEY/OMIE_APP_SECRET)")
    
    # Adiciona credenciais aos dados
    data.update({
        "app_key": OMIE_APP_KEY,
        "app_secret": OMIE_APP_SECRET
    })
    
    url = f"{OMIE_BASE_URL}{endpoint}"
    
    try:
        response = requests.post(
            url,
            json=data,
            headers=_get_omie_headers(),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"[OMIE] Erro na requisição para {endpoint}: {e}")
        raise Exception(f"Falha na comunicação com OMIE: {e}")

def solicitar_requisicao_compra(peca: Peca, quantidade: int, fornecedor: Optional[str] = None) -> Dict[str, Any]:
    """
    Solicita uma requisição de compra no OMIE para uma peça específica.
    
    Args:
        peca: Objeto Peca que precisa ser comprada
        quantidade: Quantidade a ser solicitada
        fornecedor: Nome do fornecedor (opcional, será inferido se não fornecido)
        
    Returns:
        Dicionário com resultado da operação
    """
    try:
        # Se fornecedor não especificado, busca o primeiro fornecedor da peça
        if not fornecedor:
            fornecedor_obj = db.session.query(FornecedoresPorPeca).filter_by(peca_id=peca.id).first()
            if fornecedor_obj:
                fornecedor = fornecedor_obj.fornecedor
            else:
                fornecedor = "Fornecedor Padrão"
        
        # Cria registro na tabela local
        requisicao = OmieRequisicao(
            peca_id=peca.id,
            fornecedor=fornecedor,
            quantidade=quantidade,
            status="pendente",
            created_at=datetime.utcnow()
        )
        db.session.add(requisicao)
        db.session.flush()  # Para obter o ID
        
        # Prepara dados para OMIE
        omie_data = {
            "call": "IncluirRequisicaoCompra",
            "param": [{
                "cabecalho": {
                    "codigo_interno": f"REQ_{requisicao.id}",
                    "descricao": f"Requisição automática - {peca.descricao}",
                    "observacoes": f"Gerada automaticamente pelo sistema SGP - Peca ID: {peca.id}"
                },
                "itens": [{
                    "codigo_produto": peca.codigo_omie or peca.codigo_pneumark,
                    "descricao": peca.descricao,
                    "quantidade": quantidade,
                    "observacoes": f"Estoque atual: {peca.estoque_atual}, Ponto de pedido: {peca.ponto_pedido}"
                }],
                "fornecedor": {
                    "nome": fornecedor
                }
            }]
        }
        
        try:
            # Envia para OMIE
            response = _make_omie_request("produtos/requisicao/", omie_data)
            
            # Atualiza registro com sucesso
            requisicao.status = "enviado"
            requisicao.sent_at = datetime.utcnow()
            requisicao.cod_int = response.get("codigo_interno", f"REQ_{requisicao.id}")
            
            db.session.commit()
            
            logger.info(f"[OMIE] Requisição criada com sucesso para peça {peca.codigo_pneumark}")
            return {
                "success": True,
                "requisicao_id": requisicao.id,
                "omie_response": response
            }
            
        except Exception as e:
            # Atualiza registro com erro
            requisicao.status = "erro"
            requisicao.erro_msg = str(e)
            db.session.commit()
            
            logger.error(f"[OMIE] Falha ao enviar requisição para peça {peca.codigo_pneumark}: {e}")
            return {
                "success": False,
                "requisicao_id": requisicao.id,
                "error": str(e)
            }
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"[OMIE] Erro interno ao processar requisição: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def exportar_produtos_excel() -> bytes:
    """
    Exporta catálogo de produtos para Excel.
    
    Returns:
        Bytes do arquivo Excel
    """
    try:
        # Busca todas as peças
        pecas = db.session.query(Peca).all()
        
        # Converte para DataFrame
        data = []
        for peca in pecas:
            data.append({
                "ID": peca.id,
                "Tipo": peca.tipo,
                "Descrição": peca.descricao,
                "Código Pneumark": peca.codigo_pneumark,
                "Código OMIE": peca.codigo_omie,
                "Estoque Atual": peca.estoque_atual,
                "Estoque Mínimo": peca.estoque_minimo,
                "Ponto de Pedido": peca.ponto_pedido,
                "Estoque Máximo": peca.estoque_maximo,
                "Custo": peca.custo,
                "Margem": peca.margem
            })
        
        df = pd.DataFrame(data)
        
        # Gera Excel em memória
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Produtos', index=False)
        
        output.seek(0)
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"[OMIE] Erro ao exportar produtos: {e}")
        raise

def exportar_fornecedores_excel() -> bytes:
    """
    Exporta catálogo de fornecedores para Excel.
    
    Returns:
        Bytes do arquivo Excel
    """
    try:
        # Busca todos os fornecedores
        fornecedores = db.session.query(Fornecedor).all()
        
        # Converte para DataFrame
        data = []
        for fornecedor in fornecedores:
            data.append({
                "ID": fornecedor.id,
                "Nome Empresa": fornecedor.nome_empresa,
                "Nome Contato": fornecedor.nome_contato,
                "Telefone 1": fornecedor.telefone1,
                "Telefone 2": fornecedor.telefone2,
                "Email 1": fornecedor.email1,
                "Email 2": fornecedor.email2
            })
        
        df = pd.DataFrame(data)
        
        # Gera Excel em memória
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Fornecedores', index=False)
        
        output.seek(0)
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"[OMIE] Erro ao exportar fornecedores: {e}")
        raise

def exportar_produtos_fornecedores_excel() -> bytes:
    """
    Exporta relacionamento produtos x fornecedores para Excel.
    
    Returns:
        Bytes do arquivo Excel
    """
    try:
        # Busca relacionamentos com JOIN
        query = db.session.query(
            Peca.codigo_pneumark,
            Peca.descricao,
            FornecedoresPorPeca.fornecedor,
            FornecedoresPorPeca.etapa,
            FornecedoresPorPeca.preco
        ).join(
            FornecedoresPorPeca, Peca.id == FornecedoresPorPeca.peca_id
        ).all()
        
        # Converte para DataFrame
        data = []
        for row in query:
            data.append({
                "Código Peça": row.codigo_pneumark,
                "Descrição": row.descricao,
                "Fornecedor": row.fornecedor,
                "Etapa": row.etapa,
                "Preço": row.preco
            })
        
        df = pd.DataFrame(data)
        
        # Gera Excel em memória
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Produtos x Fornecedores', index=False)
        
        output.seek(0)
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"[OMIE] Erro ao exportar produtos x fornecedores: {e}")
        raise

def exportar_snapshot_ponto_pedido_excel() -> bytes:
    """
    Exporta snapshot do ponto de pedido para Excel.
    
    Returns:
        Bytes do arquivo Excel
    """
    try:
        # Busca todas as peças com informações de estoque
        pecas = db.session.query(Peca).filter(Peca.ponto_pedido.isnot(None)).all()
        
        # Converte para DataFrame
        data = []
        for peca in pecas:
            status = "OK"
            if peca.estoque_atual is not None and peca.ponto_pedido is not None:
                if peca.estoque_atual <= peca.ponto_pedido:
                    status = "ALERTA"
            
            data.append({
                "Código": peca.codigo_pneumark,
                "Descrição": peca.descricao,
                "Tipo": peca.tipo,
                "Estoque Atual": peca.estoque_atual,
                "Ponto de Pedido": peca.ponto_pedido,
                "Estoque Máximo": peca.estoque_maximo,
                "Status": status,
                "Data Snapshot": datetime.now().strftime("%d/%m/%Y %H:%M")
            })
        
        df = pd.DataFrame(data)
        
        # Gera Excel em memória
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Snapshot Ponto de Pedido', index=False)
        
        output.seek(0)
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"[OMIE] Erro ao exportar snapshot ponto de pedido: {e}")
        raise

def get_requisicoes_recentes(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Retorna as requisições OMIE mais recentes.
    
    Args:
        limit: Número máximo de requisições a retornar
        
    Returns:
        Lista de dicionários com dados das requisições
    """
    try:
        requisicoes = db.session.query(OmieRequisicao).order_by(
            OmieRequisicao.created_at.desc()
        ).limit(limit).all()
        
        result = []
        for req in requisicoes:
            # Busca dados da peça
            peca = db.session.query(Peca).get(req.peca_id)
            
            result.append({
                "id": req.id,
                "data_hora": req.created_at.strftime("%d/%m/%Y %H:%M"),
                "fornecedor": req.fornecedor or "",
                "codIntReqCompra": req.cod_int or "-",
                "itens": 1,  # Uma peça por requisição
                "qtde_total": req.quantidade,
                "status": req.status.capitalize(),
                "peca_codigo": peca.codigo_pneumark if peca else "",
                "peca_descricao": peca.descricao if peca else "",
                "erro_msg": req.erro_msg
            })
        
        return result
        
    except Exception as e:
        logger.error(f"[OMIE] Erro ao buscar requisições recentes: {e}")
        return []
