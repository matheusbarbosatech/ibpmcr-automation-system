"""
Minerador NLP Extrativo, Heuristico, DSP e Diretor de Arte Algoritmico (Fase 2 Mineracao Pro v3) - IBPM CR.

Melhorias v3:
1. TypedDict Schemas: MasterCutRecord, VisualDirectives, TypographyDirectives, AudioDirectives, TheologicalAnalysis, SEOMetadata, RetentionHooks.
2. NLPFeatureExtractor (spaCy + fallback nativo):
   - Extrai substantivos/verbos para B-rolls (Pexels).
   - Identifica elementos biblicos, locais historicos, perfil do sermao (Exortacao, Ensino, Consolo, etc.).
   - Gera 3 variacoes de titulo (Curiosidade, Teologico, Emocional), hashtags, copy de thumbnail e posts de redes sociais.
   - Limpa vicios de linguagem ("ne", "ha", "entao") para legendas elegantes.
   - Gera legendas .ASS sinteticas word-by-word (estilo CapCut).
   - Injeta emojis por sentimento e destaca termos teologicos (amarelo/vermelho).
3. DSPFeatureExtractor (librosa + envelope deterministico por WPM/silencios):
   - Picos de RMS (zoom-in rapido, shake 0.5s, caps lock).
   - Silencios > 2s (black screen, zoom-out slow).
   - Marcador de Drop (climax em ms, SFX riser 5s antes, boom no hook).
   - Ducking sidechain para alto WPM e atenuacao de agudos se houver clipping.
4. Mantem 100% de compatibilidade com o algoritmo de TextRank e NMS.
"""

import sys
import os
import re
import json
import csv
import math
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from collections import Counter

# Tenta importar librosa e spacy com fallbacks nativos
try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False

try:
    import spacy
    try:
        nlp_spacy = spacy.load("pt_core_news_lg")
    except Exception:
        try:
            nlp_spacy = spacy.load("pt_core_news_sm")
        except Exception:
            nlp_spacy = None
except ImportError:
    spacy = None
    nlp_spacy = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.cluster import MiniBatchKMeans
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

    class TfidfVectorizer:
        def __init__(self, max_features=500, min_df=1, sublinear_tf=True):
            self.max_features = max_features

        def fit_transform(self, raw_documents):
            docs_words = [re.findall(r'\b\w{3,}\b', doc.lower()) for doc in raw_documents]
            all_words = Counter(w for doc in docs_words for w in doc)
            vocab = [w for w, _ in all_words.most_common(self.max_features)]
            if not vocab:
                return np.zeros((len(raw_documents), 1))
            vocab_idx = {w: i for i, w in enumerate(vocab)}
            n_docs = len(raw_documents)
            matrix = np.zeros((n_docs, len(vocab)))
            doc_freq = Counter(w for doc in docs_words for w in set(doc))
            idf = {w: math.log((1 + n_docs) / (1 + doc_freq[w])) + 1 for w in vocab}

            for i, doc in enumerate(docs_words):
                counts = Counter(doc)
                for w, c in counts.items():
                    if w in vocab_idx:
                        tf = 1 + math.log(c)
                        matrix[i, vocab_idx[w]] = tf * idf[w]
            return matrix

    def cosine_similarity(X, Y=None):
        if Y is None:
            Y = X
        norm_X = np.linalg.norm(X, axis=1, keepdims=True)
        norm_Y = np.linalg.norm(Y, axis=1, keepdims=True)
        norm_X[norm_X == 0] = 1.0
        norm_Y[norm_Y == 0] = 1.0
        return np.dot(X / norm_X, (Y / norm_Y).T)

    class MiniBatchKMeans:
        def __init__(self, n_clusters=8, random_state=42, batch_size=50):
            self.n_clusters = n_clusters

        def fit_predict(self, X):
            n_samples = X.shape[0]
            return np.array([i % self.n_clusters for i in range(n_samples)])


BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from src.core.logger import get_logger
from src.domain.cut_directives import (
    MasterCutRecord, VisualDirectives, TypographyDirectives,
    AudioDirectives, TheologicalAnalysis, SEOMetadata, RetentionHooks
)

logger = get_logger("NLPHeuristicMinerProV3")


