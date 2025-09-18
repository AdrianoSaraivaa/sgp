
from app import create_app, db
from app.models import Peca, FornecedorPeca
import pandas as pd

# Caminho do arquivo Excel
excel_path = "X:/NOVA-ESTRUTURA/PNEUMARK/DIRETORIA/SARAIVA/SGP/PopularBancoDeDados.xlsx"

# Carrega os dados pulando a primeira linha (cabeçalho está na linha 2 da planilha)
df = pd.read_excel(excel_path, skiprows=1)

# Renomeia colunas relevantes
df = df.rename(columns={
    df.columns[0]: "codigo_pneumark",
    df.columns[1]: "descricao",
    df.columns[2]: "fornecedor",
    df.columns[13]: "estoque_minimo",
    df.columns[14]: "ponto_pedido",
    df.columns[15]: "estoque_maximo",
    df.columns[16]: "estoque_atual",
    df.columns[17]: "valor_unitario",
    df.columns[18]: "codigo_fornecedor_omie",
    df.columns[19]: "codigo_produto_omie"
})

app = create_app()

with app.app_context():
    for _, row in df.iterrows():
        if pd.isna(row["codigo_pneumark"]) or pd.isna(row["descricao"]):
            continue  # ignora linhas incompletas

        # Evita duplicidade
        existente = Peca.query.filter_by(codigo_pneumark=row["codigo_pneumark"]).first()
        if existente:
            print(f"Já existe: {row['codigo_pneumark']}")
            continue

        # Cria objeto Peca
        nova_peca = Peca(
            tipo="peca",
            descricao=row["descricao"],
            codigo_pneumark=row["codigo_pneumark"],
            codigo_omie=str(row["codigo_produto_omie"]) if not pd.isna(row["codigo_produto_omie"]) else None,
            estoque_minimo=int(row["estoque_minimo"]) if not pd.isna(row["estoque_minimo"]) else 0,
            ponto_pedido=int(row["ponto_pedido"]) if not pd.isna(row["ponto_pedido"]) else 0,
            estoque_maximo=int(row["estoque_maximo"]) if not pd.isna(row["estoque_maximo"]) else 0,
            estoque_atual=int(row["estoque_atual"]) if not pd.isna(row["estoque_atual"]) else 0,
            margem=5.0,  # margem padrão
            custo=float(row["valor_unitario"]) * 1.05 if not pd.isna(row["valor_unitario"]) else 0
        )
        db.session.add(nova_peca)
        db.session.flush()  # obtém o ID antes de salvar

        # Cria fornecedor vinculado
        if not pd.isna(row["fornecedor"]):
            fornecedor = FornecedorPeca(
                peca_id=nova_peca.id,
                fornecedor=row["fornecedor"],
                etapa="principal",
                preco=float(row["valor_unitario"]) if not pd.isna(row["valor_unitario"]) else 0
            )
            db.session.add(fornecedor)

    db.session.commit()
    print("Importação concluída com sucesso.")
