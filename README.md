# IBPM CR - Ecossistema de Automação de Mídia e Gestão Eclesiástica

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Google Colab T4 GPU](https://img.shields.io/badge/Google%20Colab-T4%20GPU-orange.svg)](https://colab.research.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Ecossistema inteligente e 100% automatizado em Python para a **Igreja Batista Pentecostal Mundial (IBPM CR)** - canal do YouTube [`@ibpmcr7976`](https://www.youtube.com/@ibpmcr7976). 

O sistema integra processamento de áudio/vídeo com IA, pesquisa operacional, modelos preditivos de retenção pastoral, visão computacional, RAG teológico exegético, clonagem de voz e canais interativos de atendimento ao comunitário.

---

## 📌 Funcionalidades Principais

- **Mídia & Inteligência Audiovisual:**
  - Gestão de estado idempotente (`estado_videos.json`) com 3 filas de prioridade (Recentes 48h, Mais Vistos com deduplicação rápida e Acervo Histórico do 1º ao 440º vídeo).
  - Transcrição acelerada via GPU CUDA com `Faster-Whisper`.
  - Edição dinâmica de cortes 9:16 (Shorts/Reels) com legendas acopladas e agrupamento 16:9 de temas litúrgicos (Oração, Família, Fé, Libertação).
  - Mapeamento e catalogação automática de louvores com `librosa` e `AcoustID`.
  - Tratamento de áudio com `pydub` e geração automática de Feed RSS XML de Podcasts.

- **Inteligência Artificial & PNL:**
  - **RAG Teológico Exegético:** Assistente com `LlamaIndex` e `ChromaDB` para busca vetorial de sermões e termos em grego/hebraico.
  - **Clonagem de Voz Pastoral:** Geração de devocionais diários narrados com a voz clonada da liderança (`XTTS-v2`).
  - **EBD Kids NLP:** Adaptador que simplifica a linguagem dos cultos em historinhas infantis atrativas (`spaCy`).
  - **Detector de Testemunhos:** Extração automática de relatos de milagres e vitórias (`spaCy NER`) para o "Mural de Testemunhos".
  - **Análise de Sentimentos:** Mineração de comentários no YouTube usando `BERTimbau`.

- **Analytics, Visão Computacional & Pesquisa Operacional:**
  - **Otimizador de Escalas:** Solver CSP via `Google OR-Tools` para alocação justa de voluntários sem conflitos de datas.
  - **Alerta de Evasão Pastoral:** Análise de RFM (Recência, Frequência e Engajamento) com `scikit-learn` para retenção comunitária.
  - **Visão Computacional:** Contagem anônima de pessoas e lotação do templo em tempo real via `YOLOv8` e `OpenCV`.
  - **Geo Analytics:** Mapas de calor espaciais de membros e pedidos de oração na Zona Oeste (Campo Grande) com `GeoPandas` e `Folium`.

- **Geração Programática & Canais de Atendimento:**
  - Gerador de E-books, Devocionais e Apostilas em PDF (`fpdf2`).
  - Desenho automático de cartões de aniversário via `Pillow` enviados no dia às 08:00.
  - Slides automáticos em `.pptx` para reuniões de células (`python-pptx`).
  - Boletim semanal de áudio via `edge-tts`.
  - Bot no Telegram (`python-telegram-bot`) e Webhook de WhatsApp (`FastAPI` + Twilio).
  - Painel Web de Curadoria Humana (*Human-in-the-loop*) construído em `Streamlit`.

---

## 📐 Estrutura do Repositório

```text
ibpmcr-automation-system/
├── .github/
│   └── workflows/
│       └── rotina_diaria.yml          # Pipeline diário no GitHub Actions
├── config/
│   ├── settings.py                    # Configurações globais e paths do Drive
│   └── setup_drive.py                 # Criação das 16 subpastas no Google Drive
├── src/
│   ├── core/
│   │   ├── state_manager.py           # Gerenciador de estado e deduplicação
│   │   └── youtube_api.py             # Cliente da API v3 do YouTube
│   ├── processing/
│   │   ├── audio_transcriber.py       # Transcrição CUDA com Faster-Whisper
│   │   ├── video_editor.py            # Corte 9:16 / 16:9 com MoviePy e FFmpeg
│   │   ├── audio_processor.py         # Podcast RSS, pydub e tratamento de áudio
│   │   └── praise_detector.py         # Mapeamento de louvores (librosa/AcoustID)
│   ├── ai_modules/
│   │   ├── rag_theological.py         # RAG Teológico (LlamaIndex + ChromaDB)
│   │   ├── voice_cloning.py           # Clonagem de voz pastoral (XTTS-v2)
│   │   ├── nlp_kids.py                # Adaptador EBD Kids (spaCy)
│   │   ├── ner_testimonies.py         # Reconhecimento de testemunhos (NER)
│   │   └── sentiment_analysis.py      # Mineração de comentários (BERTimbau)
│   ├── analytics_opt/
│   │   ├── schedule_optimizer.py      # Otimização de escalas (Google OR-Tools)
│   │   ├── rfm_evasion.py             # Modelo preditivo de evasão (scikit-learn)
│   │   ├── computer_vision.py         # Contagem de público templo (YOLOv8)
│   │   └── geo_analytics.py           # Mapas de calor espaciais (GeoPandas/Folium)
│   ├── generation/
│   │   ├── pdf_generator.py           # PDFs de Devocionais/Kids (fpdf2)
│   │   ├── image_designer.py          # Cartões de Aniversário e Thumbs (Pillow)
│   │   ├── pptx_generator.py          # Slides de Célula (python-pptx)
│   │   └── tts_bulletin.py            # Boletim de áudio (edge-tts)
│   └── bot/
│       ├── telegram_bot.py            # Bot interativo Telegram
│       └── whatsapp_webhook.py        # Webhook FastAPI Twilio WhatsApp
├── dashboard/
│   └── app.py                         # App de Curadoria Humana em Streamlit
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Como Executar no Google Colab

1. **Abra um notebook no Google Colab** com aceleração por **GPU T4** (`Runtime` > `Change runtime type` > `T4 GPU`).
2. **Monte o Google Drive** e clone este repositório:
   ```python
   from google.colab import drive
   drive.mount('/content/drive')

   !git clone https://github.com/ibpmcr/ibpmcr-automation-system.git
   %cd ibpmcr-automation-system
   ```
3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   python -m spacy download pt_core_news_sm
   ```
4. **Inicialize a estrutura de pastas no Drive:**
   ```bash
   python config/setup_drive.py
   ```
5. **Execute a rotina de processamento:**
   ```bash
   python src/core/state_manager.py
   ```

---

## 💻 Como Executar o Dashboard Streamlit Localmente

```bash
# Clone e entre na pasta do projeto
git clone https://github.com/ibpmcr/ibpmcr-automation-system.git
cd ibpmcr-automation-system

# Crie e ative um ambiente virtual
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate

# Instale os requisitos
pip install -r requirements.txt

# Inicie a aplicação Streamlit
streamlit run dashboard/app.py
```

---

## ⚙️ Variáveis de Ambiente (`.env`)

Crie um arquivo `.env` na raiz do projeto conforme a especificação do `.env.example`:

```env
YOUTUBE_API_KEY="sua_chave_aqui"
TELEGRAM_BOT_TOKEN="seu_token_telegram"
TWILIO_ACCOUNT_SID="seu_sid_twilio"
TWILIO_AUTH_TOKEN="seu_auth_token"
TWILIO_WHATSAPP_NUMBER="whatsapp:+14155238886"
DRIVE_MOUNT_PATH="/content/drive/MyDrive/IBPM_CR_Cortes"
```

---

## 📜 Licença

Este projeto é desenvolvido para o uso exclusivo da **Igreja Batista Pentecostal Mundial (IBPM CR)** sob licença MIT.
