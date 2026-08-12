# 🏛️ IBPM CR AUTOMATION SYSTEM - FASE 1

**Ecossistema de Automação, Ingestão de Áudio e Mineração de PLN do Canal @ibpmcr7976 (Igreja Batista Pentecostal Mundial - Campo Grande, RJ).**

---

## 🎯 Arquitetura em 4 Etapas Independentes e Idempotentes

Para garantir máxima estabilidade e eficiência em máquinas locais com CPU, a FASE 1 foi estruturada em 4 etapas isoladas:

```
ibpmcr-automation-system/
├── config/
│   └── settings.py                 # Configurações de caminhos locais e parâmetros do Whisper
├── data/
│   ├── db/
│   │   └── ibpmcr_master.db        # Banco SQLite local relacional
│   ├── json/
│   │   └── plano_mestre_ibpmcr.json # Plano Mestre consolidado
│   └── audio_podcasts/             # Pasta de áudios MP3 leves (64kbps mono)
├── reports/                        # Relatórios executivos em HTML e PDF
├── src/
│   ├── core/
│   │   └── state_manager.py        # Gerenciador de estado idempotente no SQLite
│   └── discovery/
│       ├── channel_sweeper.py      # Varredura do /streams + Download de MP3s com índice 001_...
│       ├── transcriber_batch.py    # Transcritor sequencial leitor de MP3 local
│       ├── content_analyzer.py     # Mineração PLN dos 25 pilares (Strict Grounding)
│       └── generate_report.py      # Gerador de relatórios executivos (HTML/PDF)
├── 1_baixar_audios.py              # Etapa 1: Download ordenado de MP3s leves (001 a 447+)
├── 2_transcrever_fila.py           # Etapa 2: Transcrição em fila sequencial via Faster-Whisper
├── 3_analisar_conteudo.py          # Etapa 3: Mineração PLN 100% fiel ao texto do SQLite
├── 4_gerar_relatorio.py            # Etapa 4: Exportação do Plano Mestre JSON e PDFs
├── requirements.txt
└── README.md
```

---

## 🚀 Como Executar Sequencialmente no Terminal

### 📥 1. Etapa 1: Download Organizado dos Áudios MP3 (001 a N)
Varre prioritariamente a aba `/streams`, ordena cronologicamente do 1º culto em 02/10/2022 ao mais recente e salva na pasta `data/audio_podcasts/` com o padrão `001_YYYY-MM-DD_[VIDEO_ID]_[TITULO].mp3`:
```powershell
python 1_baixar_audios.py
```

### 🎙️ 2. Etapa 2: Transcrição Sequencial via Faster-Whisper
Lê os arquivos MP3 do HD em ordem cronológica e salva a transcrição com timestamps por segundo no SQLite:
```powershell
# Transcrever todos os pendentes:
python 2_transcrever_fila.py

# Ou transcrever em lotes de 10 cultos por rodada:
python 2_transcrever_fila.py --batch 10
```

### 🧠 3. Etapa 3: Mineração PLN (Strict Grounding - 25 Pilares)
Analisa EXCLUSIVAMENTE os textos e timestamps gravados no SQLite, identificando trechos de Shorts 9:16, passagens bíblicas reais, timeline da liturgia e score viral:
```powershell
python 3_analisar_conteudo.py
```

### 📊 4. Etapa 4: Exportação de JSON e Relatórios Executivos
Exporta o `plano_mestre_ibpmcr.json` e gera os relatórios em PDF (`PLANO_MESTRE_IBPMCR_COMPLETO.pdf`) e HTML:
```powershell
python 4_gerar_relatorio.py
```

---

## 🛡️ Idempotência e Resiliência
Todas as etapas consultam o banco SQLite (`data/db/ibpmcr_master.db`) antes de executar qualquer operação. Se a conexão cair, a energia for interrompida ou você fechar o terminal, basta rodar novamente o script da etapa desejada e ele **continuará exatamente de onde parou!**
