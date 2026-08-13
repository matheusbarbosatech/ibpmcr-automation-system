# 🏛️ IBPM CR AUTOMATION SYSTEM

**Ecossistema Modular de Ingestão de Áudio, Transcrição em GPU, Mineração de Inteligência Teológica (Gemini 1.5 Flash / Groq LLM) e Produção de Conteúdo do Canal @ibpmcr7976 (Igreja Batista Pentecostal Mundial - Campo Grande, RJ).**

---

## 🎯 Arquitetura Modular em 4 Fases ETL (Desacoplada & Resiliente)

```text
ibpmcr-automation-system/
├── 📥 FASE 1: INGESTÃO & SINCRONIZAÇÃO
│   ├── 1_baixar_audios.py          # Download ordenado dos cultos (001 a 449+)
│   └── upload_monitorado.py        # Upload resiliente para Google Drive via Rclone
│
├── 🎙️ FASE 2: TRANSCRIÇÃO EM MASSA GPU (GOOGLE COLAB)
│   └── colab_fase2_transcricao_gpu.py  # Transcrição Faster-Whisper Large-v3 (GPU T4) -> .txt/.json no Drive
│
├── 🧠 FASE 3: HUB INTELIGENTE DE MINERAÇÃO (NUVEM)
│   ├── 3_mineracao_fase3.py        # Mineração com Gemini 1.5 Flash / Groq LLM (Freio ABS 4.5s)
│   └── src/discovery/content_miner_llm.py # Extrator dos 6 Pilares Estruturados em JSON
│
└── 🎬 FASE 4: AUTOMAÇÃO DE CORTES E GERAÇÃO DE ATIVOS (EM CONSTRUÇÃO)
    ├── Gerador de Cortes em Vídeo 9:16 (Corte por Timestamps do JSON)
    ├── Renderização de Legendas Animadas (Burned-in Captions)
    └── Exportação do Plano Mestre Consolidado e Relatórios Executivos (PDF/HTML)
```

---

## 📋 Os 6 Pilares Extraídos na Fase 3 (Mineração Teológica & Viral)

Cada culto transcrito é minerado pela IA na nuvem e retorna um objeto JSON estritamente formatado com 6 pilares:

1. **`01_tema_central`**: Resumo executivo teológico do culto em 2 a 3 parágrafos curtos.
2. **`02_frases_virais`**: Lista com as 4 frases de maior impacto e poder de memorização.
3. **`03_passagens_biblicas`**: Referências de livros, capítulos e versículos citados no áudio.
4. **`04_ideia_carrossel_instagram`**: Estrutura pronta de 4 slides para postagem em carrossel.
5. **`05_cortes_virais`**: 3 sugestões de cortes virais para Reels/TikTok contendo:
   - Título impactante
   - Contexto do momento
   - Sugestão visual de B-Roll
   - Score viral (0 a 100)
   - Citação exata do trecho inicial e final falado
6. **`06_prompt_thumbnail`**: Prompt descritivo em inglês para geração de capas cinematográficas no Midjourney.

---

## 🚀 Como Executar o Fluxo no Colab e no Terminal

### 🎙️ Fase 2 (Google Colab GPU T4):
Execute a célula do `colab_fase2_transcricao_gpu.py` no Google Colab. Ele transcreve os áudios enviados pelo Rclone em velocidade máxima e grava os arquivos `.txt` e `.json` diretamente na pasta `audio_podcasts/transcricoes/` no seu Google Drive.

### 🧠 Fase 3 (Hub Inteligente):
Os arquivos `.txt` salvos no Drive são minerados pelo Gemini 1.5 Flash ou Groq LLM (Llama 3.3 70B). O script aplica o controle de vazão de 4.5 segundos ("Freio ABS") para respeitar rigorosamente o limite de 15 RPM da API gratuita.

---

## 🛡️ Idempotência e Resiliência Atômica
Todas as fases consultam o banco de dados SQLite (`ibpmcr_master.db`) e os arquivos do Google Drive antes de processar qualquer item. Se um processo for interrompido, o sistema recomeça exatamente do ponto onde parou de forma segura (usando escrita atômica `.tmp`).
