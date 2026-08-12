# ⛪ IBPM CR Automation System - FASE 1: Varredura de Lives & Plano Mestre DE Mídia

> **REGRA DE OURO DA FASE 1:** NENHUM VÍDEO É RENDERIZADO OU CORTADO NESTA ETAPA.  
> **Foco:** Mapeamento completo da aba de LIVES (`/streams`), ingestão leve de áudio, transcrição via CPU otimizada (Faster-Whisper INT8) e mineração dos **25 Pilares de Insights Teológicos, Litúrgicos e de Mídia**.

---

## 🎯 Arquitetura & Estrutura de Pastas da Fase 1

```text
ibpmcr-automation-system/
├── config/
│   └── settings.py                # Configurações de caminhos locais, API Keys e Faster-Whisper
├── data/
│   ├── db/
│   │   └── ibpmcr_master.db       # Banco SQLite local estruturado para RAG e análises
│   ├── json/
│   │   └── plano_mestre_ibpmcr.json # Estado consolidado em JSON contendo os 25 pilares de insights
│   └── audio_podcasts/            # MP3s leves (64kbps mono)
├── reports/                       # Relatórios HTML e PDF
├── src/
│   ├── core/
│   │   └── state_manager.py       # Gerenciador de estado no SQLite/JSON com idempotência
│   └── discovery/
│       ├── channel_sweeper.py     # Varredura do YouTube focada na aba de LIVES (/streams) + API v3
│       ├── transcriber_batch.py   # Download de MP3 leve + Transcrição CPU (faster-whisper INT8)
│       ├── content_analyzer.py    # Motor avançado de PLN, Homilética, Liturgia, Oratória, Mídia e Operações (25 Pilares)
│       └── generate_report.py     # Gerador de relatórios executivos em HTML e PDF
├── run_fase1_varredura.py         # Script principal de orquestração
├── requirements.txt
└── README.md
```

---

## 💎 Os 25 Pilares de Insights Minerados por Culto

### 🏛️ A. Homilética, Teologia Avançada & Mapeamento Bíblico (AT vs NT)
1. **Pregador / Preletor:** Atribuição do mensageiro (*Pastor Titular, Pastora, Convidado, etc.*).
2. **Série / Campanha:** Identificação da campanha (*Quarta Profética, Santa Ceia, Restituição, etc.*).
3. **Estilo Homilético:** Classificação (*Doutrinária, Evangelística, Profética, Encorajamento*).
4. **Passagens Bíblicas:** Mapeamento de livros, capítulos e versículos pregados (*Isaías, Salmos, Atos, etc.*).
5. **Proporção AT vs NT:** Percentual de embasamento no Antigo Testamento vs Novo Testamento.
6. **Ilustrações & Testemunhos:** Catalogação de metáforas e testemunhos do altar.
7. **Análise Sazonal:** Tag de datas e temporadas festivas.

### 🎙️ B. Oratória, Liturgia Pentecostal & Qualidade Técnica
8. **Dinâmica do Tom & Sentimentos:** Sentimento emocional predominante (*Gratidão, Esperança, Clamor*).
9. **Glossário Pastoral:** Bordões e expressões proféticas marcantes.
10. **Altar Call (Apelo):** Minutagem exata da chamada ao altar.
11. **Oração por Cura & Libertação:** Minutagem exata do clamor por milagres.
12. **Elementos Sagrados:** Minutagem da Santa Ceia, Unção com Óleo, etc.
13. **Diagnóstico Técnico de Áudio:** Avaliação de estabilidade sonora.

### 🎵 C. Louvor & Adoração
14. **Repertório de Hinos:** Catalogação dos cânticos de adoração.
15. **Adoração Espontânea:** Marcação dos momentos de louvor espontâneo.

### 📱 D. Kits de Conteúdo, Social Media & Conexão Local (Campo Grande - RJ)
16. **Frases de Impacto & Ganchos Virais:** Citações com minutagem para Shorts/Reels 9:16.
17. **Linha do Tempo das Etapas:** Divisão exata em min/seg (Louvor, Palavra, Apelo, Ofertas).
18. **Score de Potencial Viral:** Nota de 0 a 100 baseada em engajamento e PNL.
19. **Thumbnail Titulo:** Sugestão de título curto (3 a 5 palavras) para capas.
20. **Legenda Instagram:** Texto formatado com emojis e chamada para ação (CTA).
21. **Copywriting Geolocalizado:** Texto de convite focado na região de Campo Grande - RJ.

### 📬 E. Comunicação Pastoral, Produtos Derivados & RAG
22. **Resumo Pastoral:** Síntese em 1 parágrafo para membros ausentes.
23. **Palavra Profética da Semana:** 5 palavras-chave para o boletim via WhatsApp/Telegram.
24. **Roteiro para Células / EBD:** 3 a 4 perguntas reflexivas para estudo em grupo.
25. **Chunks RAG Teológicos:** Fatiamento em blocos com timestamps salvos no SQLite para futura busca semântica.

---

## 🚀 Como Executar Localmente na CPU

1. **Instalar as dependências:**
   ```bash
   pip install -r requirements.txt
   python -m spacy download pt_core_news_sm
   ```

2. **Configurar o arquivo `.env`:**
   ```env
   YOUTUBE_API_KEY="SuaChaveAPI"
   YOUTUBE_CHANNEL_ID="UCHhLxWRcCB-xKo0ifOQ8MVQ"
   YOUTUBE_CHANNEL_HANDLE="@ibpmcr7976"
   USE_CUDA="False"
   WHISPER_MODEL_SIZE="small"
   ```

3. **Executar o script de orquestração:**
   ```bash
   python run_fase1_varredura.py
   ```
