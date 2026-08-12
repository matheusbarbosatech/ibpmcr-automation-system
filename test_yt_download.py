import yt_dlp

url = "https://www.youtube.com/watch?v=2hvx5L2DR2U"

for b in ["edge", "chrome", "brave"]:
    print(f"\n--- TENTANDO COM NAVEGADOR: {b.upper()} ---")
    try:
        ydl_opts = {
            'format': 'm4a/bestaudio/best',
            'cookiesfrombrowser': (b,),
            'quiet': False
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            print(f"[OK SUCESSO] {b.upper()}! Titulo: {info.get('title')}")
            break
    except Exception as e:
        print(f"  [FALHOU] {b}: {e}")
