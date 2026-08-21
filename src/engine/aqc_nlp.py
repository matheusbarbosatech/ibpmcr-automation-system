# -*- coding: utf-8 -*-
"""
Módulo AQC NLP — Validação de Integridade Sintática e Coesão Semântica
IBPM CR Automation System
"""

from typing import Dict, List, Tuple, Optional, Any, NamedTuple


class ResultadoIntegridade(NamedTuple):
    is_valido: bool
    completeness: float
    last_pos: str
    diagnostico: str


class ValidadorSentido:
    """
    Validador Heurístico de Sentido e Integridade Gramatical.
    Inspeciona fronteiras de corte narrativo para prevenir frases truncadas.
    """

    def __init__(self):
        self.bad_tail_pos = {"ADP", "DET", "CCONJ", "SCONJ"}
        self.valid_terminals = {".", "!", "?", "...", "…”", "…", "''", '""', '"'}

    def analisar_frequencia_louvor(self, doc: Any) -> bool:
        """
        Gatilho heurístico para identificar intervenção de cânticos/louvores
        que interrompem a densidade doutrinária do sermão.
        """
        if not doc:
            return False
        
        try:
            tokens_str = [t.text for t in doc]
        except AttributeError:
            tokens_str = []
            
        palavras_louvor = {"Aleluia", "Glória", "Amém", "Hosana", "Louvado"}
        count = sum(1 for token in tokens_str if token in palavras_louvor)
        return count >= 2 or ("Aleluia" in tokens_str and len(tokens_str) <= 5)

    def validar_integridade_corte(self, doc: Any) -> ResultadoIntegridade:
        """
        Verifica se a estrutura sintática do documento spaCy (ou mock equivalente)
        termina com integridade oracional plena.
        """
        if not doc:
            return ResultadoIntegridade(
                is_valido=False,
                completeness=0.0,
                last_pos="",
                diagnostico="Texto ou documento vazio."
            )

        # Trata o iterável de tokens
        try:
            tokens = list(doc)
        except Exception:
            tokens = []

        if not tokens:
            return ResultadoIntegridade(
                is_valido=False,
                completeness=0.0,
                last_pos="",
                diagnostico="Sem tokens na oração."
            )

        # Checa intervenção de cânticos
        if self.analisar_frequencia_louvor(doc):
            return ResultadoIntegridade(
                is_valido=False,
                completeness=0.4,
                last_pos=tokens[-1].pos_ if hasattr(tokens[-1], "pos_") else "",
                diagnostico="Intervenção de cântico/louvor interrompe densidade doutrinária."
            )

        last_token = tokens[-1]
        last_text = getattr(last_token, "text", str(last_token)).strip()
        last_pos = getattr(last_token, "pos_", "")

        # 1. Terminação fatal em conectivo adpositivo (ADP/DET/CCONJ/SCONJ)
        if last_pos in self.bad_tail_pos:
            return ResultadoIntegridade(
                is_valido=False,
                completeness=0.4,
                last_pos=last_pos,
                diagnostico=f"Decapitação pós-preposicional/conectivo. Estrutura suspensa na tag POS ({last_pos})."
            )

        # 2. Presença de pontuação terminal natural ou pontuação de encerramento
        has_punctuation = any(last_text.endswith(p) for p in self.valid_terminals) or last_pos == "PUNCT"

        # 3. Raiz Oracional (ROOT)
        has_root = any(getattr(t, "dep_", "") == "ROOT" for t in tokens)

        is_valido = has_punctuation and has_root and (last_pos not in self.bad_tail_pos)

        score = 1.0
        diagnosticos = []
        if not has_punctuation:
            score -= 0.3
            diagnosticos.append("Ausência de pontuação terminal natural.")
        if not has_root:
            score -= 0.3
            diagnosticos.append("Ausência de oração principal (ROOT).")

        diagnostico_final = "Sintaxe e coesão oracional íntegras." if is_valido else (" ".join(diagnosticos) or "Frase suspensa.")

        return ResultadoIntegridade(
            is_valido=is_valido,
            completeness=float(max(0.0, score)),
            last_pos=last_pos,
            diagnostico=diagnostico_final
        )


class TextCohesionNLP:
    """
    Abstração avançada que consome vetores de linguagem e tabelas de
    árvores de dependência da língua Portuguesa via spaCy.
    """

    def __init__(self, spacy_model: str = "pt_core_news_sm", nlp_instance: Any = None):
        if nlp_instance is not None:
            self.nlp = nlp_instance
        else:
            try:
                import spacy
                self.nlp = spacy.load(spacy_model, disable=["ner"])
            except Exception:
                self.nlp = None
        self.validador = ValidadorSentido()

    def analyze_sentence_completeness(self, text: str) -> Dict[str, Any]:
        if not text or not text.strip() or self.nlp is None:
            return {"completeness": 0.0, "last_pos": "", "diagnostico": "Texto vazio ou spaCy indisponível."}

        doc = self.nlp(text)
        res = self.validador.validar_integridade_corte(doc)
        return {
            "completeness": res.completeness,
            "last_pos": res.last_pos,
            "diagnostico": res.diagnostico
        }

    def calculate_wpm(self, text: str, audio_duration_sec: float) -> float:
        if audio_duration_sec <= 0:
            return 0.0
        if self.nlp is not None:
            doc = self.nlp(text)
            words = [token for token in doc if getattr(token, "is_alpha", True) or getattr(token, "is_digit", False)]
            word_count = len(words)
        else:
            word_count = len(text.split())
        return float((word_count / audio_duration_sec) * 60.0)


class MotorAQC:
    """
    Motor global do AQC NLP. Orquestra a validação sintática e semântica.
    """

    def __init__(self):
        self.validador = ValidadorSentido()

    def avaliar(self, doc: Any) -> ResultadoIntegridade:
        return self.validador.validar_integridade_corte(doc)