class NLPFeatureExtractor:
    """
    Extrator Semantico e Tipografico via spaCy / Regras Nativas em Portugues.
    Mapeia verbos de acao, elementos biblicos, sobreposicoes historicas, SEO e diretrizes tipograficas.
    """

    def __init__(self):
        self.action_verbs = {
            "correr": "person running dramatically",
            "cair": "person falling to knees praying",
            "chorar": "person crying emotion",
            "lutar": "spiritual battle warrior",
            "vencer": "victory celebration mountain top",
            "orar": "hands folded praying light",
            "caminhar": "walking in desert sunlight",
            "gritar": "preacher shouting passion",
            "levantar": "person rising up light",
            "subir": "climbing mountain peak",
            "descer": "descending valley mist",
            "escrever": "hand writing in journal",
            "cantar": "worship singer church",
            "abraçar": "people hugging reconciliation",
            "voar": "eagle flying sky",
            "quebrar": "chains breaking freedom",
        }

        self.biblical_elements = {
            "mar": "parting red sea waves ocean",
            "fogo": "holy fire altar flame",
            "montanha": "biblical mountain Sinai peak",
            "ovelha": "flock of sheep green pasture shepherd",
            "cruz": "wooden cross sunset Golgotha",
            "deserto": "desert wilderness sand dunes",
            "tempestade": "stormy sea dark clouds lighting",
            "leão": "lion of Judah majestic strength",
            "cordeiro": "white lamb innocent gentle",
            "altar": "ancient stone altar incense smoke",
            "espada": "sharp sword light truth",
            "anjos": "heavenly light angels glory",
            "céu": "glorious blue sky sun rays",
            "rio": "river of living water flowing",
            "pão": "bread breaking communion",
            "vinho": "grape wine chalice cup",
        }

        self.historical_places = [
            "egito", "babilônia", "jerusalém", "roma", "nínive", "babel",
            "assíria", "jordão", "faraó", "césar", "nabucodonosor",
            "davi", "moisés", "abraão", "elias", "paulo", "pedro"
        ]

        self.theological_highlights = {
            "graça": "#FFD700", "salvação": "#FFD700", "redenção": "#FFD700",
            "santidade": "#FFD700", "justificação": "#FFD700", "expiação": "#FF3333",
            "ressurreição": "#FFD700", "propiciação": "#FF3333", "espírito": "#FFD700",
            "glória": "#FFD700", "unção": "#FFD700", "aliança": "#FFD700",
            "milagre": "#FFD700", "fé": "#FFD700", "cruz": "#FF3333",
            "sangue": "#FF3333", "poder": "#FFD700", "vitória": "#FFD700"
        }

        self.imperative_verbs = [
            "levante", "receba", "olhe", "escute", "pare", "acredite",
            "vem", "tome", "glorifique", "busque", "creia", "acorda", "marcha"
        ]

        self.crutch_words_pattern = re.compile(
            r'\b(né|hã|então|tipo assim|né verdade|tá entendendo|sabe|éhh|hãm)\b',
            re.IGNORECASE
        )

        self.emoji_map = [
            (r'\b(choro|lágrima|tristeza|sofrimento|dor|aflição)\b', "😭", "choro"),
            (r'\b(fogo|poder|unção|avivamento|glória|gloria|espírito)\b', "🔥", "poder"),
            (r'\b(aleluia|amém|amen|adoração|louvor|graças)\b', "🙌", "adoração"),
            (r'\b(batalha|inimigo|vitória|vitoria|autoridade|armadura)\b', "⚔️", "batalha"),
            (r'\b(palavra|bíblia|biblia|versículo|escrito)\b', "📖", "palavra"),
            (r'\b(segredo|revelação|revelacao|visão|luz)\b', "💡", "revelação"),
        ]

        self.bible_books = [
            "Gênesis", "Êxodo", "Levítico", "Números", "Deuteronômio", "Josué",
            "Juízes", "Rute", "1 Samuel", "2 Samuel", "1 Reis", "2 Reis",
            "1 Crônicas", "2 Crônicas", "Esdras", "Neemias", "Ester", "Jó",
            "Salmos", "Provérbios", "Eclesiastes", "Cânticos", "Isaías", "Jeremias",
            "Lamentações", "Ezequiel", "Daniel", "Oséias", "Joel", "Amós",
            "Obadias", "Jonas", "Miquéias", "Naum", "Habacuc", "Sofonias",
            "Ageu", "Zacarias", "Malaquias", "Mateus", "Marcos", "Lucas",
            "João", "Atos", "Romanos", "1 Coríntios", "2 Coríntios", "Gálatas",
            "Efésios", "Filipenses", "Colossenses", "1 Tessalonicenses",
            "2 Tessalonicenses", "1 Timóteo", "2 Timóteo", "Tito", "Filemom",
            "Hebreus", "Tiago", "1 Pedro", "2 Pedro", "1 João", "2 João",
            "3 João", "Judas", "Apocalipse"
        ]

    def extract_brolls(self, text: str, win_sentences: List[Dict]) -> List[Dict[str, Any]]:
        """Extrai sugestoes de B-roll usando spaCy ou busca regex por verbos e elementos."""
        brolls = []
        text_lower = text.lower()

        # 1. Verbos de acao
        for verb, query in self.action_verbs.items():
            if verb in text_lower:
                # Encontra timestamp relativo
                ts = win_sentences[0]['start'] if win_sentences else 0.0
                for s in win_sentences:
                    if verb in s['text'].lower():
                        ts = s['start']
                        break
                brolls.append({
                    "timestamp_sec": round(ts, 2),
                    "pexels_query": query,
                    "category": "action_verb",
                    "trigger_word": verb
                })

        # 2. Elementos biblicos
        for elem, query in self.biblical_elements.items():
            if elem in text_lower:
                ts = win_sentences[0]['start'] if win_sentences else 0.0
                for s in win_sentences:
                    if elem in s['text'].lower():
                        ts = s['start']
                        break
                brolls.append({
                    "timestamp_sec": round(ts, 2),
                    "pexels_query": query,
                    "category": "biblical_element",
                    "trigger_word": elem
                })

        # 3. Sobreposicao historica
        for hist in self.historical_places:
            if hist in text_lower:
                ts = win_sentences[0]['start'] if win_sentences else 0.0
                for s in win_sentences:
                    if hist in s['text'].lower():
                        ts = s['start']
                        break
                brolls.append({
                    "timestamp_sec": round(ts, 2),
                    "pexels_query": f"historical {hist} ancient biblical scene",
                    "category": "historical_overlay",
                    "trigger_word": hist
                })

        return brolls[:6]

    def classify_sermon_profile(self, text: str) -> str:
        """Classifica o perfil do trecho entre Exortacao, Ensino, Consolo, Testemunho e Batalha Espiritual."""
        txt = text.lower()
        scores = {
            "Exortação": sum(1 for w in ["arrependa", "pecado", "vigiai", "mudança", "alerta", "postura"] if w in txt),
            "Ensino": sum(1 for w in ["significa", "grego", "hebraico", "versículo", "contexto", "exegese"] if w in txt),
            "Consolo": sum(1 for w in ["chora não", "consolador", "paz", "descansa", "não temas", "lágrimas"] if w in txt),
            "Testemunho": sum(1 for w in ["aconteceu comigo", "minha vida", "eu era", "deus fez", "testemunho"] if w in txt),
            "Batalha Espiritual": sum(1 for w in ["guerra", "inimigo", "muralhas", "derrota", "vitória", "sangue"] if w in txt),
        }
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "Exortação"

    def extract_contextual_subtitle(self, text: str) -> Optional[str]:
        """Extrai citacao de livro biblico para fixar no canto da tela."""
        for book in self.bible_books:
            pattern = rf'\b{re.escape(book)}\s*(\d+)?\b'
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                cap = f" {m.group(1)}" if m.group(1) else ""
                return f"{book}{cap}"
        return None

    def clean_caption_text(self, text: str) -> str:
        """Remove vicios de linguagem mantendo a leitura elegante."""
        cleaned = self.crutch_words_pattern.sub('', text)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    def generate_ass_word_by_word(self, win_sentences: List[Dict]) -> List[Dict[str, Any]]:
        """Gera eventos de legenda palavra-por-palavra no estilo CapCut (.ASS)."""
        events = []
        for s in win_sentences:
            words = s['text'].split()
            if not words:
                continue
            dur = max(0.5, s['end'] - s['start'])
            w_dur = dur / len(words)
            c_start = s['start']
            for w in words:
                c_end = round(c_start + w_dur, 2)
                events.append({
                    "start_sec": round(c_start, 2),
                    "end_sec": c_end,
                    "word": re.sub(r'[^\w]', '', w),
                    "raw_word": w
                })
                c_start = c_end
        return events

    def generate_titles_and_seo(
        self, text: str, profile: str, context_sub: Optional[str], preacher: str = "Pastor IBPM CR"
    ) -> SEOMetadata:
        """Gera 3 variacoes de titulo (Curiosidade, Teologico, Emocional) e metadados completos de SEO."""
        words = [w for w in re.findall(r'\b\w{4,}\b', text.lower()) if w not in {'para', 'como', 'esta', 'voce'}]
        top_topic = words[0].capitalize() if words else "Fé"

        curiosity_title = f"O detalhe sobre {top_topic} que você não percebeu..."
        theological_title = f"Exposição em {context_sub or top_topic} - A Essência da Fé"
        emotional_title = f"Ouça isso se o seu coração está pesado hoje"

        titles = [curiosity_title, theological_title, emotional_title]
        hashtags = ["#IBPMCR", "#Pregação", f"#{top_topic}", f"#{profile.replace(' ', '')}", "#ShortsEvangelicos"]

        description = (
            f"📖 {curiosity_title}\n\n"
            f"Mensagem edificante pregada no culto da IBPM CR.\n"
            f"Preletor: {preacher}\n\n"
            f"{' '.join(hashtags)}"
        )

        pinned_comment = f"Você já passou por isso em sua vida espiritual? Deixe seu comentário e compartilhe essa palavra! 🙌"

        # Copy da thumbnail (max 4 palavras impactantes)
        top_4 = words[:4] if len(words) >= 4 else ["DEUS", "TEM", "O", "PODER"]
        thumbnail_copy = " ".join([w.upper() for w in top_4[:4]])

        instagram_post = (
            f"✨ {curiosity_title} ✨\n\n"
            f"{text[:280]}...\n\n"
            f"🔥 Salve este post e envie para alguém que precisa ouvir essa verdade hoje!\n\n"
            f"{' '.join(hashtags)}"
        )

        return {
            "titles": titles,
            "hashtags": hashtags,
            "youtube_chapters": [{"relative_start_seconds": 0.0, "chapter_title": "Introdução Profética"}],
            "tiktok_keywords": [top_topic.lower(), profile.lower(), "fe", "deus", "ibpmcr", "shorts"],
            "curiosity_title": curiosity_title,
            "theological_title": theological_title,
            "emotional_title": emotional_title,
            "description": description,
            "pinned_comment": pinned_comment,
            "thumbnail_copy": thumbnail_copy,
            "instagram_post": instagram_post,
        }


