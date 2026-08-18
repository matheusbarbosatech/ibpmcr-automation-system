# 🏛️ IBPM CR AUTOMATION SYSTEM

> **Ecossistema Inteligente e Custo-Zero de Mapeamento de Conteúdo, Transcrição em Nuvem (Kaggle GPU), Mineração Teológica Local e Editor de Vídeos em Python com Agendamento para o Canal [@ibpmcr7976](https://www.youtube.com/@ibpmcr7976).**

---

## 📌 Visão Geral

O **IBPM CR Automation System** é um ecossistema projetado para transformar as transmissões ao vivo e cultos da **Igreja Batista Pentecostal Mundial (Campo Grande, RJ)** em cortes virais (Reels, Shorts, TikTok), playlists temáticas no YouTube e pacotes completos de mídia visual.

O sistema foi reformulado com o objetivo de oferecer **eficiência máxima, zero custo de APIs pagas e zero sobrecarga no hardware local**:
- ❌ **Sem consumo de APIs de IA pagas** (OpenAI, Gemini Pago, Groq), eliminando surpresas financeiras ou estouro de cotas.
- ❌ **Sem execução de LLMs pesadas na máquina local**, garantindo um fluxo leve e rápido em qualquer computador.
- ❌ **Sem necessidade de baixar antecipadamente vídeos brutos de 2h** para analisar o conteúdo.

---

## ⚡ Arquitetura em 3 Fases

```text
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ FASE 1: MAPEAMENTO, INGESTÃO & TRANSCRIÇÃO GPU (KAGGLE NUVEM)                            │
│ 1. Mapeia todo o canal @ibpmcr7976 ordenando os cultos cronologicamente.                 │
│ 2. Extrai legendas nativas do YouTube para todos os vídeos que as possuem.               │
│ 3. Separa numa lista os vídeos faltantes (sem transcrição nativa).                       │
│ 4. Baixa apenas o áudio MP3 no formato mais leve possível para os faltantes.            │
│ 5. Upload para Notebook no Kaggle com GPU ativada (Faster-Whisper GPU).                   │
│ 6. Download dos JSONs de transcrição gerados de volta para o acervo local.             │
└──────────────────────────────────────────┬──────────────────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ FASE 2: MINERAÇÃO SEMÂNTICA & GERAÇÃO DE RELATÓRIOS (LOCAL - CUSTO ZERO)                 │
│ 1. Processa transcrições localmente via algoritmo de NLP (TextRank, heurísticas & NMS). │
│ 2. Identifica os melhores momentos, trechos virais, temas centrais e versículos citados.│
│ 3. Gera relatórios estruturados em JSON e Markdown com timestamps exatos de corte.      │
│ 🛑 NOTA: 100% focado em texto. Sem nenhum processamento de mídia ou vídeo nesta fase!    │
└──────────────────────────────────────────┬──────────────────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ FASE 3: EDITOR DE VÍDEO PYTHON (FLET WEBAPP/DESKTOP) & AGENDAMENTO AUTOMÁTICO          │
│ 1. WebApp / App Desktop desenvolvido em Python + Flet (interface estilo CapCut).        │
│ 2. Importa relatórios da Fase 2 e executa os cortes automáticos nos momentos marcados.  │
│ 3. Estratégia de Mídia: Tenta recortar via stream do YouTube (fallback: download local).│
│ 4. Formatos de Saída: Cortes 9:16 (Reels/Shorts/TikTok) + Vídeos 16:9 para Playlists de Média/Longa duração.        │
│ 5. Metadados de Mídia: Prompts para Thumbnails, Títulos, Legendas e Agendamento Automático│
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Detalhamento das Fases

### 📥 FASE 1: Mapeamento do Canal, Ingestão & Transcrição GPU (Kaggle)
* **Mapeamento do Acervo**: O script `executar_fase1_mapeamento_canal.py` realiza a varredura do canal e organiza todos os vídeos por ordem cronológica.
* **Extração Nativa**: Tenta obter primeiramente as legendas/transcrições já geradas nativamente pelo próprio YouTube.
* **Filtro de Faltantes & Extração de Áudio Leve**: Para os vídeos que não possuem transcrição nativa, o sistema gera uma lista e realiza o download **apenas do áudio em MP3 no formato mais leve possível** (baixo bitrate), otimizando armazenamento e tráfego de dados.
* **Transcrição Acelerada por GPU na Nuvem (Kaggle)**:
  * Os arquivos de áudio leves são enviados para um notebook no **Kaggle** com aceleração por GPU (NVIDIA T4 / P100), localizado em `notebooks/kaggle_gpu_transcribe/`.
  * O modelo **Faster-Whisper GPU** processa horas de culto em poucos minutos.
  * As transcrições retornam no formato `.json` e `.txt` com marcas de tempo detalhadas e são salvas no acervo local (`data/1.TRANSCRICOES/`).

---

### 🧠 FASE 2: Mineração Semântica & Relatórios (Local & Custo Zero)
* **Processamento NLP Nativo Local**: Executado através do script `executar_fase2_mineracao.py`.
* **Zero Custo de API & Zero Carga de LLM**:
  * **Sem APIs pagas**: Não depende de OpenAI, Gemini Pago ou Groq, evitando faturas surpresa e instabilidades de cota.
  * **Sem LLM Local**: Não requer a instalação de LLMs locais pesadas, evitando o travamento do computador do usuário.
  * **Algoritmo Inteligente**: Utiliza técnicas avançadas de sumarização extativa (TextRank), supressão de não-máximos (NMS) e dicionários teológicos/bíblicos customizados.
* **Relatórios Executivos**:
  * Síntese teológica e mapeamento do tema principal do culto.
  * Seleção de citações bíblicas e frases marcantes.
  * Mapeamento dos **cortes virais** com os timestamps exatos de início e fim (`HH:MM:SS`).
  * **Processamento 100% Textual**: Sem qualquer conversão ou renderização pesada de vídeo nesta fase.

---

### 🎬 FASE 3: Editor de Vídeos em Python (Flet), Renderização & Agendamento
* **Editor de Vídeo CapCut-Style (Python + Flet)**:
  * Interface moderna e responsiva desenvolvida com o framework **Flet** (Flutter para Python), permitindo execução tanto como WebApp quanto aplicativo Desktop (e expansão futura para Mobile).
* **Automação Baseada em Relatórios**:
  * Importa os relatórios JSON/Markdown/TXT gerados na Fase 2 e lê automaticamente todos os momentos recomendados para edição.
  * **Cortes Verticais (9:16)**: Geração automatizada de conteúdo para Shorts, Reels e TikTok com enquadramento inteligente e legendas embutidas.
  * **Vídeos de Média/Longa Duração (16:9)**: Recorte e seleção de sermões para criação de **Playlists Temáticas** no YouTube (ex: Séries de Pregações, Orações, Estudos).
* **Estratégia Otimizada de Captura de Mídia**:
  * **Tentativa Primária (Stream Direct)**: Efetua os cortes puxando o fluxo de vídeo diretamente dos servidores do YouTube a partir dos timestamps definidos no relatório, dispensando o download de vídeos brutos de 2 horas de duração.
  * **Fallback Local**: Caso ocorram instabilidades na conexão ou limitação do servidor, o sistema baixa o vídeo bruto pontualmente e realiza a renderização via FFmpeg local.
* **Metadados de Vídeo & Agendamento Automático**:
  * **Metadados Completos**: Geração de Prompts para Thumbnails cinematográficas (Midjourney/Flux), sugestões de Títulos impactantes, Legendas e Hashtags estratégicas — com foco exclusivo em produções em vídeo.
  * **Agendador de Redes Sociais**: Módulo para agendamento e postagem automática no **YouTube, Instagram, Facebook e TikTok**, agregando total comodidade ao fluxo diário.

---

## 📁 Estrutura de Diretórios

```text
ibpmcr-automation-system/
├── 📄 README.md                            # Documentação mestre do ecossistema
├── 📄 requirements.txt                     # Dependências Python do projeto
├── 📄 executar_fase1_mapeamento_canal.py   # Script Fase 1: Mapeamento, legendas e exportação de MP3 leve
├── 📄 executar_fase2_mineracao.py          # Script Fase 2: Mineração semântica e relatórios teológicos
├── 📄 executar_fase3_renderizacao.py       # Script/Protótipo Fase 3: Editor Flet e renderização
│
├── 📂 config/                              # Dicionários de temas, versículos e configurações
├── 📂 data/                                # Acervo e dados locais
│   ├── 1.TRANSCRICOES/                     # Armazenamento das transcrições JSON/TXT
│   ├── audio_podcasts/                     # Áudios MP3 leves destinados à transcrição em GPU
│   └── canal_ibpm_todos_videos.json        # Mapeamento consolidado do canal do YouTube
│
├── 📂 notebooks/                           # Notebooks e scripts de processamento em GPU na Nuvem
│   └── kaggle_gpu_transcribe/              # Notebook e script para Faster-Whisper GPU no Kaggle
│
├── 📂 src/                                 # Módulos Python reutilizáveis
│   ├── core/                               # Logger, banco de dados e utilitários base
│   ├── discovery/                          # Algoritmos de mineração semântica e NLP
│   └── services/                           # Serviços de corte FFmpeg e manipulação de mídia
│
└── 📂 reports/                             # Relatórios estruturados e planos de corte gerados pela Fase 2
```

---

## 🛠️ Como Executar

### 1️⃣ Fase 1 — Ingestão e Transcrição
```bash
python executar_fase1_mapeamento_canal.py
```
*Para os vídeos sem transcrição nativa, envie os MP3s leves gerados para o Kaggle (`notebooks/kaggle_gpu_transcribe/`) e baixe as transcrições JSON para `data/1.TRANSCRICOES/`.*

### 2️⃣ Fase 2 — Mineração Semântica (Local & Custo Zero)
```bash
python executar_fase2_mineracao.py
```
*Gera instantaneamente os relatórios teológicos e planos de corte com timestamps em `reports/`, sem custos de API ou uso de LLMs pesadas.*

### 3️⃣ Fase 3 — Editor Flet, Renderização e Agendamento
```bash
python executar_fase3_renderizacao.py
```
*Abre o Editor de Vídeos em Python (Flet) para importar o relatório da Fase 2, efetuar os cortes (por stream ou download local), gerar metadados de capa/título e agendar as publicações nas redes sociais.*

---

## 🤝 Propriedade e Uso
Desenvolvido para a **Igreja Batista Pentecostal Mundial (IBPM CR)** — Campo Grande, RJ.  
Visite o canal oficial: [@ibpmcr7976](https://www.youtube.com/@ibpmcr7976)
