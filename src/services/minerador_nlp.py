"""
Minerador NLP Extrativo, Heuristico e Agrupamento Tematico (Fase 2 Mineração Pro v2) - IBPM CR.

Melhorias v2 sobre v1:
1. parse_text_with_real_timestamps(): le [HH:MM:SS] reais do Whisper.
2. _score_positional_weight(): fator de peso por posicao temporal.
3. _score_emotional_intensity(): intensidade emocional por exclamacoes, repeticao e gatilhos.
4. _extract_title_from_content(): extrai titulo descritivo real por TF-IDF local.
5. short_hooks / medium_markers / blacklist expandidos (50+ padroes pentecostais brasileiros).
6. Threshold minimo de score: filtra cortes irrelevantes.
7. TextRank com max_features=500 e 15 iteracoes.
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

logger = get_logger("NLPHeuristicMinerProV2")


class DualSermonMiner:
    """
    Minerador de Alta Precisao v2: TextRank + Timestamps Reais + Posicao + Emocao + NMS + Heuristica.
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

        logger.info("Inicializado DualSermonMiner v2 (Timestamps Reais + Posicao + Emocao + NMS).")

    def format_timestamp(self, seconds):
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"

    def parse_text_with_real_timestamps(self, transcript_text):
        """Le timestamps [HH:MM:SS] reais do Whisper. Fallback para estimativa."""
        pattern = re.compile(r'\[(\d{2}):(\d{2}):(\d{2})\]\s*(.*?)(?=\[\d{2}:\d{2}:\d{2}\]|$)', re.DOTALL)
        matches = list(pattern.finditer(transcript_text))

        if len(matches) >= 5:
            sentences = []
            for i, m in enumerate(matches):
                h, mi, s = int(m.group(1)), int(m.group(2)), int(m.group(3))
                start_sec = h * 3600 + mi * 60 + s
                text = m.group(4).strip().replace('\n', ' ')
                if not text:
                    continue
                if i + 1 < len(matches):
                    h2, mi2, s2 = int(matches[i+1].group(1)), int(matches[i+1].group(2)), int(matches[i+1].group(3))
                    end_sec = h2 * 3600 + mi2 * 60 + s2
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
            logger.info(f"Timestamps reais: {len(sentences)} linhas do Whisper.")
            return sentences

        logger.warning("Sem timestamps [HH:MM:SS] suficientes - usando estimativa.")
        return self._parse_text_estimated(transcript_text)

    def _parse_text_estimated(self, transcript_text):
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

    def _compute_textrank(self, texts, damping=0.85):
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

    def _score_positional_weight(self, start_sec, total_duration):
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

    def _score_emotional_intensity(self, win_text):
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

    def _extract_title_from_content(self, win_text, max_words=7):
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

    def generate_windows(self, sentences, min_dur, max_dur, step=10):
        """
        Para SHORTS (min_dur < 180s): gera uma janela por ponto de inicio.
        Para MEDIOS (min_dur >= 180s): gera snapshots em 5 durações-alvo distintas
        (3, 5, 8, 12, 15 min) por ponto de inicio, para que o NMS escolha
        os melhores por score em vez de sempre pegar o minimo.
        """
        windows = []
        n = len(sentences)

        if min_dur >= 180.0:
            # Modo MEDIO: múltiplos tamanhos-alvo por ponto de inicio
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
            # Modo SHORT: uma janela por ponto de inicio (comportamento original)
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

    def suppress_nms(self, windows, iou_thresh):
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

    def extract_7_words_anchor(self, text, is_end=False):
        clean = re.sub(r'\[\d{2}:\d{2}:\d{2}\]', '', text).strip()
        words = clean.split()
        if len(words) < 7:
            words += ["palavra"] * (7 - len(words))
        return " ".join(words[-7:] if is_end else words[:7])

    def mine_sermon(self, transcript_text, sermon_id="IBPM_CULTO"):
        """v2: timestamps reais + posicao + emocao + titulo automatico + threshold minimo."""
        sentences = self.parse_text_with_real_timestamps(transcript_text)
        if not sentences:
            return {"job_id": f"job_v2_{sermon_id}", "source_video_id": sermon_id,
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
            hooks = sum(1.0 for h in self.short_hooks if re.search(h, win_text.lower()))
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
            markers = sum(1.0 for m in self.medium_markers if re.search(m, win_text.lower()))
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

        # --- Formatacao ---
        short_payload = []
        for idx, s in enumerate(shorts, 1):
            title = self._extract_title_from_content(s['text'])
            short_payload.append({
                "cut_id": f"short_{idx:03d}",
                "title_hook_a": title,
                "title_hook_b": f"{title} | IBPM CR",
                "start_anchor_7_words": self.extract_7_words_anchor(s['text'], is_end=False),
                "end_anchor_7_words": self.extract_7_words_anchor(s['text'], is_end=True),
                "category": "Gatilho Profetico",
                "emotional_tone": "Inspirador",
                "start_sec": round(s['start'], 2),
                "end_sec": round(s['end'], 2),
                "score": round(s['score'], 3),
                "text_snippet": s['text'][:200] + "..."
            })

        medium_payload = []
        for idx, m in enumerate(mediums, 1):
            title = self._extract_title_from_content(m['text'])
            medium_payload.append({
                "cut_id": f"mid_{idx:03d}",
                "title_hook_a": title,
                "title_hook_b": f"{title} - Pregacao Completa",
                "start_anchor_7_words": self.extract_7_words_anchor(m['text'], is_end=False),
                "end_anchor_7_words": self.extract_7_words_anchor(m['text'], is_end=True),
                "category": "Exegese",
                "emotional_tone": "Reflexivo",
                "start_sec": round(m['start'], 2),
                "end_sec": round(m['end'], 2),
                "score": round(m['score'], 3),
                "text_snippet": m['text'][:300] + "..."
            })

        insights_payload = {
            "job_id": f"job_v2_{sermon_id}",
            "source_video_id": sermon_id,
            "sermon_title": f"Culto IBPM CR {sermon_id}",
            "preacher_name": "Pastor IBPM CR",
            "short_form_cuts": short_payload,
            "mid_form_cuts": medium_payload,
            "metadata": {
                "total_duration_sec": round(total_duration, 1),
                "sentences_parsed": len(sentences),
                "uses_real_timestamps": sentences[0].get("has_real_ts", False) if sentences else False,
                "algorithm_version": "v2"
            }
        }

        self.export_relatorio_csv(sermon_id, short_payload + medium_payload)
        return insights_payload

    def export_relatorio_csv(self, source_file, cuts):
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

    def build_playlists(self, all_medium_videos):
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
