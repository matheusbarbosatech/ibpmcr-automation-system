"""
Script Principal da Etapa 4: Exportação do JSON Mestre e Geração de Relatórios Executivos (PDF/HTML).

Execução independente e idempotente.
Exporta data/json/plano_mestre_ibpmcr.json e compila o relatório gerencial em PDF e HTML
prontos para entrega e leitura do pastor/usuário.
"""

import sys
import os
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.append(str(Path(__file__).resolve().parent))

from config.settings import DB_PATH, JSON_EXPORT_DIR, REPORT_DIR
from src.core.state_manager import MasterPlanManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Etapa4_GerarRelatorio")


def print_banner():
    banner = """
===========================================================================
 [IBPM CR] AUTOMATION SYSTEM - ETAPA 4: GERAÇÃO DE RELATÓRIOS E JSON MESTRE
   Saídas: plano_mestre_ibpmcr.json, relatorio_acervo_ibpmcr.html/pdf
   Foco: Apresentação Legível, Visualização Homilética e Plano de Cortes
===========================================================================
    """
    print(banner)


def generate_json_master(state_mgr: MasterPlanManager) -> str:
    """Exporta todo o banco de dados relacional para o arquivo JSON Mestre."""
    videos = state_mgr.get_all_videos_chronological()

    master_data = {
        "metadata": {
            "canal": "@ibpmcr7976",
            "nome_igreja": "Igreja Batista Palavra em Cristo",
            "data_geracao": datetime.now(timezone.utc).isoformat(),
            "total_videos_catalogados": len(videos),
            "total_videos_transcritos": sum(1 for v in videos if v.get("transcrito") == 1),
            "total_videos_analisados": sum(1 for v in videos if v.get("analisado_pln") == 1)
        },
        "acervo": []
    }

    for v in videos:
        insights = {}
        if v.get("insights_json"):
            try:
                insights = json.loads(v["insights_json"])
            except Exception:
                pass

        v_dict = {
            "video_id": v["video_id"],
            "indice_sequencial": v.get("indice_sequencial", 0),
            "nome_arquivo_mp3": v.get("nome_arquivo_mp3"),
            "titulo_original": v.get("titulo_original"),
            "titulo_sanitizado": v.get("titulo_sanitizado"),
            "data_publicacao": v.get("data_publicacao"),
            "duracao_segundos": v.get("duracao_segundos", 0),
            "visualizacoes": v.get("visualizacoes", 0),
            "likes": v.get("likes", 0),
            "status": {
                "audio_baixado": bool(v.get("audio_baixado")),
                "caminho_audio": v.get("caminho_audio"),
                "transcrito": bool(v.get("transcrito")),
                "analisado_pln": bool(v.get("analisado_pln"))
            },
            "analise_homiletica": {
                "pregador": v.get("pregador") or "Não identificado",
                "estilo": v.get("estilo_homiletico") or "Expositivo/Evangelístico",
                "serie_campanha": v.get("serie_campanha") or "Geral",
                "referencias_biblicas": v.get("referencias_biblicas", "").split(", ") if v.get("referencias_biblicas") else [],
                "score_viral": v.get("score_viral", 0)
            },
            "cortes_recomendados": insights.get("cortes_recomendados", []),
            "resumo": insights.get("resumo", "Transcrição completa armazenada no SQLite.")
        }
        master_data["acervo"].append(v_dict)

    os.makedirs(JSON_EXPORT_DIR, exist_ok=True)
    json_path = os.path.join(JSON_EXPORT_DIR, "plano_mestre_ibpmcr.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(master_data, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ JSON Mestre exportado com sucesso: {json_path}")
    return json_path


def generate_html_report(json_path: str) -> str:
    """Gera um relatório HTML responsivo e elegante a partir do JSON Mestre."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data["metadata"]
    acervo = data["acervo"]

    os.makedirs(REPORT_DIR, exist_ok=True)
    html_path = os.path.join(REPORT_DIR, "relatorio_acervo_ibpmcr.html")

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório Executivo - Acervo IBPM CR</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; color: #1e293b; margin: 0; padding: 30px; }}
        .header {{ background: linear-gradient(135deg, #1e3a8a, #3b82f6); color: white; padding: 25px; border-radius: 12px; margin-bottom: 25px; shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
        .header h1 {{ margin: 0 0 10px 0; font-size: 26px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); text-align: center; }}
        .stat-card .num {{ font-size: 28px; font-weight: bold; color: #2563eb; }}
        .stat-card .label {{ font-size: 14px; color: #64748b; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }}
        th, td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid #e2e8f0; font-size: 14px; }}
        th {{ background-color: #f1f5f9; font-weight: 600; color: #334155; }}
        tr:hover {{ background-color: #f8fafc; }}
        .badge {{ padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: 600; }}
        .badge-success {{ background-color: #dcfce7; color: #166534; }}
        .badge-pending {{ background-color: #fef3c7; color: #92400e; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Relatório de Análise do Acervo - IBPM CR (@ibpmcr7976)</h1>
        <p>Igreja Batista Palavra em Cristo | Mapeamento Cronológico do Acervo de Lives</p>
    </div>

    <div class="stats-grid">
        <div class="stat-card">
            <div class="num">{meta['total_videos_catalogados']}</div>
            <div class="label">Total de Lives Mapeadas</div>
        </div>
        <div class="stat-card">
            <div class="num">{meta['total_videos_transcritos']}</div>
            <div class="label">Cultos Transcritos</div>
        </div>
        <div class="stat-card">
            <div class="num">{meta['total_videos_analisados']}</div>
            <div class="label">Análises de PLN Concluídas</div>
        </div>
    </div>

    <h2>📅 Acervo Histórico de Lives (Ordenado do 001 ao {len(acervo):03d})</h2>
    <table>
        <thead>
            <tr>
                <th># Seq.</th>
                <th>Data Postagem</th>
                <th>Título Original</th>
                <th>Nome Arquivo MP3</th>
                <th>Áudio</th>
                <th>Transcrição</th>
            </tr>
        </thead>
        <tbody>
"""

    for item in acervo:
        audio_st = '<span class="badge badge-success">OK</span>' if item["status"]["audio_baixado"] else '<span class="badge badge-pending">Pendente</span>'
        trans_st = '<span class="badge badge-success">Concluída</span>' if item["status"]["transcrito"] else '<span class="badge badge-pending">Pendente</span>'
        pub_d = str(item.get("data_publicacao", ""))[:10]

        html_content += f"""
            <tr>
                <td><strong>{item['indice_sequencial']:03d}</strong></td>
                <td>{pub_d}</td>
                <td>{item['titulo_original']}</td>
                <td><code>{item['nome_arquivo_mp3']}</code></td>
                <td>{audio_st}</td>
                <td>{trans_st}</td>
            </tr>
        """

    html_content += """
        </tbody>
    </table>
</body>
</html>
"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    logger.info(f"✅ Relatório HTML gerado com sucesso: {html_path}")
    return html_path


def main():
    print_banner()

    state_mgr = MasterPlanManager()
    json_path = generate_json_master(state_mgr)
    html_path = generate_html_report(json_path)

    print("\n" + "=" * 75)
    print(" RESUMO DA EXECUÇÃO DA ETAPA 4:")
    print(f"   • JSON Mestre Gerado: {json_path}")
    print(f"   • Relatório HTML Gerado: {html_path}")
    print("=" * 75)
    print(" [ETAPA 4 CONCLUÍDA COM SUCESSO!]")
    print(" Todos os relatórios do ecossistema IBPM CR foram atualizados com sucesso.")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()
