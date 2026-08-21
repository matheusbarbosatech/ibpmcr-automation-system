# -*- coding: utf-8 -*-
"""
Script de Organização de Dataset por Ano com Suporte a Índice Cronológico
IBPM CR Automation System
"""

import os
import re
import json
import shutil
import sys
from pathlib import Path

# Suporte UTF-8 no terminal Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DATASET_DIR = Path(r"C:\Users\matheus\Desktop\dataset")


def extrair_ano(nome_arquivo: str, caminho_file: Path = None) -> str:
    """
    Extrai o ano a partir do nome do arquivo, conteúdo JSON ou faixa de índice numérico.
    """
    # 1. Procura ano explícito de 4 dígitos: 2022, 2023, 2024, 2025, 2026
    m4 = re.search(r'20(2[2-6])', nome_arquivo)
    if m4:
        return f"20{m4.group(1)}"

    # 2. Procura sufixo de ano _22, _23, _24, _25, _26 no final do nome
    m2 = re.search(r'_(2[2-6])(?:\.[a-zA-Z0-9]+)?$', nome_arquivo)
    if m2:
        return f"20{m2.group(1)}"

    # 3. Procura padrão de data _DD_MM_YY_ ou _DD_MM_YY
    m_data = re.search(r'_\d{1,2}_\d{1,2}_(2[2-6])', nome_arquivo)
    if m_data:
        return f"20{m_data.group(1)}"

    # 4. Inspeciona o JSON se disponível
    if caminho_file and caminho_file.suffix.lower() == ".json":
        try:
            with open(caminho_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                txt = json.dumps(data)
                m_json = re.search(r'20(2[2-6])', txt)
                if m_json:
                    return f"20{m_json.group(1)}"
        except Exception:
            pass

    # 5. Mapeamento por Faixa do Índice Numerado (001-457)
    m_idx = re.match(r'^(\d{3})_', nome_arquivo)
    if m_idx:
        num = int(m_idx.group(1))
        if num <= 27:
            return "2022"
        elif num <= 126:
            return "2023"
        elif num <= 247:
            return "2024"
        elif num <= 371:
            return "2025"
        else:
            return "2026"

    return "outros"


def organizar():
    if not DATASET_DIR.exists():
        print(f"❌ Diretório {DATASET_DIR} não encontrado!")
        return

    print("==========================================================================")
    print(f"📂 RE-ORGANIZANDO DATASET COMPLETO POR ANO EM: {DATASET_DIR}")
    print("==========================================================================\n")

    contadores = {}

    # Varre subpastas existentes incluindo 'outros' e redistribui
    anos_possiveis = ["2022", "2023", "2024", "2025", "2026", "outros"]

    for ano_pasta in anos_possiveis:
        pasta_ano = DATASET_DIR / ano_pasta
        if not pasta_ano.exists():
            continue

        for root, dirs, files in os.walk(pasta_ano):
            for file in files:
                caminho_origem = Path(root) / file
                rel_path = caminho_origem.relative_to(pasta_ano)
                sub_categoria = str(rel_path.parent).replace("\\", "/")

                ano_correto = extrair_ano(file, caminho_origem)

                if ano_correto != ano_pasta:
                    pasta_destino = DATASET_DIR / ano_correto / sub_categoria
                    pasta_destino.mkdir(parents=True, exist_ok=True)
                    caminho_destino = pasta_destino / file
                    shutil.move(str(caminho_origem), str(caminho_destino))

    # Limpar pastas vazias se houver
    for p in DATASET_DIR.glob("**/*"):
        if p.is_dir() and not any(p.iterdir()):
            try:
                p.rmdir()
            except Exception:
                pass

    # Contagem final de auditoria
    for ano_pasta in ["2022", "2023", "2024", "2025", "2026", "outros"]:
        pasta_ano = DATASET_DIR / ano_pasta
        if pasta_ano.exists():
            for sub in ["audios", "transcriptions/json", "transcriptions/txt"]:
                p_sub = pasta_ano / sub
                if p_sub.exists():
                    qtd = len([f for f in p_sub.glob("*") if f.is_file()])
                    if qtd > 0:
                        contadores[f"{ano_pasta}/{sub}"] = qtd

    print("\n==========================================================================")
    print("🎉 ORGANIZAÇÃO FINAL CONCLUÍDA COM SUCESSO!")
    print("==========================================================================")
    for k in sorted(contadores.keys()):
        print(f"   • {k:<32} : {contadores[k]} arquivos")
    print("==========================================================================\n")


if __name__ == "__main__":
    organizar()
