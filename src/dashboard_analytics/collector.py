# -*- coding: utf-8 -*-
"""
Dashboard Analytics — Agregador Estatístico em Lote
IBPM CR Automation System
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class RegistroVeredito:
    id_corte: str
    situacao: str = "APROVADO"
    score: float = 0.0
    erro_critico: bool = False


class ColetorEstatistico:
    """
    Acumula vereditos e digere sumários estatísticos ignorando amostras
    com falhas físicas irrecuperáveis e calculando médias sobre amostras qualificadas (APROVADO).
    """

    def __init__(self, capacidade_alvo: int = 5):
        self.capacidade_alvo = capacidade_alvo
        self.amostras: List[RegistroVeredito] = []

    def acumular(self, amostra: RegistroVeredito) -> None:
        self.amostras.append(amostra)

    def digerir_sumario_estatistico(self) -> Dict[str, Any]:
        tamanho_total = len(self.amostras)
        if tamanho_total == 0:
            return {
                "tamanho_total": 0,
                "media_pontuacao_qualificados": 0.0,
                "taxa_aprovados": 0.0,
                "incidentes_irrecuperaveis": 0
            }

        amostras_processaveis = [a for a in self.amostras if not a.erro_critico]
        amostras_qualificadas = [a for a in amostras_processaveis if a.situacao == "APROVADO"]
        incidentes_irrecuperaveis = sum(1 for a in self.amostras if a.erro_critico)

        if amostras_qualificadas:
            media_pontuacao = float(sum(a.score for a in amostras_qualificadas) / len(amostras_qualificadas))
        elif amostras_processaveis:
            media_pontuacao = float(sum(a.score for a in amostras_processaveis) / len(amostras_processaveis))
        else:
            media_pontuacao = 0.0

        if amostras_processaveis:
            taxa_aprovados = float((len(amostras_qualificadas) / len(amostras_processaveis)) * 100.0)
        else:
            taxa_aprovados = 0.0

        return {
            "tamanho_total": tamanho_total,
            "media_pontuacao_qualificados": round(media_pontuacao, 1),
            "taxa_aprovados": round(taxa_aprovados, 1),
            "incidentes_irrecuperaveis": incidentes_irrecuperaveis
        }
