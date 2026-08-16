"""
PIPELINE DE MINERAÇÃO DA FASE 3 (TEXTRANK + NMS + TIMESTAMPS EXATOS + PLAYLISTS)
IBPM CR AUTOMATION SYSTEM - Arquitetura Orientada a Objetos.
"""

import sys
import os
import json
import csv
import re
from pathlib import Path
from typing import Dict, List, Tuple

# Suporte a UTF-8 nativo no terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from src.core.logger import get_logger
from src.services.minerador_nlp import DualSermonMiner, PlaylistOrganizer
from src.services.cortador_ffmpeg import FastStreamCopyCutter


class PipelineMineracaoFase3:
    """
    Classe orquestradora da Fase 3: Mineração, Clusterização e Cortes de Mídia.
    """

    EXTENSOES_MIDIA = {".webm", ".mp4", ".mkv", ".mp3", ".wav", ".m4a"}

    def __init__(self):
        self.logger = get_logger("PipelineFase3")
        self.miner = DualSermonMiner()
        self.cutter = FastStreamCopyCutter()

        # Definição de caminhos ATUALIZADOS
        self.pasta_base = BASE_DIR / "data" / "audio_podcasts"
        
        self.dir_audios = self.pasta_base / "1.AUDIOS"
        self.dir_transcricoes = self.pasta_base / "2.TRANSCRICOES"
        self.dir_output = self.pasta_base / "3.CONTEUDOS"
        
        # Subpastas de Output
        self.dir_insights = self.dir_output / "insights_json"
        self.dir_cortes = self.dir_output / "cortes_finais"
        self.arq_csv = self.dir_output / "relatorio_cortes.csv"
        self.arq_playlists = self.dir_output / "playlists_tematicas.json"

        # Listas de estado em memória
        self.todos_cortes_csv: List[dict] = []
        self.cortes_medios_playlists: List[dict] = []

    def preparar_diretorios(self):
        """Garante que toda a estrutura de pastas de saída exista."""
        for diretorio in [self.dir_output, self.dir_insights, self.dir_cortes]:
            diretorio.mkdir(parents=True, exist_ok=True)

    def extrair_yt_id(self, nome_arquivo: str) -> str:
        """Extrai o ID do YouTube (11 caracteres) ignorando prefixos numéricos."""
        # Procura por IDs com 11 caracteres que comumente têm _ ou - 
        match = re.search(r"([a-zA-Z0-9_-]{11})", Path(nome_arquivo).stem)
        return match.group(1) if match else Path(nome_arquivo).stem

    def mapear_acervo(self) -> Tuple[Dict[str, Path], Dict[str, Path]]:
        """
        Mapeia os arquivos agrupando pelo ID do YouTube, resolvendo o problema
        de TXT e JSON terem prefixos diferentes (ex: 004_culto vs 005_culto).
        """
        mapa_transcricoes_bruto = {}
        mapa_midias_bruto = {}
        nomes_originais = {}

        # 1. Mapeamento de Mídias (1.AUDIOS)
        if self.dir_audios.exists():
            for arq in self.dir_audios.iterdir():
                if arq.is_file() and arq.suffix.lower() in self.EXTENSOES_MIDIA:
                    yt_id = self.extrair_yt_id(arq.name)
                    mapa_midias_bruto[yt_id] = arq
                    nomes_originais[yt_id] = arq.stem  # Guarda o nome bonito para usar depois

        # 2. Mapeamento de Transcrições (2.TRANSCRICOES)
        formatos_texto = {".txt", ".srt", ".vtt"}
        if self.dir_transcricoes.exists():
            for arq in self.dir_transcricoes.iterdir():
                if arq.is_file():
                    ext = arq.suffix.lower()
                    yt_id = self.extrair_yt_id(arq.name)
                    
                    if ext in formatos_texto:
                        if yt_id not in mapa_transcricoes_bruto:
                            mapa_transcricoes_bruto[yt_id] = arq
                    elif ext == ".json" and not arq.name.endswith(".insights.json"):
                        # O JSON sempre vence o TXT se tiver o mesmo ID de YouTube
                        mapa_transcricoes_bruto[yt_id] = arq

        # 3. Consolidação Final
        mapa_final_transcricoes = {}
        mapa_final_midias = {}
        
        for yt_id, arq_trans in mapa_transcricoes_bruto.items():
            # Usa o nome exato do áudio como ID do sermão, se não existir áudio, usa o do texto
            sermon_id = nomes_originais.get(yt_id, arq_trans.stem)
            mapa_final_transcricoes[sermon_id] = arq_trans
            
            if yt_id in mapa_midias_bruto:
                mapa_final_midias[sermon_id] = mapa_midias_bruto[yt_id]
                
        return mapa_final_transcricoes, mapa_final_midias

    def carregar_transcricao(self, caminho: Path) -> Tuple[str, List[dict]]:
        """Lê de forma segura JSON, TXT, SRT ou VTT com parser agressivo."""
        ext = caminho.suffix.lower()
        try:
            if ext == ".json":
                with open(caminho, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    
                texto = ""
                segmentos = []
                
                # 1. Se for um Dicionário (Formato padrão Whisper/Faster-Whisper)
                if isinstance(dados, dict):
                    # Caça o texto em qualquer chave comum
                    texto = dados.get("text", "") or dados.get("texto", "")
                    segmentos = dados.get("segments", []) or dados.get("segmentos", [])
                    
                    # Se não tem a chave global de texto, junta as palavras dos segmentos
                    if not texto and segmentos:
                        texto = " ".join(s.get("text", "") for s in segmentos if isinstance(s, dict))
                        
                # 2. Se for uma Lista (Algumas APIs retornam assim)
                elif isinstance(dados, list):
                    segmentos = dados
                    texto = " ".join(s.get("text", "") for s in dados if isinstance(s, dict))
                
                # Debug agressivo: se ainda estiver vazio, avisa o motivo exato
                if not texto.strip():
                    chaves_disp = list(dados.keys()) if isinstance(dados, dict) else "Lista"
                    print(f"   ❌ [DEBUG] Arquivo JSON lido, mas não achei o texto. Chaves encontradas: {chaves_disp}")
                    
                return texto.strip(), segmentos
                    
            elif ext in {".txt", ".srt", ".vtt"}:
                with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
                    conteudo = f.read()
                    
                if ext in {".srt", ".vtt"}:
                    # Limpa as marcações de tempo das legendas
                    conteudo = re.sub(r'^WEBVTT.*\n', '', conteudo, flags=re.MULTILINE)
                    conteudo = re.sub(r'^\d+$\n', '', conteudo, flags=re.MULTILINE)
                    conteudo = re.sub(r'^\d{2}:\d{2}:\d{2}.*-->.*\n', '', conteudo, flags=re.MULTILINE)
                    conteudo = re.sub(r'\n+', ' ', conteudo)
                    
                return conteudo.strip(), []
                
        except json.JSONDecodeError as e:
            print(f"   ❌ ERRO: O JSON {caminho.name} está corrompido ou mal formatado. Detalhe: {e}")
        except Exception as e:
            print(f"   ❌ ERRO DESCONHECIDO ao ler {caminho.name}: {e}")
            
        return "", []

    def executar(self):
        print("=" * 75)
        print("🚀 IBPM CR AUTOMATION - PIPELINE FASE 3 (ORIENTADO A OBJETOS)")
        print("=" * 75)

        self.preparar_diretorios()
        mapa_trans, mapa_midias = self.mapear_acervo()

        if not mapa_trans:
            print(f"⚠️ Nenhuma transcrição encontrada na pasta: \n{self.dir_transcricoes}\nEncerrando pipeline.")
            return

        print(f"📂 Transcrições únicas agrupadas : {len(mapa_trans)}")
        print(f"🎥 Mídias fonte validadas        : {len(mapa_midias)} em 1.AUDIOS\n")

        sucessos = 0

        for idx, (sermon_id, caminho_arq) in enumerate(mapa_trans.items(), 1):
            print(f"[{idx:03d}/{len(mapa_trans):03d}] Minerando: {sermon_id} ({caminho_arq.suffix.upper()})")
            
            # Validação de Mídia
            if sermon_id not in mapa_midias:
                print(f"   ⚠️ Mídia original não encontrada para '{sermon_id}'. O FFmpeg não poderá cortá-lo.")

            texto, segmentos = self.carregar_transcricao(caminho_arq)
            if not texto:
                print("   ❌ Texto vazio ou estrutura JSON não reconhecida. Pulando.")
                continue

            try:
                # Chama o minerador com os parâmetros padrão originais
                insights = self.miner.mine_sermon(transcript_text=texto, sermon_id=sermon_id)

                # Salvar JSON do Culto com Insights
                out_json = self.dir_insights / f"{sermon_id}.insights.json"
                with open(out_json, "w", encoding="utf-8") as f:
                    json.dump(insights, f, ensure_ascii=False, indent=2)

                # Catalogar Cortes
                shorts = insights.get("short_form_cuts", [])
                mids = insights.get("mid_form_cuts", [])
                
                for s in shorts:
                    s.update({"sermon_id": sermon_id, "tipo": "Short (9:16)"})
                    self.todos_cortes_csv.append(s)
                    
                for m in mids:
                    m.update({"sermon_id": sermon_id, "tipo": "Mid (16:9)"})
                    self.todos_cortes_csv.append(m)
                    self.cortes_medios_playlists.append(m)

                print(f"   ✓ Sucesso! Shorts extraídos: {len(shorts)} | Mids extraídos: {len(mids)}")
                sucessos += 1

            except Exception as e:
                print(f"   ❌ Erro de processamento no TextRank: {e}")

        self._gerar_artefatos(sucessos, len(mapa_trans))

    def _gerar_artefatos(self, sucessos: int, total: int):
        print("\n" + "-" * 75)
        
        # 1. Gerar Relatório CSV
        if self.todos_cortes_csv:
            campos = ["sermon_id", "tipo", "start_time", "end_time", "duracao", "score", "titulo", "texto_trecho"]
            with open(self.arq_csv, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=campos)
                writer.writeheader()
                for c in self.todos_cortes_csv:
                    writer.writerow({
                        "sermon_id": c.get("sermon_id", ""),
                        "tipo": c.get("tipo", ""),
                        "start_time": c.get("start", c.get("start_time", 0)),
                        "end_time": c.get("end", c.get("end_time", 0)),
                        "duracao": round(float(c.get("end", 0)) - float(c.get("start", 0)), 2),
                        "score": round(float(c.get("score", 0)), 3),
                        "titulo": c.get("titulo", c.get("title", "Corte Automático")),
                        "texto_trecho": c.get("text", c.get("texto", "")).replace("\n", " ")
                    })
            print(f"📊 Relatório CSV exportado com {len(self.todos_cortes_csv)} cortes mapeados.")

        # 2. Gerar Playlists Temáticas (Clustering)
        if self.cortes_medios_playlists:
            try:
                k = max(1, min(5, len(self.cortes_medios_playlists)))
                organizer = PlaylistOrganizer(num_playlists=k)
                playlists = organizer.build_playlists(self.cortes_medios_playlists)
                with open(self.arq_playlists, "w", encoding="utf-8") as f:
                    json.dump(playlists, f, ensure_ascii=False, indent=2)
                print("🎶 Playlists temáticas estruturadas via Clustering (KMeans).")
            except Exception as e:
                print(f"⚠️ Erro no agrupamento de playlists: {e}")

        # 3. Cortes Finais em Vídeo (FFmpeg)
        if self.arq_csv.exists() and sucessos > 0:
            print("🎬 Acionando FFmpeg FastStreamCopyCutter para fatiar as mídias...")
            try:
                # O FFmpeg procura a mídia fonte na pasta 1.AUDIOS
                self.cutter.cut_from_csv(
                    self.arq_csv,
                    self.dir_audios,
                    self.dir_cortes
                )
            except Exception as e:
                print(f"⚠️ Erro durante o fatiamento dos vídeos no FFmpeg: {e}")

        # Resumo Executivo
        print("\n" + "=" * 75)
        print("                       🎉 RESUMO DA FASE 3")
        print("=" * 75)
        print(f"  • Cultos Processados com Sucesso : {sucessos} de {total}")
        print(f"  • Total de Cortes Catalogados    : {len(self.todos_cortes_csv)}")
        print(f"  • Diretório de Entrega Final     : {self.dir_output.relative_to(BASE_DIR)}")
        print("=" * 75 + "\n")


if __name__ == "__main__":
    pipeline = PipelineMineracaoFase3()
    pipeline.executar()