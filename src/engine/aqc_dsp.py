# -*- coding: utf-8 -*-
"""
Módulo AQC DSP — Qualidade Acústica de Sinal e Cadência de Fala
IBPM CR Automation System
"""

import numpy as np
from typing import Dict, Any, NamedTuple, Optional


class ScoreCadencia(NamedTuple):
    wpm: float
    pontos: float
    veredito: str


class AnalisadorDSP:
    """
    Motor DSP para inspeção de sinais sonoros (clipping ratio e silêncio RMS).
    opera em tensores NumPy sem acoplamento direto de arquivos físicos quando necessário.
    """

    def __init__(self, audio_signal: Optional[np.ndarray] = None, sample_rate: int = 22050):
        self.y = audio_signal if audio_signal is not None else np.array([], dtype=np.float32)
        self.sr = sample_rate

    def calcular_clipping_ratio(self, signal: Optional[np.ndarray] = None, threshold: float = 0.9) -> float:
        """
        Calcula a proporção de amostras com amplitude saturada (ceifamento/clipping).
        """
        y = signal if signal is not None else self.y
        if len(y) == 0:
            return 0.0

        abs_y = np.abs(y)
        clipped_samples = np.sum(abs_y >= threshold)
        return float(clipped_samples / len(y))

    def avalia_distorcao_fatal(self, clipping_ratio: float) -> bool:
        """
        Retorna True se o clipping ratio ultrapassar o limiar de tolerância fatal (> 5%).
        """
        return clipping_ratio > 0.05

    def calculate_silence_ratio(self, signal: Optional[np.ndarray] = None, db_threshold: float = -40.0, hop_length: int = 512) -> float:
        """
        Calcula a fração temporal em que a energia RMS fica abaixo do piso de ruído.
        """
        y = signal if signal is not None else self.y
        if len(y) == 0:
            return 1.0

        try:
            import librosa
            rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
            db_levels = librosa.amplitude_to_db(rms, ref=1.0)
        except Exception:
            frames = len(y) // hop_length
            if frames == 0:
                return 1.0
            rms = np.array([
                np.sqrt(np.mean(y[i*hop_length:(i+1)*hop_length]**2))
                for i in range(frames)
            ])
            with np.errstate(divide='ignore'):
                db_levels = 20 * np.log10(np.maximum(rms, 1e-10))

        total_frames = len(db_levels)
        if total_frames == 0:
            return 1.0

        silent_frames = np.sum(db_levels < db_threshold)
        return float(silent_frames / total_frames)


class MotorCadencia:
    """
    Cadenciador de ritmo de fala e densidade WPM (Words Per Minute).
    """

    def computar_pontuacao_wpm(self, texto: str, janela_segundos: float) -> ScoreCadencia:
        if janela_segundos <= 0:
            return ScoreCadencia(wpm=0.0, pontos=0.0, veredito="REJEITADO")

        palavras = texto.strip().split()
        wpm = float((len(palavras) / janela_segundos) * 60.0)

        delta = abs(wpm - 145.0)
        penalidade = max(0.0, (delta - 25.0) * 0.5)
        
        pontos = float(max(0.0, min(100.0, 100.0 - penalidade)))

        if wpm > 250.0 or wpm < 60.0 or pontos < 70.0:
            veredito = "REJEITADO"
        else:
            veredito = "APROVADO"

        return ScoreCadencia(wpm=wpm, pontos=pontos, veredito=veredito)
