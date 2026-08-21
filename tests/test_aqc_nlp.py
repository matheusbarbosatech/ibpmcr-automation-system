# -*- coding: utf-8 -*-
"""
Testes Unitários AQC NLP — Mocks do spaCy e Classificação de Sentido Completo
IBPM CR Automation System
"""

import pytest
from unittest.mock import MagicMock
from src.engine.aqc_nlp import ValidadorSentido, MotorAQC, TextCohesionNLP


@pytest.mark.parametrize("lista_tokens, esperado", [
    # Cenário A: Frase Suspensa terminada fatalmente num conectivo adpositivo
    ([("O", "DET", "det"), ("Salvador", "NOUN", "nsubj"), ("de", "ADP", "case")], False),
    # Cenário B: Pregação Teológica Estrutural Plena, Fecho Terminal
    ([("Ele", "PRON", "nsubj"), ("sofreu", "VERB", "ROOT"), ("na", "ADP", "case"), ("cruz", "NOUN", "obl"), (".", "PUNCT", "punct")], True),
    # Cenário C: Intervenção de Cânticos Interrompendo a Densidade Doutrinária (Falso Sentido)
    ([("Aleluia", "INTJ", "ROOT"), ("Deus", "PROPN", "nsubj"), ("Obrigado", "VERB", "ROOT")], False)
])
def test_classificador_fronteiras_teologicas(mock_spacy_doc_factory, lista_tokens, esperado):
    # Organizar (Arrange): Instanciar classes de fronteiras não baseadas no tensor,
    # utilizando uma predição emulação injetável.
    doc_emulado = mock_spacy_doc_factory(lista_tokens)
    validador = ValidadorSentido()

    # Stubbing heurístico para injetar gatilhos nas frequências léxicas e desbancar lógicas complexas.
    validador.analisar_frequencia_louvor = MagicMock(
        return_value=(True if "Aleluia" in [t[0] for t in lista_tokens] else False)
    )

    # Agir (Act): Invocação lógica de regras formais
    resultado_heuristico = validador.validar_integridade_corte(doc_emulado)

    # Afirmar (Assert): Valida as resoluções finais da suíte NLP.
    assert resultado_heuristico.is_valido == esperado

    # Confirmar integridade comportamental invocando verificações isoladas simuladas
    validador.analisar_frequencia_louvor.assert_called_once()


def test_motor_aqc_avaliar(mock_spacy_doc_factory):
    doc_valido = mock_spacy_doc_factory([("Deus", "PROPN", "nsubj"), ("ama", "VERB", "ROOT"), (".", "PUNCT", "punct")])
    motor = MotorAQC()
    resultado = motor.avaliar(doc_valido)
    assert resultado.is_valido is True
    assert resultado.last_pos == "PUNCT"
