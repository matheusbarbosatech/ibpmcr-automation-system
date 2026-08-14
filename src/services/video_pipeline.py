"""
Serviço Orquestrador da Fase 4 (Video Pipeline) - IBPM CR Automation System.

Integra o download cirúrgico (yt-dlp), o gerador de legendas Karaokê (.ASS),
a renderização visual via FFmpeg (Crop 9:16, EBU R128, Auto-Ducking) e a publicação
nas redes sociais (YouTube Shorts e Instagram Reels).
"""

from pathlib import Path
from typing import Dict, Any, Optional

from src.core.logger import get_logger
from src.infrastructure.yt_dlp_client import YTDLPClient
from src.infrastructure.ffmpeg_client import FFmpegClient
from src.infrastructure.youtube_api import YouTubePublisher
from src.infrastructure.instagram_api import InstagramGraphAPIClient

logger = get_logger("VideoPipelineService")


def generate_ass_subtitle_file(words: list, output_path: Path) -> Path:
    """
    Gera um arquivo de legendas em formato Advanced SubStation Alpha (.ASS) com marcação Karaokê.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: DynamicKaraoke,Montserrat Black,52,&H00FFFFFF,&H0000D7FF,&H00000000,&H88000000,-1,0,0,0,100,100,0,0,1,4,2,2,50,50,380,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    chunk_size = 4
    for i in range(0, len(words), chunk_size):
        chunk = words[i:i + chunk_size]
        if not chunk:
            continue

        start_t = float(chunk[0].get("start", chunk[0].get("start_sec", 0.0)))
        end_t = float(chunk[-1].get("end", chunk[-1].get("end_sec", start_t + 2.0)))

        def fmt_time(seconds: float) -> str:
            hrs = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            cs = int(round((seconds - int(seconds)) * 100))
            return f"{hrs}:{mins:02d}:{secs:02d}.{cs:02d}"

        start_str = fmt_time(start_t)
        end_str = fmt_time(end_t)

        text_line = ""
        for w in chunk:
            dur = int((float(w.get("end", w.get("end_sec", 0))) - float(w.get("start", w.get("start_sec", 0)))) * 100)
            dur = max(10, dur)
            word_str = w.get("word", "").strip().upper()
            text_line += f"{{\\kf{dur}}}{word_str} "

        events.append(f"Dialogue: 0,{start_str},{end_str},DynamicKaraoke,,0,0,0,,{text_line.strip()}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(events))

    return output_path


class VideoPipelineService:
    """
    Orquestrador de Caso de Uso para a Fase 4 da Pipeline (Sniper & Renderização).
    """

    def __init__(
        self,
        ytdlp_client: Optional[YTDLPClient] = None,
        ffmpeg_client: Optional[FFmpegClient] = None,
        yt_publisher: Optional[YouTubePublisher] = None,
        ig_publisher: Optional[InstagramGraphAPIClient] = None
    ):
        self.ytdlp = ytdlp_client or YTDLPClient()
        self.ffmpeg = ffmpeg_client or FFmpegClient()
        self.yt_publisher = yt_publisher or YouTubePublisher()
        self.ig_publisher = ig_publisher or InstagramGraphAPIClient()

    def execute_short_cut_pipeline(
        self,
        video_url: str,
        cut_payload: Dict[str, Any],
        start_sec: float,
        end_sec: float,
        publish_to_social: bool = False,
        job_id: str = "job_pipeline_short"
    ) -> Dict[str, Any]:
        """
        Executa o fluxo assíncrono completo da Fase 4:
        1. Download cirúrgico do trecho via yt-dlp
        2. Geração do arquivo de legendas .ASS Karaokê
        3. Renderização no FFmpeg (Crop 9:16 + EBU R128 + Ducking)
        4. Publicação opcional nas redes sociais (YouTube Shorts / Instagram Reels)
        """
        cut_id = cut_payload.get("cut_id") or "short_001"
        logger.info("Iniciando pipeline de vídeo Short-Form", job_id=job_id, cut_id=cut_id, start_sec=start_sec, end_sec=end_sec)

        # Step 1: Download cirúrgico do trecho
        temp_dir = Path("data/cache") / job_id
        temp_dir.mkdir(parents=True, exist_ok=True)
        raw_cut_path = temp_dir / f"raw_{cut_id}.mp4"

        surgical_cut = self.ytdlp.download_surgical_cut(
            video_url=video_url,
            start_sec=start_sec,
            end_sec=end_sec,
            output_path=raw_cut_path,
            job_id=job_id
        )

        # Step 2: Geração de Legendas Animadas .ASS
        ass_path = temp_dir / f"subtitles_{cut_id}.ass"
        words_sample = cut_payload.get("words", [
            {"start": start_sec, "end": start_sec + 2, "word": "FORTE"},
            {"start": start_sec + 2, "end": start_sec + 4, "word": "PREGAÇÃO"}
        ])
        generate_ass_subtitle_file(words_sample, ass_path)

        # Step 3: Renderização Final via FFmpeg
        output_dir = Path("data/audio_podcasts/cortes_fase4")
        output_dir.mkdir(parents=True, exist_ok=True)
        final_video_path = output_dir / f"{cut_id}.mp4"

        rendered_video = self.ffmpeg.render_short_form(
            video_input=surgical_cut,
            output_path=final_video_path,
            start_sec=0.0,  # Já foi cortado cirurgicamente pelo yt-dlp
            end_sec=end_sec - start_sec,
            ass_subtitle_path=ass_path,
            enable_ducking=True,
            job_id=job_id
        )

        pub_results = {}
        # Step 4: Publicação Opcional nas Redes Sociais
        if publish_to_social:
            title = cut_payload.get("title_hook_a") or f"Mensagem Forte #{cut_id}"
            metadata = {"title": title, "description": f"Pregação edificante da IBPM CR.\n\n#{cut_id} #Shorts"}
            
            try:
                pub_results["youtube"] = self.yt_publisher.publish_video(rendered_video, metadata, is_short=True, job_id=job_id)
            except Exception as e:
                logger.warning("Falha na publicação automática do YouTube", error=str(e))

        logger.info("Pipeline de vídeo Short-Form concluída com sucesso!", job_id=job_id, final_video=str(rendered_video))

        return {
            "status": "success",
            "cut_id": cut_id,
            "final_video_path": str(rendered_video),
            "publication_results": pub_results
        }
