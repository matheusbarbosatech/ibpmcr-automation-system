"""
Esquemas Pydantic V2 e Tipos de Dados do Domínio - IBPM CR Automation System.

Define todos os contratos de dados estritamente tipados para a mineração teológica via LLM,
configurações de renderização tipográfica (.ASS), engenharia de áudio (Loudness/Ducking),
visão computacional (Auto-Reframe) e serialização de payloads para publicação em nuvem.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# ENUMS DE DOMÍNIO E NAVEGAÇÃO MULTIMÍDIA
# =============================================================================

class MomentCategory(str, Enum):
    """Categorias funcionais da retórica pentecostal e momentos virais."""
    HOOK_PATTERN_INTERRUPT = "hook_pattern_interrupt"
    EMOTIONAL_CLIMAX_PROPHETIC = "emotional_climax_prophetic"
    PRACTICAL_STORY_ILLUSTRATION = "practical_story_illustration"
    BIBLICAL_PRINCIPLE_REVELATION = "biblical_principle_revelation"


class FramingType(str, Enum):
    """Estratégias de enquadramento computacional e recomposição visual 9:16."""
    DYNAMIC_TRACKING = "dynamic_tracking"
    SPLIT_SCREEN_REACTION = "split_screen_reaction"
    LETTERBOX_16_9_PADDED = "letterbox_16_9_padded"
    CENTER_CROP_STATIC = "center_crop_static"


class EmotionCategory(str, Enum):
    """Emoção predominante do trecho para guia de design visual e paleta cromática."""
    AUTHORITY_FAITH = "authority_faith"
    COMPASSION_LOVE = "compassion_love"
    URGENCY_WARNING = "urgency_warning"
    JOY_CELEBRATION = "joy_celebration"
    SOLEMN_REVERENCE = "solemn_reverence"


class BrollIntensity(str, Enum):
    """Nível de densidade de inserções B-Roll/Imagens suplementares."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# =============================================================================
# MODELOS DE DESIGN, SONOPLASTIA E LEGENDAS ANIMADAS (.ASS)
# =============================================================================

class ColorPalette(BaseModel):
    """Paleta de cores em formato hexadecimal (BGR/RGB) para renderização no FFmpeg."""
    primary_text_hex: str = Field(
        default="#FFFFFF",
        description="Cor principal do texto das legendas em hexadecimal BGR/RGB."
    )
    highlight_word_hex: str = Field(
        default="#FFD700",
        description="Cor de destaque para a palavra ativa em estilo Karaokê."
    )
    stroke_color_hex: str = Field(
        default="#000000",
        description="Cor do contorno/outline das letras."
    )
    shadow_color_hex: str = Field(
        default="#00000088",
        description="Cor e transparência da sombra projetada."
    )


class SoundFxTag(BaseModel):
    """Efeito sonoro pontual sincronizado com o tempo do corte."""
    timestamp_offset_sec: float = Field(
        description="Segundo relativo ao início do corte em que o efeito sonoro deve ser executado."
    )
    sfx_type: str = Field(
        description="Identificador do efeito sonoro (ex: 'whoosh', 'cinematic_boom', 'riser', 'bell')."
    )
    volume_gain_db: float = Field(
        default=0.0,
        description="Ajuste de ganho de volume para o efeito sonoro em dB."
    )


class DynamicEmojiRule(BaseModel):
    """Mapeamento dinâmico de palavras gatilho para exibição de emojis nas legendas."""
    target_word: str = Field(description="Palavra gatilho presente na transcrição.")
    emoji_character: str = Field(description="Emoji unicode correspondente a ser exibido junto à palavra.")


class SubtitlesConfig(BaseModel):
    """Configuração completa para geração do arquivo de legendas .ASS."""
    palette: ColorPalette = Field(description="Paleta cromática derivada da emoção do trecho.")
    font_size: int = Field(default=48, description="Tamanho base da fonte tipográfica em pontos.")
    font_name: str = Field(default="Montserrat Black", description="Família tipográfica a ser utilizada.")
    emoji_rules: List[DynamicEmojiRule] = Field(
        default_factory=list,
        description="Mapeamento de palavra para emoji na renderização."
    )


