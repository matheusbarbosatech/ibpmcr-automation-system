import sys
import os
from pathlib import Path
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Carrega a chave do .env
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

from google import genai

print("========================================")
print(" 🚀 INICIANDO TESTE ISOLADO DO GEMINI")
print("========================================")

CHAVE = os.getenv("GEMINI_API_KEY", "")

try:
    print("⏳ Conectando aos servidores do Google (Novo SDK)...")
    client = genai.Client(api_key=CHAVE)
    
    # Mandando um prompt ultra simples
    response = client.models.generate_content(
        model='gemini-flash-latest',
        contents="Diga apenas: 'Olá, o Gemini está conectado e funcionando!'"
    )
    
    print("\n✅ SUCESSO ABSOLUTO! A IA RESPONDEU:")
    print(response.text)

except Exception as e:
    print("\n❌ O ERRO VERDADEIRO É ESTE AQUI:")
    print(str(e))
