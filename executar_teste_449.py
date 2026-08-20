"""
Script de teste dedicado para o Culto 449 na pasta C:\\Users\\matheus\\Desktop\\TESTE.
Executa o Diretor de Arte Algorítmico da Fase 2 (DualSermonMiner v3) com extração
completa de metadados NLP, DSP, Tipografia, Áudio, Teologia e SEO.
"""

import sys
import json
import csv
from pathlib import Path

# Suporte a UTF-8 nativo no terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from src.services.minerador_nlp import DualSermonMiner

def executar_teste():
    pasta_teste = Path(r"C:\Users\matheus\Desktop\TESTE")
    
    arq_txt = pasta_teste / "449_FlqCTPRsIT4_3_dia_de_festividade_mulheres_13_08_26.txt"
    arq_json = pasta_teste / "449_FlqCTPRsIT4_3_dia_de_festividade_mulheres_13_08_26.json"
    arq_audio = pasta_teste / "449_FlqCTPRsIT4_3_dia_de_festividade_mulheres_13_08_26.webm"
    
    print(f"🔍 Lendo transcrição de: {arq_txt.name}")
    
    texto_transcricao = ""
    if arq_txt.exists():
        with open(arq_txt, "r", encoding="utf-8", errors="ignore") as f:
            texto_transcricao = f.read()
    elif arq_json.exists():
        with open(arq_json, "r", encoding="utf-8") as f:
            dados = json.load(f)
            texto_transcricao = dados.get("transcript", "") or dados.get("text", "")
            
    if not texto_transcricao:
        print("❌ Erro: Não foi possível carregar a transcrição do Culto 449.")
        return

    print(f"📊 Transcrição carregada: {len(texto_transcricao.split())} palavras.")
    print(f"🎙️ Áudio detectado: {arq_audio.name} ({arq_audio.stat().st_size / (1024*1024):.1f} MB)" if arq_audio.exists() else "⚠️ Áudio não encontrado")

    sermon_id = "449_FlqCTPRsIT4_3_dia_de_festividade_mulheres_13_08_26"
    miner = DualSermonMiner()

    print("🚀 Executando Mineração Semântica + Direção de Arte Algorítmica (v3)...")
    insights = miner.mine_sermon(
        transcript_text=texto_transcricao,
        sermon_id=sermon_id,
        audio_path=str(arq_audio) if arq_audio.exists() else None
    )

    # 1. Salvar JSON Mestre na pasta Desktop/TESTE
    out_insights_json = pasta_teste / f"{sermon_id}.insights.json"
    with open(out_insights_json, "w", encoding="utf-8") as f:
        json.dump(insights, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON Mestre de Insights salvo em: {out_insights_json}")

    # 2. Salvar Relatório CSV na pasta Desktop/TESTE
    out_csv = pasta_teste / "relatorio_cortes_449.csv"
    shorts = insights.get("short_form_cuts", [])
    mids = insights.get("mid_form_cuts", [])
    todos_cortes = shorts + mids

    campos = ["cut_id", "sermon_id", "tipo", "start_sec", "end_sec", "duration", "score", "title_hook_a", "sermon_profile", "bgm_mood"]
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        for c in todos_cortes:
            writer.writerow({
                "cut_id": c.get("cut_id"),
                "sermon_id": c.get("sermon_id"),
                "tipo": c.get("tipo"),
                "start_sec": c.get("start_sec"),
                "end_sec": c.get("end_sec"),
                "duration": c.get("duration"),
                "score": c.get("score"),
                "title_hook_a": c.get("title_hook_a"),
                "sermon_profile": c.get("theological_analysis", {}).get("sermon_profile", "-"),
                "bgm_mood": c.get("audio_directives", {}).get("bgm_mood", "-"),
            })
    print(f"✅ Relatório CSV salvo em: {out_csv}")

    print("\n" + "="*70)
    print(f"🎉 CULTO 449 MINERADO COM SUCESSO!")
    print(f"• Total de Shorts (9:16) : {len(shorts)}")
    print(f"• Total de Mids (16:9)   : {len(mids)}")
    print("="*70)

if __name__ == "__main__":
    executar_teste()