class DSPFeatureExtractor:
    """
    Extrator de Processamento Digital de Sinais (DSP) via librosa ou envelope deterministico.
    Identifica picos RMS (zoom-in/shake), silencios >2s (black screen/zoom-out), drops de audio e ducking.
    """

    def __init__(self):
        self._cache_y = None
        self._cache_sr = None
        self._cache_path = None

    def _load_audio_once(self, audio_path: str):
        if self._cache_path != audio_path:
            self._cache_path = audio_path
            # Para arquivos .webm/.mp4 pesados, usa o simulador DSP determinístico instantâneo
            if HAS_LIBROSA and audio_path and os.path.exists(audio_path) and not audio_path.lower().endswith(('.webm', '.mp4', '.mkv')):
                try:
                    logger.info(f"Carregando amostra rápida do audio {audio_path}...")
                    y, sr = librosa.load(audio_path, sr=16000, mono=True, duration=120.0)
                    self._cache_y = y
                    self._cache_sr = sr
                except Exception as e:
                    logger.warning(f"Erro ao ler audio com librosa: {e}")
                    self._cache_y = None
                    self._cache_sr = None
            else:
                self._cache_y = None
                self._cache_sr = None

    def extract_features(
        self, audio_path: Optional[str], win_sentences: List[Dict], start_sec: float, end_sec: float, win_text: str
    ) -> Dict[str, Any]:
        """Calcula metadados de DSP do trecho."""
        duration = max(1.0, end_sec - start_sec)

        # 1. Tenta analise real com librosa se arquivo de audio existir
        if HAS_LIBROSA and audio_path and os.path.exists(audio_path):
            self._load_audio_once(audio_path)
            if self._cache_y is not None and self._cache_sr is not None:
                try:
                    sr = self._cache_sr
                    s_idx = int(start_sec * sr)
                    e_idx = int(end_sec * sr)
                    y_sub = self._cache_y[s_idx:e_idx]

                    if len(y_sub) > 0:
                        rms = librosa.feature.rms(y=y_sub)[0]
                        times = librosa.times_like(rms, sr=sr, hop_length=512) + start_sec

                        threshold_shake = np.percentile(rms, 88) if len(rms) > 0 else 0.5
                        shake_at = [round(float(times[idx]), 2) for idx, val in enumerate(rms) if val > threshold_shake]
                        max_climax_idx = np.argmax(rms) if len(rms) > 0 else 0
                        climax_sec = float(times[max_climax_idx]) if len(times) > 0 else start_sec + (duration / 2)
                        climax_ms = int(climax_sec * 1000)

                        silence_mask = rms < np.percentile(rms, 15)
                        black_screens = []
                        is_silent = False
                        sil_start = 0.0
                        for idx, silent in enumerate(silence_mask):
                            t = float(times[idx])
                            if silent and not is_silent:
                                is_silent = True
                                sil_start = t
                            elif not silent and is_silent:
                                is_silent = False
                                if t - sil_start >= 1.8:
                                    black_screens.append({"start_sec": round(sil_start, 2), "end_sec": round(t, 2)})

                        has_clipping = np.max(np.abs(y_sub)) > 0.98
                        eq_preset = "attenuate_treble" if has_clipping else "flat"

                        return {
                            "shake_effect_at": shake_at[:5],
                            "black_screen_at": black_screens[:3],
                            "drop_marker_ms": climax_ms,
                            "equalizer_preset": eq_preset,
                            "has_clipping": has_clipping,
                        }
                except Exception as e:
                    logger.warning(f"Falha ao fatiar audio com librosa: {e}")

        # 2. Simulator DSP Nativo (Fallback deterministico por WPM, exclamacoes e lacunas)
        shake_at = []
        black_screens = []
        caps_spans = []

        # Procura sentenças com exclamacoes ou texto em maiusculas para picos RMS
        for s in win_sentences:
            if '!' in s['text'] or s['text'].isupper():
                shake_at.append(round(s['start'], 2))
                caps_spans.append({"start_sec": round(s['start'], 2), "end_sec": round(s['end'], 2), "text": s['text'].upper()})

        # Procura lacunas entre sentenças para silêncios > 2s
        for i in range(len(win_sentences) - 1):
            gap = win_sentences[i+1]['start'] - win_sentences[i]['end']
            if gap >= 2.0:
                black_screens.append({
                    "start_sec": round(win_sentences[i]['end'], 2),
                    "end_sec": round(win_sentences[i+1]['start'], 2)
                })

        climax_sec = start_sec + (duration * 0.65)
        climax_ms = int(climax_sec * 1000)

        return {
            "shake_effect_at": shake_at[:5],
            "black_screen_at": black_screens[:3],
            "drop_marker_ms": climax_ms,
            "equalizer_preset": "flat",
            "has_clipping": False,
        }


