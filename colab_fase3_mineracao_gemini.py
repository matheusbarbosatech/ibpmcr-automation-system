# ===========================================================================
# 🚀 FASE 3 PURA: MINERAÇÃO DE CONTEÚDO (GEMINI 1.5 FLASH + FREIO ABS)
# ===========================================================================

import os, json, sqlite3, time
from pathlib import Path

# Conecta ao Google Drive
try:
    from google.colab import drive
    drive.mount('/content/drive', force_remount=False)
except ImportError:
    pass

# Instala o SDK oficial do Google Gemini e barra de progresso
os.system("pip install -q google-generativeai tqdm")

from tqdm import tqdm
import google.generativeai as genai

# 🔑 CHAVE DA API DO GOOGLE GEMINI (Cole sua chave do AI Studio entre as aspas abaixo)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "SUA_CHAVE_GEMINI_AQUI")
if GEMINI_API_KEY and GEMINI_API_KEY != "SUA_CHAVE_GEMINI_AQUI":
    genai.configure(api_key=GEMINI_API_KEY)

# Configura o modelo para forçar saída 100% JSON
ia_model = genai.GenerativeModel(
    'gemini-1.5-flash',
    generation_config={"response_mime_type": "application/json", "temperature": 0.3}
)

# 📂 PASTAS NO SEU GOOGLE DRIVE
GDRIVE_DIR = Path("/content/drive/MyDrive/IBPM_CR_Cortes")
TRANSCRICOES_DIR = GDRIVE_DIR / "audio_podcasts" / "transcricoes"
INSIGHTS_DIR = GDRIVE_DIR / "insights_fase3"
DB_PATH = GDRIVE_DIR / "ibpmcr_master.db"

INSIGHTS_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

print("===========================================================================")
print(" 🚀 FASE 3: HUB INTELIGENTE DE MINERAÇÃO (GEMINI 1.5 FLASH)")
print("    Capacidade: 1 Milhão de Tokens | Modo: JSON Forçado | Proteção: Freio ABS")
print("===========================================================================\n")

# PROMPT DO SISTEMA (A Engenharia dos 6 Pilares)
PROMPT_SYSTEM = """Você é um Curador de Conteúdo e Teólogo Sênior especializado em comunicação cristã.
Analise a pregação integral fornecida e retorne ESTRITAMENTE UM OBJETO JSON VÁLIDO contendo as chaves abaixo. 
Não adicione formatação markdown fora do JSON.

{
  "01_tema_central": "Resumo executivo da mensagem em 2 a 3 parágrafos curtos.",
  "02_frases_virais": ["Frase 1", "Frase 2", "Frase 3", "Frase 4"],
  "03_passagens_biblicas": ["Livro Cap:Vers"],
  "04_ideia_carrossel_instagram": ["Slide 1", "Slide 2", "Slide 3", "Slide 4"],
  "05_cortes_virais": [
    {"titulo": "Título Chamativo", "contexto": "Resumo do corte", "sugestao_b_roll": "Imagem de apoio visual", "score_viral": 95, "trecho_inicial": "primeiras 5 palavras do trecho", "trecho_final": "ultimas 5 palavras do trecho"}
  ],
  "06_prompt_thumbnail": "Cinematic 8k photo of pastor preaching, dramatic lighting, highly detailed..."
}"""

# 🔍 MAPEAMENTO DA FILA (Lê apenas os .txt que a Fase 2 já gerou)
txt_files = sorted([f for f in TRANSCRICOES_DIR.glob("*.txt") if f.stat().st_size > 100])

# Filtra apenas os que ainda não foram minerados pela Fase 3 (Idempotência)
pending_files = []
for f in txt_files:
    insight_path = INSIGHTS_DIR / f"{f.stem}.insights.json"
    if not (insight_path.exists() and insight_path.stat().st_size > 100):
        pending_files.append(f)

print(f"📋 Cultos prontos para mineração: {len(pending_files)} / {len(txt_files)}\n")

if not pending_files:
    print("🎉 Todos os textos transcritos já foram minerados com sucesso!")
else:
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Criar coluna no banco de dados caso não exista para salvar os insights
    try:
        cursor.execute("ALTER TABLE transcricoes ADD COLUMN insights_json TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass # A coluna já existe

    for txt_path in tqdm(pending_files, desc="Minerando Cultos na IA", unit="culto"):
        v_name = txt_path.stem
        insight_path = INSIGHTS_DIR / f"{v_name}.insights.json"
        
        try:
            # 1. Lê o texto integral gerado pela Fase 2
            with open(txt_path, "r", encoding="utf-8") as f: 
                full_text = f.read()
            
            # 2. Constrói o Prompt e envia para a IA
            prompt_completo = f"{PROMPT_SYSTEM}\n\nTítulo: {v_name}\n\nPregação Integral:\n{full_text}"
            response = ia_model.generate_content(prompt_completo)
            
            if response.text:
                # 3. Salva o JSON na pasta insights_fase3/
                with open(insight_path, "w", encoding="utf-8") as f: 
                    f.write(response.text)
                
                # 4. Atualiza o Banco de Dados com os insights
                cursor.execute("UPDATE transcricoes SET insights_json = ? WHERE nome_arquivo = ?", 
                               (response.text, v_name))
                conn.commit()
                
            # 🛑 5. O FREIO ABS (Proteção contra Bloqueio de API)
            # Atraso de 4.5 segundos garante no máximo ~13 requisições por minuto (Limite gratuito é 15)
            time.sleep(4.5)
            
        except KeyboardInterrupt:
            print(f"\n🛑 Processo interrompido manualmente pelo usuário durante: {v_name}")
            break
        except Exception as e:
            print(f"\n⚠️ Erro inesperado ao minerar {v_name}: {e}")
            time.sleep(10)

    conn.close()
    
print("\n" + "=" * 75)
print(" ✅ FASE 3 PAUSADA OU CONCLUÍDA COM SUCESSO!")
print("=" * 75)
