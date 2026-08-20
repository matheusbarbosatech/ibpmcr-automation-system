"""
Script de execução da Fase 2.5 (Triagem QA e Cortador de Áudio Bruto) para o Culto 449.
Lê os cortes minerados em Desktop/TESTE, extrai cada trecho diretamente do áudio bruto (.webm)
com FFmpeg em MP3 192k e salva os áudios e transcrições na pasta C:\\Users\\matheus\\Desktop\\TESTE\\cortes_audio_449\\.
"""

import sys
import os
import json
import csv
import re
import subprocess
from pathlib import Path

# Suporte a UTF-8 nativo no terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent

def executar_fase2_5_teste():
    pasta_teste = Path(r"C:\Users\matheus\Desktop\TESTE")
    pasta_cortes_audio = pasta_teste / "cortes_audio_449"
    pasta_cortes_audio.mkdir(parents=True, exist_ok=True)

    arq_json_insights = pasta_teste / "449_FlqCTPRsIT4_3_dia_de_festividade_mulheres_13_08_26.insights.json"
    arq_audio_bruto = pasta_teste / "449_FlqCTPRsIT4_3_dia_de_festividade_mulheres_13_08_26.webm"

    if not arq_json_insights.exists():
        print(f"❌ Erro: Arquivo de insights não encontrado: {arq_json_insights}")
        return

    if not arq_audio_bruto.exists():
        print(f"❌ Erro: Áudio bruto não encontrado: {arq_audio_bruto}")
        return

    print("📖 Carregando metadados dos cortes minerados (Fase 2)...")
    with open(arq_json_insights, "r", encoding="utf-8") as f:
        insights = json.load(f)

    shorts = insights.get("short_form_cuts", [])
    mids = insights.get("mid_form_cuts", [])
    todos_cortes = shorts + mids

    print(f"✂️ Encontrados {len(shorts)} Shorts e {len(mids)} Cortes Médios para fatiamento de áudio.")
    print(f"📁 Destino dos áudios fatiados: {pasta_cortes_audio}")

    relatorio_qa = []

    for idx, c in enumerate(todos_cortes, 1):
        cut_id = c.get("cut_id", f"corte_{idx:03d}")
        tipo = c.get("tipo", "Short")
        start_sec = c.get("start_sec", 0.0)
        end_sec = c.get("end_sec", 30.0)
        duration = round(end_sec - start_sec, 2)
        title = c.get("title_hook_a", "Corte Automático")
        text_snippet = c.get("text_snippet", "")
        start_anchor = c.get("start_anchor_7_words", "")
        end_anchor = c.get("end_anchor_7_words", "")
        
        prof = c.get("theological_analysis", {}).get("sermon_profile", "Exortação")
        bgm = c.get("audio_directives", {}).get("bgm_mood", "ambient")
        title_b = c.get("seo_metadata", {}).get("curiosity_title", title)

        nome_base = f"{cut_id}_{start_sec:.0f}s_{end_sec:.0f}s"
        out_mp3 = pasta_cortes_audio / f"{nome_base}.mp3"
        out_txt = pasta_cortes_audio / f"{nome_base}.txt"

        print(f"\n🎬 [{idx}/{len(todos_cortes)}] Fatiando {tipo}: '{cut_id}' ({start_sec:.1f}s -> {end_sec:.1f}s | {duration}s)")
        print(f"   📌 Título: {title}")

        # FFmpeg: Input seeking rápido + conversão MP3 192k
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_sec),
            "-to", str(end_sec),
            "-i", str(arq_audio_bruto),
            "-vn",
            "-acodec", "libmp3lame",
            "-ab", "192k",
            "-ar", "44100",
            "-loglevel", "error",
            str(out_mp3)
        ]

        try:
            subprocess.run(cmd, check=True)
            print(f"   ✅ Áudio cortado: {out_mp3.name} ({out_mp3.stat().st_size / 1024:.1f} KB)")
        except Exception as e:
            print(f"   ❌ Erro ao fatiar áudio via FFmpeg: {e}")
            continue

        # Escrever arquivo .txt de acompanhamento da transcrição para revisão manual
        conteudo_txt = (
            f"======================================================================\n"
            f"CORTE: {cut_id} | TIPO: {tipo} | DURAÇÃO: {duration}s\n"
            f"TIMESTAMPS: {start_sec:.2f}s até {end_sec:.2f}s\n"
            f"TÍTULO HOOK A: {title}\n"
            f"TÍTULO CURIOSIDADE: {title_b}\n"
            f"PERFIL TEOLÓGICO: {prof}\n"
            f"MOOD DA TRILHA (BGM): {bgm}\n"
            f"ÂNCORA INICIAL (7 PALAVRAS): {start_anchor}\n"
            f"ÂNCORA FINAL (7 PALAVRAS): {end_anchor}\n"
            f"======================================================================\n"
            f"TRANSCRIÇÃO LITERAL:\n\n"
            f"{text_snippet}\n"
            f"======================================================================\n"
        )
        with open(out_txt, "w", encoding="utf-8") as f_txt:
            f_txt.write(conteudo_txt)

        # Cálculo de WPM e Avaliação de QA
        wc = len(text_snippet.split())
        wpm = (wc / max(1.0, duration)) * 60.0
        qa_status = "APROVADO" if duration >= 25.0 and wpm <= 220.0 else "REVISAR"

        relatorio_qa.append({
            "cut_id": cut_id,
            "tipo": tipo,
            "start_sec": start_sec,
            "end_sec": end_sec,
            "duration": duration,
            "score_mineração": c.get("score", 0.0),
            "wpm_cadencia": round(wpm, 1),
            "veredito_qa": qa_status,
            "perfil_teológico": prof,
            "bgm_mood": bgm,
            "titulo": title,
            "arquivo_mp3": out_mp3.name
        })

    # Grava relatório final de Triagem QA Fase 2.5
    out_csv_qa = pasta_teste / "relatorio_fase2_5_triagem_449.csv"
    campos = ["cut_id", "tipo", "start_sec", "end_sec", "duration", "score_mineração", "wpm_cadencia", "veredito_qa", "perfil_teológico", "bgm_mood", "titulo", "arquivo_mp3"]
    with open(out_csv_qa, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(relatorio_qa)

    print("\n" + "="*75)
    print("🎉 FASE 2.5 (TRIAGEM E CORTE DE ÁUDIO BRUTO) FINALIZADA COM SUCESSO!")
    print(f"• Áudios MP3 Fatiados : {len(relatorio_qa)} arquivos em '{pasta_cortes_audio}'")
    print(f"• Relatório de QA CSV : {out_csv_qa}")
    print("="*75)

if __name__ == "__main__":
    executar_fase2_5_teste()
