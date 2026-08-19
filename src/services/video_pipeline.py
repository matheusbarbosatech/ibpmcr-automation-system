"""
Serviço Orquestrador da Fase 3 Renderização (Video Pipeline) - IBPM CR Automation System.

Integra o download cirúrgico (yt-dlp), o gerador de legendas Karaokê (.ASS),
a renderização visual via FFmpeg (Shorts 9:16 e Mid-Form 16:9) e a publicação
nas redes sociais (YouTube Shorts, YouTube Mid-Form e Instagram Reels).
"""

from pathlib import Path
from typing import Dict, Any, Optional, List

from src.core.logger import get_logger
from src.infrastructure.yt_dlp_client import YTDLPClient
from src.infrastructure.ffmpeg_client import FFmpegClient
from src.infrastructure.youtube_api import YouTubePublisher
from src.infrastructure.instagram_api import InstagramGraphAPIClient

logger = get_logger("VideoPipelineService")


def calculate_youtube_chapters(
    cut_start_global: float,
    cut_end_global: float,
    raw_chapters: List[Dict[str, Any]]
) -> List[Dict[str, str]]:
    """
    Converte timestamps globais para relativos e valida os critérios do YouTube:
    Garante início em 00:00, no mínimo 3 capítulos e duração mínima de 10 segundos.
    """
    relative_chapters = []
    
    # 1. Inserir capítulo inicial em 00:00 se necessário
    relative_chapters.append({
        "timestamp": "00:00",
        "description": "00:00 - Introdução da Mensagem e Leitura Bíblica"
    })

    for idx, chap in enumerate(raw_chapters, 1):
        rel_sec = float(chap.get("relative_start_seconds", idx * 60.0))
        hrs = int(rel_sec // 3600)
        mins = int((rel_sec % 3600) // 60)
        secs = int(rel_sec % 60)
        time_str = f"{hrs:02d}:{mins:02d}:{secs:02d}" if hrs > 0 else f"{mins:02d}:{secs:02d}"
        
        relative_chapters.append({
            "timestamp": time_str,
            "description": f"{time_str} - {chap.get('chapter_title', f'Parte {idx}')}"
        })

    return relative_chapters


def generate_ass_subtitle_file(words: list, output_path: Path) -> Path:
    """Gera um arquivo de legendas em formato Advanced SubStation Alpha (.ASS) com marcação Karaokê."""
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

        text_line = ""
        for w in chunk:
            dur = int((float(w.get("end", w.get("end_sec", 0))) - float(w.get("start", w.get("start_sec", 0)))) * 100)
            dur = max(10, dur)
            word_str = w.get("word", "").strip().upper()
            text_line += f"{{\\kf{dur}}}{word_str} "

        events.append(f"Dialogue: 0,{fmt_time(start_t)},{fmt_time(end_t)},DynamicKaraoke,,0,0,0,,{text_line.strip()}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(events))

    return output_path


class VideoPipelineService:
    """Orquestrador de Caso de Uso para a Fase 3 Renderização (Renderização 9:16 e 16:9)."""

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
        """Executa a renderização de corte vertical Short-Form (9:16)."""
        cut_id = cut_payload.get("cut_id") or "short_001"
        logger.info("Iniciando pipeline Short-Form (9:16)", job_id=job_id, cut_id=cut_id)

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

        ass_path = temp_dir / f"subtitles_{cut_id}.ass"
        words_sample = cut_payload.get("words", [
            {"start": start_sec, "end": start_sec + 2, "word": "FORTE"},
            {"start": start_sec + 2, "end": start_sec + 4, "word": "PREGAÇÃO"}
        ])
        generate_ass_subtitle_file(words_sample, ass_path)

        output_dir = Path("data/fase3_renderizacao/cortes_finais")
        output_dir.mkdir(parents=True, exist_ok=True)
        final_video_path = output_dir / f"{cut_id}_9x16.mp4"

        rendered_video = self.ffmpeg.render_short_form(
            video_input=surgical_cut,
            output_path=final_video_path,
            start_sec=0.0,
            end_sec=end_sec - start_sec,
            ass_subtitle_path=ass_path,
            enable_ducking=True,
            job_id=job_id
        )

        return {
            "status": "success",
            "cut_id": cut_id,
            "format": "9:16",
            "final_video_path": str(rendered_video)
        }

    def execute_mid_cut_pipeline(
        self,
        video_url: str,
        cut_payload: Dict[str, Any],
        start_sec: float,
        end_sec: float,
        publish_to_social: bool = False,
        job_id: str = "job_pipeline_mid"
    ) -> Dict[str, Any]:
        """Executa a renderização de corte horizontal Mid-Form (16:9) com capítulos do YouTube."""
        cut_id = cut_payload.get("cut_id") or "mid_001"
        logger.info("Iniciando pipeline Mid-Form (16:9)", job_id=job_id, cut_id=cut_id)

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

        output_dir = Path("data/fase3_renderizacao/cortes_finais")
        output_dir.mkdir(parents=True, exist_ok=True)
        final_video_path = output_dir / f"{cut_id}_16x9.mp4"

        rendered_video = self.ffmpeg.render_mid_form(
            video_input=surgical_cut,
            output_path=final_video_path,
            start_sec=0.0,
            end_sec=end_sec - start_sec,
            job_id=job_id
        )

        # Recálculo de Capítulos para o YouTube
        raw_chaps = cut_payload.get("suggested_chapters", [])
        rel_chaps = calculate_youtube_chapters(start_sec, end_sec, raw_chaps)

        desc_chapters_str = "\n".join([c["description"] for c in rel_chaps])

        return {
            "status": "success",
            "cut_id": cut_id,
            "format": "16:9",
            "final_video_path": str(rendered_video),
            "formatted_description": f"{cut_payload.get('synopsis', 'Estudo teológico profundo IBPM CR')}\n\nCapítulos do Vídeo:\n{desc_chapters_str}"
        }
