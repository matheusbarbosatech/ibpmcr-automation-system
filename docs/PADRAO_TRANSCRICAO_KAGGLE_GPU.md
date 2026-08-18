# PADRÃO OFICIAL DE TRANSCRIÇÃO - IBPM CR (KAGGLE GPU FASTER-WHISPER LARGE-V3)

Este documento especifica a estrutura formal e obrigatória de todos os arquivos de transcrição `.txt` e `.json` mantidos na pasta `data/transcriptions/`.

---

## 1. ESTRUTURA DO ARQUIVO DE TEXTO (.txt)

Todos os arquivos `.txt` devem seguir rigorosamente o cabeçalho e marcações de tempo:

```text
TRANSCRIÇÃO WHISPER LARGE-V3 GPU
ARQUIVO: [NÚMERO]_[ID_YOUTUBE]_[TITULO_SANITIZADO].[EXTENSÃO]
DURAÇÃO: [SEGUNDOS]s

[00:02:38] Texto transcrito do primeiro segmento...
[00:02:48] Texto transcrito do segundo segmento...
```

### Regras do TXT:
1. **Cabeçalho:** 3 primeiras linhas contendo o modelo de IA, nome do arquivo original e duração em segundos.
2. **Timestamps:** Cada linha de fala deve ser iniciada com marcação no formato `[HH:MM:SS]`.
3. **Casos Especiais (Sem fala humana / Vinheta):** Deve conter o aviso formal de auditoria especificando o motivo técnico.

---

## 2. ESTRUTURA DO ARQUIVO JSON (.json)

Todos os arquivos `.json` devem conter a estrutura padronizada com chaves de alto nível e lista detalhada de trechos (`segments`):

```json
{
  "file": "[NÚMERO]_[ID_YOUTUBE]_[TITULO_SANITIZADO].[EXTENSÃO]",
  "duration": 8656.52,
  "language": "pt",
  "words_count": 14250,
  "text": "Texto completo e corrido da transcrição do culto inteiro sem timestamps...",
  "segments": [
    {
      "start": 158.83,
      "end": 168.47,
      "text": "Texto transcrito do primeiro segmento."
    },
    {
      "start": 168.47,
      "end": 178.12,
      "text": "Texto transcrito do segundo segmento."
    }
  ]
}
```

### Regras do JSON:
1. **`file`**: Nome completo do arquivo original de áudio com extensão.
2. **`duration`**: Duração total em segundos (float com 2 casas decimais).
3. **`language`**: Código do idioma (`pt`).
4. **`words_count`**: Contagem total de palavras transcritas.
5. **`text`**: Texto corrido completo de toda a ministração/culto.
6. **`segments`**: Lista de objetos contendo `start` (segundo inicial), `end` (segundo final) e `text` (frase/trecho falado).