class AudioTrackConfig(BaseModel):
    """Diretrizes de engenharia de áudio, trilha sonora e Auto-Ducking."""
    suggested_genre: str = Field(
        description="Gênero da trilha de fundo (ex: 'ambient_worship', 'cinematic_pad', 'dramatic_strings')."
    )
    suggested_bpm: int = Field(description="BPM sugerido para sincronização visual e ritmo de corte.")
    background_music_volume_db: float = Field(
        default=-22.0,
        description="Volume alvo da música de fundo em dB relativo à voz principal."
    )
    enable_auto_ducking: bool = Field(
        default=True,
        description="Ativa compressão sidechain na música de fundo conforme a voz principal."
    )
    sound_fx_list: List[SoundFxTag] = Field(
        default_factory=list,
        description="Lista de efeitos sonoros pontuais."
    )


# =============================================================================
# MODELOS DE MINERAÇÃO DE CORTES (SHORT-FORM 9:16 E MID-FORM 16:9)
# =============================================================================

class MinedCutPayload(BaseModel):
    """Payload completo de um corte vertical Short-Form (9:16)."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    cut_id: str = Field(description="Identificador único alfanumérico do corte (ex: 'short_001').")
    title_hook_a: str = Field(description="Título A focado em curiosidade e quebra de expectativa.")
    title_hook_b: str = Field(description="Título B focado em dor e identificação pessoal.")
    category: MomentCategory = Field(description="Categoria funcional do momento viral.")
    dominant_emotion: EmotionCategory = Field(description="Emoção predominante que guia o design visual.")
    start_anchor_7_words: str = Field(
        description="Exatamente as 7 primeiras palavras do trecho para alinhamento via Whisper."
    )
    end_anchor_7_words: str = Field(
        description="Exatamente as 7 últimas palavras do trecho para alinhamento via Whisper."
    )
    framing_suggested: FramingType = Field(
        default=FramingType.DYNAMIC_TRACKING,
        description="Estratégia visual de enquadramento 9:16."
    )
    broll_intensity: BrollIntensity = Field(
        default=BrollIntensity.NONE,
        description="Nível de densidade de B-rolls/imagens suplementares."
    )
    subtitles_config: SubtitlesConfig = Field(description="Instruções de renderização tipográfica.")
    audio_config: AudioTrackConfig = Field(description="Instruções de engenharia e sonoplastia de áudio.")


class SuggestedChapter(BaseModel):
    """Marcador de capítulo para a timeline do YouTube."""
    chapter_title: str = Field(description="Título descritivo do capítulo no YouTube.")
    relative_start_seconds: float = Field(description="Timestamp relativo em segundos para início do capítulo.")


class MidFormCutPayload(BaseModel):
    """Payload de um corte horizontal Mid-Form (16:9) para o YouTube."""
    cut_id: str = Field(description="Identificador único alfanumérico do corte horizontal.")
    title: str = Field(description="Título otimizado para busca e CTR no YouTube.")
    synopsis: str = Field(description="Sinopse expositiva rica em palavras-chave.")
    start_anchor_7_words: str = Field(description="Exatamente as 7 primeiras palavras literais do trecho.")
    end_anchor_7_words: str = Field(description="Exatamente as 7 últimas palavras literais do trecho.")
    suggested_chapters: List[SuggestedChapter] = Field(
        default_factory=list,
        description="Lista de capítulos para barra de reprodução do YouTube."
    )


class SermonMiningResponse(BaseModel):
    """Resposta consolidada da mineração teológica do culto via Gemini API."""
    job_id: str = Field(default="", description="Identificador único do trabalho.")
    source_video_id: str = Field(description="ID do vídeo do YouTube de origem.")
    total_cuts_found: int = Field(description="Quantidade total de cortes validados extraídos.")
    short_form_cuts: List[MinedCutPayload] = Field(
        default_factory=list,
        description="Lista de cortes verticais (Short-Form 9:16)."
    )
    mid_form_cuts: List[MidFormCutPayload] = Field(
        default_factory=list,
        description="Lista de cortes horizontais (Mid-Form 16:9)."
    )
