import re, json, time
from pathlib import Path

txt_dir = Path(r'c:\Users\matheus\.gemini\antigravity-ide\scratch\ibpmcr-automation-system\data\transcriptions\txt')
json_dir = Path(r'c:\Users\matheus\.gemini\antigravity-ide\scratch\ibpmcr-automation-system\data\transcriptions\json')

txt_files = sorted(list(txt_dir.glob('*.txt')))

header_junk_exact = [
    'ibpm cr', '472 inscritos', 'vídeos', 'sobre', 'replay do chat ao vivo',
    'veja o que outras pessoas disseram sobre este vídeo enquanto ele estava ao vivo.',
    'abrir painel'
]

sidebar_stop_patterns = [
    r'^\d+([\.,]\d+)?\s*(mil|mi|k)?\s*assistindo$',
    r'^\d+([\.,]\d+)?\s*(mil|mi|k)?\s*visualizações$',
    r'^transmitido há',
    r'^há \d+\s*(h|dia|dias|sem|semanas|mês|meses|ano|anos)',
    r'^ao vivo$',
    r'^novo$',
    r'^cazétv$', r'^revista oeste$', r'^connect ministry$', r'^mauro cezar$', r'^dr\. marco menelau$', r'^kof da depressão$',
    r'^\d+[\s°º\w\(\)/-]*dia de festividade',
    r'quarta profética - restituição',
    r'domingo de celebração -',
    r'culto de santa ceia -'
]

aria_pattern = re.compile(r'^\d+\s*(hora|horas|minuto|minutos|segundo|segundos)(\s*e\s*\d+\s*(minuto|minutos|segundo|segundos))?$', re.IGNORECASE)
ts_aria_pattern = re.compile(r'^\[(\d{1,2}:\d{2}(:\d{2})?)\]\s*\d+\s*(hora|horas|minuto|minutos|segundo|segundos).*', re.IGNORECASE)

cleaned_count = 0

for tf in txt_files:
    if tf.name == 'lista_exata_faltantes.txt':
        continue
    try:
        content = tf.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        continue
        
    if 'AVISO DE AUDITORIA E DOCUMENTAÇÃO' in content:
        continue
        
    lines = content.splitlines()
    clean_lines = []
    
    in_speech = False
    
    for l in lines:
        l_str = l.strip()
        if not l_str:
            continue
            
        l_lower = l_str.lower()
        
        # Header filtering
        if not in_speech:
            if any(h in l_lower for h in header_junk_exact):
                continue
            if 'inscritos' in l_lower and len(l_str) < 30:
                continue
            in_speech = True
            
        # Tail sidebar filtering
        is_sidebar = False
        for pat in sidebar_stop_patterns:
            if re.search(pat, l_str, re.IGNORECASE):
                is_sidebar = True
                break
        if is_sidebar:
            break
            
        # Remove aria labels
        if aria_pattern.match(l_str) or ts_aria_pattern.match(l_str):
            continue
            
        clean_lines.append(l_str)
        
    full_text = ' '.join(clean_lines)
    
    # Format into clean paragraphs (4 sentences per paragraph)
    sentences = re.split(r'(?<=[.!?])\s+', full_text)
    paragraphs = []
    curr = []
    for s in sentences:
        if not s.strip():
            continue
        curr.append(s.strip())
        if len(curr) >= 4:
            paragraphs.append(' '.join(curr))
            curr = []
    if curr:
        paragraphs.append(' '.join(curr))
        
    formatted_txt = '\n\n'.join(paragraphs)
    
    try:
        tf.write_text(formatted_txt, encoding='utf-8')
        cleaned_count += 1
    except Exception as e:
        print(f'Error writing {tf.name}: {e}')

print(f'Done! Successfully cleaned {cleaned_count} TXT files.')
