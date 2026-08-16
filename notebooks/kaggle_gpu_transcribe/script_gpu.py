import os
import sys
import re
import json
import traceback
import subprocess
from pathlib import Path

# Suporte UTF-8 no stdout
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

def log(msg):
    print(msg)
    sys.stdout.flush()

try:
    log("[IBPM CR GPU] Instalando dependencias e ffmpeg na GPU do Kaggle...")
    subprocess.run(["apt-get", "update", "-qq"], check=False)
    subprocess.run(["apt-get", "install", "-y", "-qq", "ffmpeg"], check=False)
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "faster-whisper", "openai-whisper", "yt-dlp"], check=False)

    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    log(f"[IBPM CR GPU] Dispositivo GPU Ativo: {device.upper()}")

    model = None
    use_faster = True

    try:
        from faster_whisper import WhisperModel
        compute_type = "float16" if device == "cuda" else "int8"
        model = WhisperModel("large-v3", device=device, compute_type=compute_type)
        log("[IBPM CR GPU] Modelo Faster-Whisper Large-V3 carregado com sucesso!")
    except Exception as e:
        log(f"[IBPM CR GPU] Faster-Whisper indisponivel ({e}), usando OpenAI Whisper...")
        import whisper
        model = whisper.load_model("large-v3", device=device)
        use_faster = False
        log("[IBPM CR GPU] Modelo OpenAI Whisper Large-V3 carregado!")

    pendentes = ["001_2022-10-03_2hvx5L2DR2U_culto_santa_ceia_dia_02_10_2022.webm", "002_2022-10-07_RSrP_ZJMdC8_quinta_profetica_06_10.webm", "003_2022-10-10_c9apu4Aormc_culto_de_celebracao_09_10.webm", "004_2022-10-10_nAAxlOmtOT0_culto_de_celebracao_09_10.webm", "005_2022-10-21_zBK-vyB2OaE_quinta_profetica_20_10.webm", "006_2022-10-24_dTQ7deZHgH4_domingo_culto_de_celebrecao_23_10_2022.webm", "007_2022-10-28_Z4gqn40sAU4_domingo_culto_de_celebrecao_23_10_2022.webm", "008_2022-10-31_HeAglREKFqs_domingo_culto_de_celebrecao_30_10_2022.webm", "009_2022-11-04_5_d5YTdJf68_quinta_profetica_03_11_2022.webm", "010_2022-11-07_I0Esphj3dOI_domingo_santa_ceia_06_11_2022.webm", "011_2022-11-11_4NmrlDfIdOI_quinta_feira_profetica_10_11_2022.webm", "012_2022-11-14_qk9mMnOJKoI_domingo_culto_de_celebracao_13_11_2022.webm", "013_2022-11-18_eAc7BGYrTDk_quinta_profetica_17_11_2022.webm", "021_2022-12-16_OleOihvb8Wk_quinta_profetica_15_12_2022.webm", "022_2022-12-19_1-J9sdxbs04_culto_de_natal_18_12_2022.webm", "025_2023-01-06_83jIjuJMEk0_quinta_profetica_05_01_2022.webm", "028_2023-01-16_MaL7VfjzxnY_domingo_de_celebracao_15_01_2023.webm", "045_2023-03-31_rhVKtUpgx7w_quinta_profetica_30_03_2023.webm", "048_2023-04-07_QfVsYv4vzEA_quinta_profetica_da_redencao_06_04_2023.webm", "049_2023-04-09_NYr_VS-wKVA_domingo_culto_de_pascoa_09_04_2023.webm", "050_2023-04-10_g4W4CMMonu0_domingo_culto_de_pascoa_09_04_2023.webm", "052_2023-04-16_6Yk0YWObIVs_domingo_culto_de_pascoa_09_04_2023.webm", "053_2023-04-17_UxchF5M1TYg_domingo_de_celebracao_16_04_2023.webm", "058_2023-05-04_p5i1LCvzWvE_quinta_profetica_da_familia_04_05_2023.webm", "060_2023-05-07_2hhL-Tq2QiY_domingo_santa_ceia_07_05_2023.webm", "061_2023-05-08_yNWViCaW1_4_domingo_santa_ceia_07_05_2023.webm", "063_2023-05-15_2QtNB1kvXng_domingo_de_celebracao_dia_das_maes_14_05_2023.webm", "065_2023-05-19_hNeM9ic71R0_quinta_profetica_da_familia_18_05_2023.webm", "066_2023-05-22_7MuaOrZS53Y_domingo_celebracao_da_familia_21_05_2023.webm", "074_2023-07-09_ikGrfwaIiNU_quinto_dia_de_festividade_08_07.webm", "083_2023-08-07_uhJEt7ZBwXg_domingo_de_santa_ceia_06_08_23.webm", "085_2023-08-13_iBFl3QCw05A_culto_dia_dos_pais_13_08_23.webm", "086_2023-08-14_8QDErFAO1zc_culto_dia_dos_pais_13_08_23.webm", "087_2023-08-18_GDb6dIji6dg_quinta_feira_profetica_17_08_23.webm", "089_2023-08-25_NTEJejlgBi8_quinta_feira_profetica_24_08_23.webm", "090_2023-08-28_Yb_6_tZUmWI_domingo_de_celebracao_27_08_23.webm", "091_2023-09-01_UhtkIwXfbyk_quinta_profetica_31_08_23.webm", "097_2023-09-28__Lg0K3V_Q_A_quinta_profetica_sala_de_adoracao_28_09_23.webm", "102_2023-10-08_9n98OHAaBMc_terceiro_dia_de_re_festa_07_10_23.webm", "103_2023-10-09_mhtZQdR_mZs_quarto_dia_de_re_festa_08_10_23.webm", "108_2023-10-27_6gMIVFNV7m8_quinta_profetica_26_10_23.webm", "112_2023-11-10_38xbrmz7e50_quinta_profetica_09_11_23.webm", "115_2023-11-20_V4oH86ItMB8_domingo_de_celebracao_19_11_23.webm", "118_2023-12-01_kALO6xBj1Wk_quinta_profetica_30_11_23.webm", "123_2023-12-18_dYy1edFhw64_domingo_culto_de_natal_17_12_23.webm", "127_2024-01-01_sTKABTeqC7s_domingo_culto_da_virada_2024_31_12_23.webm", "128_2024-01-04_wMtdeSP_PBk_quinta_profetica_avivamento_e_intimidade_04_01_23.webm", "134_2024-01-22_LbAbxxpicec_domingo_de_celebracao_21_01_24.webm", "145_2024-02-24_RZeH_28hnQw_mini_vigilia_avivamento_e_intimidade_23_02_24.webm", "148_2024-03-04_NddisUFEUyI_domingo_santa_ceia_03_03_24.webm", "156_2024-04-01_eCrTjaH1j7I_domingo_de_celebracao_culto_de_pascoa_31_03_24.webm", "160_2024-04-12_kSxBUPt9Bvg_quinta_profetica_derrubando_as_mulharas_da_minha_vida_11_04_.webm", "164_2024-04-22_lcQfI-svRrA_domingo_de_celebracao_21_04_24.webm", "169_2024-05-08_TTsj3E_ebLI_culto_das_perolas_08_05_24.webm", "177_2024-05-30_ILzAvDqYI8Y_quinta_profetica_rompendo_limites_30_05_24.webm", "219_2024-10-07_s83xhQn4J_Q_domingo_de_santa_ceia_intimidade_06_10_24.webm", "227_2024-10-25_jfE4kRU7Mrc_quinta_profetica_teu_nome_e_cura_24_10_24.webm", "228_2024-10-28__6EppQWo75w_domingo_intimidade_27_10_24.webm", "229_2024-11-01_60Mn7cT3_nE_quinta_profetica_teu_nome_e_cura_31_10_24.webm", "239_2024-12-06_MK6w25_MKXw_quinta_profetica_da_familia_05_12_24.webm", "250_2025-01-03_o-CAO5cQPDQ_quinta_profetica_02_01_24.webm", "267_2025-03-03_UR11tNNKReM_domingo_de_celebracao_02_03_25.webm", "271_2025-03-13_ebNluIDhd90_quarta_profetica_chame_a_existencia_12_03_25.webm", "274_2025-03-20_fSG96TmMUk4_quarta_profetica_chame_a_existencia_19_03_25.webm", "279_2025-04-02_vIEQEx6KisA_primeiro_dia_conferencia_01_04_25.webm", "286_2025-04-21_qAMlfgJlqKI_culto_de_pascoa_20_04_25.webm", "290_2025-05-04_R8GgaByob8g_culto_de_santa_ceia_04_05_25.webm", "291_2025-05-05_NNVPhI5GTRA_culto_de_santa_ceia_04_05_25.webm", "301_2025-06-05_EVldzg5G1Os_quarta_profetica_atos_2_04_06_25.webm", "308_2025-07-03_Wg5qbNI_X-w_quarta_profetica_faz_de_novo_02_07_25.webm", "311_2025-07-09_YQPyEe19uAw_2_dia_festividade_maa_09_07_25.webm", "321_2025-07-28__BzhyHyPI5M_domingo_culto_do_amigo_27_07_25.webm", "323_2025-07-31_RtFG7tRir9I_quarta_profetica_faz_de_novo_30_07_25.webm", "327_2025-08-14_WBn23cPHELo_quarta_profetica_alegrai_vos_13_08_25.webm", "359_2025-11-13_pIyDow9iaZs_quarta_profetica_o_desafio_da_fe_12_11_25.webm", "370_2025-12-18__fom7Gyo6K0_quarta_profetica_profundidade_17_12_2025.webm", "371_2025-12-22__nI2Wifu2Ys_domingo_culto_de_natal_21_12_2025.webm", "375_2026-01-08_1KvwI8L7Um4_quarta_profetica_efata_07_01_26.webm", "379_2026-01-19__RAW9ShOUZE_domingo_de_celebracao_18_01_26.webm", "382_2026-01-29_yq3Vcl5zl1I_quarta_profetica_efata_28_01_26.webm", "383_2026-02-16_2siKjuEmpq0_domingo_de_celebracao_15_02_26.webm", "388_2026-03-05_gFeXeSlsEuE_quarta_profetica_esforca_te_04_03_26.webm", "396_2026-03-30_ECFjGc3049g_domingo_de_celebracao_29_03_26.webm", "399_2026-04-09_o2J7qjqheSo_quarta_profetica_a_cruz_08_04_26.webm", "400_2026-04-12_H8Q3dsXdLlI_domingo_de_celebracao_12_04_26.webm", "408_2026-04-30_19N573Txx0w_quarta_profetica_a_cruz_29_04_26.webm", "410_2026-05-04_ZbiTyRI2PHQ_domingo_santa_ceia_03_05_26.webm", "423_2026-06-01_CRDG6bnhBXA_domingo_de_celebracao_31_05_26.webm", "430_2026-06-22_eUlr3RNeNsE_domingo_de_celebracao_21_06_26.webm", "432_2026-07-02_Fp3jmgbz608_quarta_profetica_restituicao_01_07_26.webm", "435_2026-07-13_Izk3my2j3uQ_domingo_de_celebracao_12_07_26.webm", "436_2026-07-16_IaqUSzEzuxo_quarta_profetica_restituicao_15_07_26.webm", "437_2026-07-18_XqLuz7HRv_M_mini_vigilia_reformando_o_altar_17_07_26.webm", "441_2026-07-27_5t26RhzBOA0_domingo_sala_de_adoracao_26_07_26.webm", "442_2026-07-27_5NwIiPBdVfQ_domingo_sala_de_adoracao_26_07_26.webm", "445_2026-08-10_nDSulaP76b8_domingo_de_celebracao_09_08_26.webm"]
    log(f"[IBPM CR GPU] Total de cultos pendentes a transcrever: {len(pendentes)}")

    out_dir = Path(".")

    def extract_video_id(filename):
        match = re.search(r'_([a-zA-Z0-9_-]{11})_', filename)
        return match.group(1) if match else None

    def format_timestamp(seconds):
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"

    for idx, audio_name in enumerate(pendentes[:50], start=1):
        vid = extract_video_id(audio_name)
        stem = Path(audio_name).stem
        txt_out = out_dir / f"{stem}.txt"
        json_out = out_dir / f"{stem}.json"

        if not vid:
            continue

        log(f"[PROGRESS {idx}/{len(pendentes)}] Baixando audio do YouTube (ID: {vid})...")
        temp_audio = Path(f"/tmp/audio_{vid}.m4a")
        cmd_dl = [
            "yt-dlp",
            "-f", "ba[ext=m4a]/ba",
            "-o", str(temp_audio),
            f"https://www.youtube.com/watch?v={vid}"
        ]

        try:
            subprocess.run(cmd_dl, capture_output=True, text=True, check=True)
        except Exception as e:
            log(f"Erro ao baixar audio {vid}: {e}")
            continue

        log(f"[PROGRESS {idx}/{len(pendentes)}] Transcrevendo na GPU: {audio_name}...")
        try:
            txt_lines = []
            seg_list = []

            if use_faster:
                segments, info = model.transcribe(str(temp_audio), language="pt", beam_size=5, vad_filter=True)
                for seg in segments:
                    ts = format_timestamp(seg.start)
                    txt_lines.append(f"[{ts}] {seg.text.strip()}")
                    seg_list.append({"start": round(seg.start, 2), "end": round(seg.end, 2), "text": seg.text.strip()})
            else:
                res = model.transcribe(str(temp_audio), language="pt")
                for seg in res.get("segments", []):
                    st = seg.get("start", 0.0)
                    txt = seg.get("text", "").strip()
                    ts = format_timestamp(st)
                    txt_lines.append(f"[{ts}] {txt}")
                    seg_list.append({"start": round(st, 2), "end": round(seg.get("end", 0.0), 2), "text": txt})

            with open(txt_out, "w", encoding="utf-8") as f:
                f.write(f"TRANSCRIÇÃO WHISPER LARGE-V3 GPU\nARQUIVO: {audio_name}\n\n" + "\n".join(txt_lines))

            with open(json_out, "w", encoding="utf-8") as f:
                json.dump({"arquivo": audio_name, "video_id": vid, "segments": seg_list}, f, ensure_ascii=False, indent=2)

            temp_audio.unlink(missing_ok=True)
            log(f"[OK] Transcricao concluida -> {txt_out.name}")
        except Exception as err:
            log(f"Erro ao transcrever {audio_name}: {err}")

    log("[IBPM CR GPU] PROCESSO CONCLUIDO COM SUCESSO!")
except Exception as fatal_err:
    log(f"FATAL ERROR NO KERNEL GPU: {fatal_err}")
    traceback.print_exc()
