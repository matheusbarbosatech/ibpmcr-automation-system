import sys
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from kaggle.api.kaggle_api_extended import KaggleApi

print("================================================================")
print("📡 ACOMPANHAMENTO EM TEMPO REAL: KAGGLE GPU TRANSCRIÇÃO")
print("================================================================\n", flush=True)

api = KaggleApi()
api.authenticate()

kernel_slug = "omatheusbsilva/ibpmcr-whisper-gpu"
printed_lines = set()

while True:
    try:
        status_info = api.kernels_status(kernel_slug)
        raw_status = getattr(status_info, "status", status_info)
        status_str = str(raw_status).upper()
        
        logs = api.kernels_logs(kernel_slug)
        if isinstance(logs, list):
            for item in logs:
                text = item.get("data", "").strip() if isinstance(item, dict) else str(item).strip()
                if text and text not in printed_lines:
                    printed_lines.add(text)
                    print(text, flush=True)
                    
        if any(term in status_str for term in ["COMPLETE", "ERROR", "CANCELLED"]):
            print(f"\n✨ Execução no Kaggle finalizada com status: {status_str}", flush=True)
            break
            
    except Exception as e:
        print(f"⚠️ Aviso: {e}", flush=True)
        
    time.sleep(8)
