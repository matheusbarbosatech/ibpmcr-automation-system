# IBPM CR - Ecossistema de Mídia e Gestão (FASE 1: Mapeamento & Plano Mestre)

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Google Colab T4 GPU](https://img.shields.io/badge/Google%20Colab-T4%20GPU-orange.svg)](https://colab.research.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Ecossistema inteligente em Python para a **Igreja Batista Pentecostal Mundial (IBPM CR)** - canal do YouTube [`@ibpmcr7976`](https://www.youtube.com/@ibpmcr7976).

> ⚠️ **OBJETIVO DA FASE 1:** Mapeamento completo, ingestão de dados, transcrição leve por IA (`Faster-Whisper` em GPU T4), mineração de texto com PNL (`spaCy`) e geração do **Plano Mestre de Mídia** (`plano_mestre_ibpmcr.json` e banco `SQLite`).
> **NENHUM VÍDEO É RENDERIZADO OU CORTADO NESTA ETAPA.**

---

## 📌 Escopo da Fase 1 (Mapeamento & Diagnóstico)

1. **Coleta e Extração de Metadados (`src/discovery/channel_sweeper.py`):**
   - Mapeia todos os ~440+ vídeos do canal `@ibpmcr7976` (3 anos de acervo histórico) via YouTube Data API v3 com fallback por `yt-dlp`.
   - Extrai metadados completos: `video_id`, `titulo_original`, `data_publicacao`, `duracao_segundos`, `visualizacoes`, `likes`, `quantidade_comentarios` e `descricao`.

2. **Ingestão de Áudio e Transcrição por IA (`src/discovery/transcriber_batch.py`):**
   - Ingestão leve de áudio em MP3.
   - Transcrição em lote acelerada por GPU T4 via `Faster-Whisper`.
   - Armazenamento dos textos completos com carimbos de tempo (*timestamps* segundo a segundo).

3. **Mineração de Texto e Classificação Temática (`src/discovery/content_analyzer.py`):**
   - Análise semântica via `spaCy` / NLTK para mapeamento das minutagens de início e fim:
     - **Cortes Curtos (9:16):** 30s a 60s de impacto espiritual.
     - **Cortes Médios (16:9):** 5 a 15 min categorizados por temas (*Oração*, *Família*, *Fé*, *Libertação*).
     - **E-books & Devocionais:** Sermões expositivos estruturados para conversão em PDF.
     - **EBD Kids:** Histórias bíblicas simplificáveis para o público infantil.
     - **Louvores Executados:** Mapeamento do bloco inicial de louvor.

4. **Geração do Plano Mestre de Mídia (`src/core/state_manager.py`):**
   - Gravação dos resultados no `plano_mestre_ibpmcr.json` e no banco `SQLite` (`plano_mestre_ibpmcr.db`) no Google Drive (`/content/drive/MyDrive/IBPM_CR_Cortes/`).

5. **Dashboard de Diagnóstico do Canal (`src/discovery/generate_report.py`):**
   - Geração de relatório visual de diagnóstico em **PDF** (`fpdf2`) e **HTML** contendo total de horas gravadas, gráfico de temas, top 20 vídeos de maior engajamento e inventário de cortes prontos para produção futura.

---

## 📐 Estrutura de Arquivos da Fase 1

```text
ibpmcr-automation-system/
├── config/
│   ├── settings.py                # Configurações do Drive e APIs
│   └── setup_drive.py             # Criação de pastas no Google Drive
├── src/
│   ├── discovery/
│   │   ├── channel_sweeper.py     # Varredura do histórico do YouTube
│   │   ├── transcriber_batch.py   # Transcrição em lote com Faster-Whisper
│   │   ├── content_analyzer.py    # Classificação temática e mapeamento de cortes
│   │   └── generate_report.py     # Relatório diagnóstico em PDF/HTML
│   └── core/
│       └── state_manager.py       # Gestão do plano_mestre_ibpmcr.json e SQLite
├── notebooks/
│   └── Fase1_Varredura_Colab.ipynb # Notebook pronto para rodar no Google Colab
├── requirements.txt
└── README.md
```

---

## 🚀 Como Executar a Fase 1 no Google Colab (GPU T4)

1. Abra o notebook `notebooks/Fase1_Varredura_Colab.ipynb` no Google Colab.
2. Certifique-se de que o acelerador de hardware esteja definido como **T4 GPU**.
3. Execute todas as células sequencialmente para gerar o **Plano Mestre de Mídia** no seu Google Drive.

---

## 📜 Licença

Desenvolvido para uso da **Igreja Batista Pentecostal Mundial (IBPM CR)** sob licença MIT.