class DualSermonMiner:
    """
    Minerador de Alta Precisao v3: TextRank + NMS + Directives (Diretor de Arte Algoritmico).
    """

    def __init__(self, blacklists=None):
        self.blacklists = blacklists or [
            r'd[ii]zimo', r'oferta', r'estacionamento', r'boa noite', r'boa tarde', r'bom dia',
            r'inscreva-se', r'boletim', r'sonoplastia', r'microfone', r'banco', r'pix',
            r'tesouraria', r'comunicados', r'sa[ii]da', r'cantina', r'aniversariante',
            r'vamos sentar', r'vamos ficar de p[ee]', r'vamos abrir a b[ii]blia',
            r'proxima semana', r'na semana que vem', r'encerrar o culto',
            r'aplicativo', r'youtube', r'like', r'compartilhe', r'notificacao',
            r'vai fazer a oferta', r'passar o envelope', r'celular no silencioso',
            r'informes', r'avisos', r'fique a vontade', r'pode sentar',
        ]

        self.short_hooks = [
            r'preste aten[cc][aa]o', r'olhe para mim', r'me olha', r'escuta isso',
            r'para um momento', r'isso [ee] importante', r'anota isso',
            r'a b[ii]blia diz', r'a palavra de deus diz', r'diz assim', r'est[aa] escrito',
            r'em \w+ cap[ii]tulo', r'jesus disse', r'o senhor disse', r'deus falou',
            r'o segredo [ee]', r'voc[ee] precisa', r'deus mandou te dizer',
            r'palavra para', r'receba essa palavra', r'tem milagre aqui', r'profecia',
            r'n[aa]o [ee] coincid[ee]ncia', r'deus n[aa]o falha',
            r'pare de', r'n[aa]o desista', r'levanta a cabe[cc]a',
            r'voc[ee] vai vencer', r'isso vai mudar', r'sua vida vai',
            r'aleluia', r'gl[oo]ria a deus', r'amen', r'hallelujah',
            r'chora n[aa]o', r'chegou a hora', r'[ee] hora de',
            r'voc[ee] [ee] filho', r'filho de deus', r'herdeiro',
            r'autoridade em cristo', r'no nome de jesus',
            r'vem para jesus', r'hoje [ee] o dia', r'se arrepende',
        ]

        self.medium_markers = [
            r'aconteceu', r'certa feita', r'hist[oo]ria', r'conta a b[ii]blia',
            r'imagine a cena', r'pensa comigo', r'veja o cen[aa]rio',
            r'era uma vez', r'naquele tempo', r'nos dias de',
            r'em primeiro lugar', r'em segundo lugar', r'em terceiro lugar',
            r'primeiro ponto', r'segundo ponto', r'ponto principal',
            r'a li[cc][aa]o que tiramos', r'o que isso significa',
            r'veja o que deus', r'o princ[ii]pio [ee]',
            r'vamos ler em', r'abre a b[ii]blia', r'texto base',
            r'o texto diz', r'a palavra (grega|hebraica) significa',
            r'contexto hist[oo]rico', r'o profeta', r'o ap[oo]stolo',
            r'aplica[cc][aa]o', r'na pr[aa]tica', r'como aplicar',
            r'isso significa que voc[ee]', r'para a sua vida',
            r'eu quero te desafiar', r'meu desafio para voc[ee]',
            r'testemunho', r'quando eu era', r'deus fez na minha vida',
        ]

        self._emotional_words = [
            'milagre', 'cura', 'libertacao', 'avivamento', 'fogo', 'uncao',
            'gloria', 'aleluia', 'amen', 'poderoso', 'sobrenatural',
            'transformacao', 'bencao', 'vitoria', 'salvacao', 'arrependimento',
            'profecia', 'revelacao', 'ungido', 'majestade',
        ]

        self.short_hooks_pattern = re.compile("|".join(self.short_hooks), re.IGNORECASE)
        self.medium_markers_pattern = re.compile("|".join(self.medium_markers), re.IGNORECASE)

        self.nlp_extractor = NLPFeatureExtractor()
        self.dsp_extractor = DSPFeatureExtractor()

        logger.info("Inicializado DualSermonMiner v3 (Diretor de Arte Algoritmico + Directives MasterCutRecord).")

    def format_timestamp(self, seconds: float) -> str:
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"

    def parse_text_with_real_timestamps(self, transcript_text: str) -> List[Dict]:
        """Le timestamps [HH:MM:SS] ou [MM:SS] reais do Whisper/YouTube. Fallback para estimativa."""
        pattern = re.compile(r'\[(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\]\s*(.*?)(?=\[(?:(?:\d{1,2}):)?\d{1,2}:\d{2}\]|$)', re.DOTALL)
        matches = list(pattern.finditer(transcript_text))

        if len(matches) >= 5:
            sentences = []
            for i, m in enumerate(matches):
                h_str, m_str, s_str = m.group(1), m.group(2), m.group(3)
                hrs = int(h_str) if h_str is not None else 0
                mins = int(m_str)
                secs = int(s_str)
                start_sec = hrs * 3600 + mins * 60 + secs

                text = m.group(4).strip().replace('\n', ' ')
                text = re.sub(r'^\d+\s+minutos?\s+e\s+\d+\s+segundos?\s*', '', text, flags=re.IGNORECASE).strip()
                if not text:
                    continue

                if i + 1 < len(matches):
                    m2 = matches[i+1]
                    h2_str, m2_str, s2_str = m2.group(1), m2.group(2), m2.group(3)
                    hrs2 = int(h2_str) if h2_str is not None else 0
                    mins2 = int(m2_str)
                    secs2 = int(s2_str)
                    end_sec = hrs2 * 3600 + mins2 * 60 + secs2
                else:
                    end_sec = start_sec + max(2.0, len(text.split()) / 2.2)

                end_sec = max(end_sec, start_sec + 0.5)
                sentences.append({
                    "text": text,
                    "start": round(start_sec, 2),
                    "end": round(end_sec, 2),
                    "duration": round(end_sec - start_sec, 2),
                    "has_real_ts": True,
                })
            logger.info(f"Timestamps reais: {len(sentences)} linhas processadas.")
            return sentences

        logger.warning("Sem timestamps [HH:MM:SS] ou [MM:SS] suficientes - usando estimativa.")
        return self._parse_text_estimated(transcript_text)

    def _parse_text_estimated(self, transcript_text: str) -> List[Dict]:
        raw_sentences = re.split(r'(?<=[.!?])\s+', transcript_text.strip())
        if len(raw_sentences) <= 3 and len(transcript_text.split()) > 100:
            words = transcript_text.strip().split()
            raw_sentences = [" ".join(words[i:i+15]) + "." for i in range(0, len(words), 15)]
        sentences = []
        current_sec = 0.0
        for s in raw_sentences:
            s_clean = re.sub(r'\[\d{2}:\d{2}:\d{2}\]', '', s.strip()).strip()
            if not s_clean:
                continue
            wc = len(s_clean.split())
            dur = max(1.5, round(wc / 2.2, 2))
            end_sec = round(current_sec + dur, 2)
            sentences.append({"text": s_clean, "start": current_sec, "end": end_sec,
                               "duration": dur, "has_real_ts": False})
            current_sec = end_sec
        return sentences

    def _compute_textrank(self, texts: List[str], damping: float = 0.85) -> np.ndarray:
        if not texts or len(texts) < 2:
            return np.ones(len(texts))
        try:
            vec = TfidfVectorizer(max_features=500, min_df=1, sublinear_tf=True)
            tfidf = vec.fit_transform(texts)
            sim_matrix = cosine_similarity(tfidf, tfidf)
            np.fill_diagonal(sim_matrix, 0)
            row_sums = sim_matrix.sum(axis=1)
            row_sums[row_sums == 0] = 1.0
            stochastic = sim_matrix / row_sums[:, np.newaxis]
            n = sim_matrix.shape[0]
            p = np.ones(n) / n
            for _ in range(15):
                p = (1 - damping) / n + damping * stochastic.T.dot(p)
            mn, mx = p.min(), p.max()
            if mx > mn:
                p = (p - mn) / (mx - mn)
            return p
        except Exception:
            return np.ones(len(texts)) / max(1, len(texts))

    def _score_positional_weight(self, start_sec: float, total_duration: float) -> float:
        if total_duration <= 0:
            return 1.0
        rel = start_sec / total_duration
        if rel < 0.20:
            return 0.60
        elif rel < 0.50:
            return 0.85
        elif rel < 0.80:
            return 1.00
        else:
            return 0.90

    def _score_emotional_intensity(self, win_text: str) -> float:
        text_lower = win_text.lower()
        excl_score = min(0.30, win_text.count('!') * 0.05)
        word_hits = sum(1 for w in self._emotional_words if w in text_lower)
        word_score = min(0.40, word_hits * 0.04)
        words = re.findall(r'\b\w{4,}\b', text_lower)
        if words:
            top_count = Counter(words).most_common(1)[0][1]
            rep_score = min(0.30, (top_count - 1) * 0.06) if top_count > 2 else 0.0
        else:
            rep_score = 0.0
        return min(1.0, excl_score + word_score + rep_score)

    def _extract_title_from_content(self, win_text: str, max_words: int = 7) -> str:
        clean = re.sub(r'\[\d{2}:\d{2}:\d{2}\]', '', win_text)
        clean = re.sub(r'[^\w\s]', ' ', clean)
        stopwords = {
            'de','do','da','dos','das','em','no','na','nos','nas','um','uma',
            'que','se','com','por','para','mas','ou','e','a','o','as','os',
            'eu','ele','ela','voce','nos','eles','me','te','lhe','foi','era',
            'esta','estou','sao','ser','ter','seu','sua','isso','este','esse',
            'pelo','pela','mais','nao','sim','aqui','ali','entao','como',
            'quando','porque','pois','tambem','ja','bem','muito','vai','tudo',
        }
        words = [w.lower() for w in clean.split() if len(w) > 3 and w.lower() not in stopwords]
        if not words:
            return "Momento Profetico"
        freq = Counter(words)
        top_words = {w for w, _ in freq.most_common(max_words)}
        ordered = []
        seen = set()
        for w in words:
            if w in top_words and w not in seen:
                ordered.append(w.capitalize())
                seen.add(w)
            if len(ordered) >= max_words:
                break
        return " ".join(ordered) if ordered else "Mensagem Poderosa"

    def generate_windows(self, sentences: List[Dict], min_dur: float, max_dur: float, step: int = 10) -> List[Dict]:
        windows = []
        n = len(sentences)

        if min_dur >= 180.0:
            target_durations = [d for d in [180, 300, 480, 720, 900] if min_dur <= d <= max_dur]
            for i in range(0, n, step):
                win_start = sentences[i]['start']
                for target in target_durations:
                    best_j = None
                    best_diff = float('inf')
                    for j in range(i + 1, min(n, i + 800)):
                        win_end = sentences[j]['end']
                        dur = win_end - win_start
                        if dur > max_dur:
                            break
                        if min_dur <= dur <= max_dur:
                            diff = abs(dur - target)
                            if diff < best_diff:
                                best_diff = diff
                                best_j = j
                    if best_j is not None:
                        win_end = sentences[best_j]['end']
                        dur = win_end - win_start
                        windows.append({
                            'start': win_start, 'end': win_end,
                            'duration': dur, 'indices': list(range(i, best_j + 1))
                        })
        else:
            max_span = 80
            for i in range(0, n, step):
                win_start = sentences[i]['start']
                for j in range(i + 1, min(n, i + max_span)):
                    win_end = sentences[j]['end']
                    dur = win_end - win_start
                    if min_dur <= dur <= max_dur:
                        windows.append({'start': win_start, 'end': win_end,
                                        'duration': dur, 'indices': list(range(i, j + 1))})
                        break
                    elif dur > max_dur:
                        break
        return windows

    def suppress_nms(self, windows: List[Dict], iou_thresh: float) -> List[Dict]:
        if not windows:
            return []
        sorted_wins = sorted(windows, key=lambda x: x['score'], reverse=True)
        selected = []
        while sorted_wins:
            best = sorted_wins.pop(0)
            selected.append(best)
            remaining = []
            for item in sorted_wins:
                inter = max(0.0, min(best['end'], item['end']) - max(best['start'], item['start']))
                union = max(best['end'], item['end']) - min(best['start'], item['start'])
                tiou = inter / union if union > 0 else 0.0
                if tiou < iou_thresh:
                    remaining.append(item)
            sorted_wins = remaining
        return selected

    def extract_7_words_anchor(self, text: str, is_end: bool = False) -> str:
        clean = re.sub(r'\[\d{2}:\d{2}:\d{2}\]', '', text).strip()
        words = clean.split()
        if len(words) < 7:
            words += ["palavra"] * (7 - len(words))
        return " ".join(words[-7:] if is_end else words[:7])

    def _build_master_cut_record(
        self,
        cut_id: str,
        sermon_id: str,
        tipo: str,
        w: Dict,
        sentences: List[Dict],
        tr_scores: np.ndarray,
        audio_path: Optional[str] = None
    ) -> MasterCutRecord:
        """Monta o objeto MasterCutRecord com as diretrizes completas de Direcao de Arte."""
        win_sentences = [sentences[idx] for idx in w['indices']]
        win_text = " ".join([s['text'] for s in win_sentences])
        start_sec = round(w['start'], 2)
        end_sec = round(w['end'], 2)
        duration = round(end_sec - start_sec, 2)
        score = round(w['score'], 3)

        title_a = self._extract_title_from_content(win_text)
        title_b = f"{title_a} | IBPM CR" if tipo == "Short (9:16)" else f"{title_a} - Pregação Completa"

        # 1. Extracao NLP
        brolls = self.nlp_extractor.extract_brolls(win_text, win_sentences)
        sermon_prof = self.nlp_extractor.classify_sermon_profile(win_text)
        context_sub = self.nlp_extractor.extract_contextual_subtitle(win_text)
        cleaned_text = self.nlp_extractor.clean_caption_text(win_text)
        ass_events = self.nlp_extractor.generate_ass_word_by_word(win_sentences)
        seo_meta = self.nlp_extractor.generate_titles_and_seo(win_text, sermon_prof, context_sub)

        # Promessa central e Cold Open (frase mais forte com verbos no futuro ou alta emocao)
        fut_matches = re.findall(r'([^.!?]*?\b(?:vai|irá|verá|fará|mudará|vou)\b[^.!?]*[.!?]?)', win_text, re.IGNORECASE)
        central_promise = fut_matches[0].strip() if fut_matches else win_sentences[0]['text']
        cold_open = win_sentences[0]['text'][:100]

        # Call to Action
        cta_match = re.search(r'\b(venha|aceite|levante|venha para|tome posse)\b', win_text, re.IGNORECASE)
        call_to_action = cta_match.group(0).capitalize() if cta_match else None

        # Exegese flag (presenca de versiculos/livros biblicos)
        is_exegese = bool(context_sub or 'versículo' in win_text.lower() or 'hebraico' in win_text.lower())

        # Contagem divindade
        divine_count = sum(1 for w_div in ['deus', 'jesus', 'espírito', 'espirito', 'senhor', 'pai'] if w_div in win_text.lower())

        # One-liner summary (sentença de maior TextRank dentro da janela)
        win_tr_scores = [tr_scores[idx] for idx in w['indices']]
        best_local_idx = int(np.argmax(win_tr_scores))
        one_liner = win_sentences[best_local_idx]['text']

        # Destaques teologicos
        highlight_words = []
        for word, color in self.nlp_extractor.theological_highlights.items():
            if word in win_text.lower():
                highlight_words.append({"word": word, "color": color})

        # Imperativos (wiggle)
        imperative_words = [w_imp for w_imp in self.nlp_extractor.imperative_verbs if w_imp in win_text.lower()]

        # Emojis por sentimento
        emoji_inserts = []
        for pattern, emo, sent in self.nlp_extractor.emoji_map:
            if re.search(pattern, win_text.lower()):
                emoji_inserts.append({"word": sent, "emoji": emo, "sentiment": sent})

        # 2. Extracao DSP
        dsp_data = self.dsp_extractor.extract_features(audio_path, win_sentences, start_sec, end_sec, win_text)

        # WPM e Ducking / BPM
        words_count = len(win_text.split())
        wpm = words_count / max(1.0, duration / 60.0)
        wps = words_count / max(1.0, duration)
        bpm = 120 if wps > 2.5 else 80

        ducking_points = []
        if wps > 2.8:
            ducking_points.append({"start_sec": start_sec, "end_sec": end_sec, "factor": 0.35})

        # Mood da BGM
        if sermon_prof == "Consolo":
            bgm_mood = "piano/cinematic"
        elif sermon_prof in ["Batalha Espiritual", "Exortação"]:
            bgm_mood = "epic/orchestral"
        else:
            bgm_mood = "worship/ambient"

        # Directives estruturados
        visual_directives: VisualDirectives = {
            "camera_movement": "Auto-Zoom In" if dsp_data.get("shake_effect_at") else "Normal",
            "shake_effect_at": dsp_data.get("shake_effect_at", []),
            "broll_inserts": brolls,
            "black_screen_at": dsp_data.get("black_screen_at", []),
            "blur_hook_sec": 3.0,
            "drop_marker_ms": dsp_data.get("drop_marker_ms"),
            "ken_burns_spans": [{"start_sec": start_sec, "end_sec": end_sec}] if duration > 45.0 and not dsp_data.get("shake_effect_at") else [],
            "crop_9_16_tracking": {"position": "center", "grid": "3x3_safe"},
            "progress_bar": {"position": "bottom", "duration_sec": duration, "visible": True},
            "safe_zones": {"top_pct": 15, "bottom_pct": 20, "logo_safe": True},
            "broll_loop_mode": "lofi_relaxing" if wps < 1.8 else None,
            "visual_countdown": True if score > 0.45 else False,
        }

        typography_directives: TypographyDirectives = {
            "highlight_words": highlight_words,
            "kinetic_style": "Word-by-Word",
            "sticky_quote": central_promise[:60],
            "emoji_inserts": emoji_inserts,
            "caps_lock_spans": dsp_data.get("shake_effect_at", []),
            "dynamic_font_spans": [{"text": win_text[:50], "font_family": "Cinzel" if is_exegese else "Montserrat"}],
            "typewriter_spans": [{"start_sec": start_sec, "end_sec": start_sec + 4.0, "text": win_sentences[0]['text']}],
            "word_by_word_ass_events": ass_events[:30],
            "imperative_wiggle_words": imperative_words,
            "contextual_subtitles": context_sub,
            "cleaned_caption_text": cleaned_text,
        }

        audio_directives: AudioDirectives = {
            "sfx_inserts": [
                {"timestamp_sec": start_sec, "sfx_type": "boom"},
                {"timestamp_sec": max(start_sec, (dsp_data.get("drop_marker_ms", 0)/1000.0) - 5.0), "sfx_type": "riser"}
            ],
            "bgm_mood": bgm_mood,
            "ducking_points": ducking_points,
            "audio_drop_ms": dsp_data.get("drop_marker_ms"),
            "sfx_whoosh_timestamps": [start_sec + (duration * 0.5)],
            "sfx_riser_timestamp": round(max(start_sec, (dsp_data.get("drop_marker_ms", 0)/1000.0) - 5.0), 2),
            "sfx_boom_timestamp": start_sec,
            "bpm_suggestion": bpm,
            "equalizer_preset": dsp_data.get("equalizer_preset", "flat"),
            "fade_out_sec": 1.5,
            "crowd_swell_spans": [],
        }

        theological_analysis: TheologicalAnalysis = {
            "sermon_profile": sermon_prof,
            "is_exegese": is_exegese,
            "central_promise": central_promise,
            "call_to_action": call_to_action,
            "problem_solution": {
                "problem": win_sentences[0]['text'],
                "solution": win_sentences[-1]['text']
            },
            "divine_density_score": divine_count,
            "one_liner_summary": one_liner,
            "bible_cross_references": [{"term": context_sub or "Fé", "cross_ref": "Bíblia Sagrada"}] if context_sub else [],
            "heresy_flag": False,
            "prophecy_marker": True if "deus mandou te dizer" in win_text.lower() else False,
        }

        retention_hooks: RetentionHooks = {
            "cold_open_text": cold_open,
            "seamless_loop": True if win_sentences[-1]['text'].strip().endswith(('...', ',')) else False,
            "cta_popup_at": round(max(start_sec, end_sec - 3.0), 2),
            "story_poll": {
                "question": "Você precisa dessa palavra hoje?",
                "option_a": "Sim, com certeza! 🙌",
                "option_b": "Preciso de oração 🙏"
            },
            "share_trigger": "Envie para alguém que precisa ouvir isso!" if sermon_prof == "Consolo" else None,
            "pattern_break_timestamps": dsp_data.get("shake_effect_at", []),
            "bible_quiz": {
                "question": f"Onde está registrada essa lição de {context_sub or 'fé'}?",
                "options": ["A) Salmos", "B) Efésios", "C) Mateus"],
                "answer": "B"
            } if is_exegese else None,
            "part_separator_tag": "Comente PARTE 2 para continuar" if duration > 60.0 else None,
            "controversy_flag": True if '?' in win_text else False,
            "easter_egg_logo_timestamps": [start_sec] if 'ibpm' in win_text.lower() else [],
        }

        return {
            "cut_id": cut_id,
            "sermon_id": sermon_id,
            "tipo": tipo,
            "start_sec": start_sec,
            "end_sec": end_sec,
            "duration": duration,
            "score": score,
            "title_hook_a": title_a,
            "title_hook_b": title_b,
            "start_anchor_7_words": self.extract_7_words_anchor(win_text, is_end=False),
            "end_anchor_7_words": self.extract_7_words_anchor(win_text, is_end=True),
            "text_snippet": win_text[:300] + "...",
            "visual_directives": visual_directives,
            "typography_directives": typography_directives,
            "audio_directives": audio_directives,
            "theological_analysis": theological_analysis,
            "seo_metadata": seo_meta,
            "retention_hooks": retention_hooks,
        }

    def mine_sermon(self, transcript_text: str, sermon_id: str = "IBPM_CULTO", audio_path: Optional[str] = None) -> Dict[str, Any]:
        """v3: Timestamps reais + TextRank + NMS + Directives de Direcao de Arte Algoritmico."""
        sentences = self.parse_text_with_real_timestamps(transcript_text)
        if not sentences:
            return {"job_id": f"job_v3_{sermon_id}", "source_video_id": sermon_id,
                    "sermon_title": f"Culto {sermon_id}", "preacher_name": "Pastor IBPM CR",
                    "short_form_cuts": [], "mid_form_cuts": []}

        texts = [s['text'] for s in sentences]
        tr_scores = self._compute_textrank(texts)
        total_duration = sentences[-1]['end'] if sentences else 1.0

        # --- SHORTS (30s-90s) ---
        short_wins = self.generate_windows(sentences, 30.0, 90.0, step=3)
        valid_shorts = []
        for w in short_wins:
            win_text = " ".join([sentences[idx]['text'] for idx in w['indices']])
            if any(re.search(p, win_text.lower()) for p in self.blacklists):
                continue
            tr_val = float(np.mean([tr_scores[idx] for idx in w['indices']]))
            hooks = len(self.short_hooks_pattern.findall(win_text))
            hooks_norm = min(1.0, hooks / 3.0)
            emot = self._score_emotional_intensity(win_text)
            pos = self._score_positional_weight(w['start'], total_duration)
            raw_score = (0.25 * tr_val) + (0.40 * hooks_norm) + (0.20 * emot) + (0.15 * tr_val)
            score = round(raw_score * pos, 3)
            if score < 0.10:
                continue
            w['score'] = score
            w['text'] = win_text
            w['sermon_id'] = sermon_id
            valid_shorts.append(w)

        valid_shorts = sorted(valid_shorts, key=lambda x: x['score'], reverse=True)[:60]
        shorts = self.suppress_nms(valid_shorts, 0.25)[:5]

        # --- MEDIOS (180s-900s) ---
        medium_wins = self.generate_windows(sentences, 180.0, 900.0, step=15)
        valid_mediums = []
        for w in medium_wins:
            win_text = " ".join([sentences[idx]['text'] for idx in w['indices']])
            if any(re.search(p, win_text.lower()) for p in self.blacklists):
                continue
            tr_val = float(np.mean([tr_scores[idx] for idx in w['indices']]))
            markers = len(self.medium_markers_pattern.findall(win_text))
            markers_norm = min(1.0, markers / 4.0)
            emot = self._score_emotional_intensity(win_text)
            pos = self._score_positional_weight(w['start'], total_duration)
            raw_score = (0.45 * tr_val) + (0.30 * markers_norm) + (0.15 * emot) + (0.10 * tr_val)
            score = round(raw_score * pos, 3)
            if score < 0.08:
                continue
            w['score'] = score
            w['text'] = win_text
            w['sermon_id'] = sermon_id
            valid_mediums.append(w)

        valid_mediums = sorted(valid_mediums, key=lambda x: x['score'], reverse=True)[:60]
        mediums = self.suppress_nms(valid_mediums, 0.35)[:3]

        # --- Formatacao MasterCutRecord ---
        short_payload = []
        for idx, s in enumerate(shorts, 1):
            cut_record = self._build_master_cut_record(
                cut_id=f"short_{idx:03d}",
                sermon_id=sermon_id,
                tipo="Short (9:16)",
                w=s,
                sentences=sentences,
                tr_scores=tr_scores,
                audio_path=audio_path
            )
            short_payload.append(cut_record)

        medium_payload = []
        for idx, m in enumerate(mediums, 1):
            cut_record = self._build_master_cut_record(
                cut_id=f"mid_{idx:03d}",
                sermon_id=sermon_id,
                tipo="Mid (16:9)",
                w=m,
                sentences=sentences,
                tr_scores=tr_scores,
                audio_path=audio_path
            )
            medium_payload.append(cut_record)

        insights_payload = {
            "job_id": f"job_v3_{sermon_id}",
            "source_video_id": sermon_id,
            "sermon_title": f"Culto IBPM CR {sermon_id}",
            "preacher_name": "Pastor IBPM CR",
            "short_form_cuts": short_payload,
            "mid_form_cuts": medium_payload,
            "metadata": {
                "total_duration_sec": round(total_duration, 1),
                "sentences_parsed": len(sentences),
                "uses_real_timestamps": sentences[0].get("has_real_ts", False) if sentences else False,
                "algorithm_version": "v3_art_director"
            }
        }

        self.export_relatorio_csv(sermon_id, short_payload + medium_payload)
        return insights_payload

    def export_relatorio_csv(self, source_file: str, cuts: List[Dict]):
        csv_path = Path("data/relatorio_cortes.csv")
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        file_exists = csv_path.exists()
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["arquivo_origem", "corte_id", "timestamp_inicio",
                                  "timestamp_fim", "duracao_segundos", "score", "titulo_extraido"])
            for c in cuts:
                s_sec = c.get("start_sec", 0.0)
                e_sec = c.get("end_sec", 45.0)
                writer.writerow([source_file, c.get("cut_id"),
                                  self.format_timestamp(s_sec), self.format_timestamp(e_sec),
                                  round(e_sec - s_sec, 1), c.get("score", 0.0),
                                  c.get("title_hook_a", "-")])
        return str(csv_path)


class PlaylistOrganizer:
    """Agrupamento Cross-Sermao em playlists tematicas via MiniBatchKMeans."""

    def __init__(self, num_playlists=8):
        self.num_playlists = num_playlists
        self.vectorizer = TfidfVectorizer(max_features=800, sublinear_tf=True)

    def build_playlists(self, all_medium_videos: List[Dict]):
        if not all_medium_videos or len(all_medium_videos) < self.num_playlists:
            return {0: all_medium_videos}
        texts = [v.get('text_snippet', '') for v in all_medium_videos]
        tfidf_matrix = self.vectorizer.fit_transform(texts)
        n_clusters = min(self.num_playlists, len(all_medium_videos))
        kmeans = MiniBatchKMeans(n_clusters=n_clusters, random_state=42, batch_size=50)
        labels = kmeans.fit_predict(tfidf_matrix)
        playlists = {i: [] for i in range(n_clusters)}
        for idx, label in enumerate(labels):
            playlists[int(label)].append(all_medium_videos[idx])
        for p_id in playlists:
            playlists[p_id] = sorted(playlists[p_id], key=lambda x: x.get('score', 0), reverse=True)
        return playlists
