"""
TypedDict Schemas para o Diretor de Arte Algorítmico - Fase 2 Mineração (IBPM CR).

Define contratos estritos para todas as diretrizes de edição de vídeo, tipografia,
áudio/sonoplastia, análise teológica, SEO/redes sociais e hooks de retenção.
"""

from typing import TypedDict, List, Dict, Any, Optional


class VisualDirectives(TypedDict):
    """Instruções de câmera, B-Rolls, enquadramento e efeitos visuais."""
    camera_movement: str  # ex: "Auto-Zoom In", "Auto-Zoom Out (Slow)", "Ken Burns", "Normal"
    shake_effect_at: List[float]  # Segundos dos picos RMS (>0.85) com tremor de 0.5s
    broll_inserts: List[Dict[str, Any]]  # [{timestamp_sec, pexels_query, category, word}]
    black_screen_at: List[Dict[str, float]]  # [{start_sec, end_sec}] para silêncios > 2s
    blur_hook_sec: float  # 3.0 para desfoque inicial (obrigar a ler legenda)
    drop_marker_ms: Optional[int]  # Timestamp exato em ms do ponto de clímax
    ken_burns_spans: List[Dict[str, Any]]  # [{start_sec, end_sec}] panorâmica leve em trechos longos
    crop_9_16_tracking: Dict[str, Any]  # Metadado de enquadramento central (face tracking)
    progress_bar: Dict[str, Any]  # {position: "bottom", duration_sec: float, visible: bool}
    safe_zones: Dict[str, Any]  # {top_pct: 15, bottom_pct: 20, logo_safe: bool}
    broll_loop_mode: Optional[str]  # "lofi_relaxing" para trechos com WPM lento
    visual_countdown: bool  # countdown=True nos primeiros 3s se corte muito forte


class TypographyDirectives(TypedDict):
    """Instruções tipográficas, legendas .ASS, destaques teológicos e emojis."""
    highlight_words: List[Dict[str, str]]  # [{word: str, color: "#FFD700" | "#FF3333"}]
    kinetic_style: str  # "Word-by-Word", "Typewriter", "Standard"
    sticky_quote: str  # Frase da promessa central fixa no topo do Shorts
    emoji_inserts: List[Dict[str, Any]]  # [{word: str, emoji: str, sentiment: str}]
    caps_lock_spans: List[Dict[str, Any]]  # [{start_sec, end_sec, text: str}] picos RMS em maiúsculas
    dynamic_font_spans: List[Dict[str, Any]]  # [{text: str, font_family: "Cinzel"|"Montserrat"}]
    typewriter_spans: List[Dict[str, Any]]  # [{start_sec, end_sec, text: str}] frases reflexivas
    word_by_word_ass_events: List[Dict[str, Any]]  # Eventos de legenda pulando palavra a palavra
    imperative_wiggle_words: List[str]  # Verbos no imperativo ("Levante", "Receba") para wiggle
    contextual_subtitles: Optional[str]  # Nome do livro bíblico citado (ex: "Efésios 2") no canto
    cleaned_caption_text: str  # Texto limpo sem vícios ("né", "hã", "então") para leitura elegante


class AudioDirectives(TypedDict):
    """Instruções de sonoplastia, BGM, sidechain ducking e equalização."""
    sfx_inserts: List[Dict[str, Any]]  # [{timestamp_sec, sfx_type: "whoosh"|"riser"|"boom"}]
    bgm_mood: str  # "piano/cinematic", "epic/orchestral", "worship/ambient"
    ducking_points: List[Dict[str, Any]]  # [{start_sec, end_sec, factor: float}] quando WPM é alto
    audio_drop_ms: Optional[int]  # Timestamp do drop em ms
    sfx_whoosh_timestamps: List[float]  # Transições de assunto via TextRank
    sfx_riser_timestamp: Optional[float]  # 5s antes do clímax máximo
    sfx_boom_timestamp: Optional[float]  # Primeira palavra do Hook emocional
    bpm_suggestion: int  # 120 para WPM rápido, 80 para WPM lento
    equalizer_preset: str  # "attenuate_treble" se houver clipping, senão "flat"
    fade_out_sec: float  # 1.5s de fade-out no final
    crowd_swell_spans: List[Dict[str, Any]]  # [{start_sec, end_sec}] aplausos/reações da congregação


class TheologicalAnalysis(TypedDict):
    """Análise teológica profunda, exegese, perfil e detecções doutrinárias."""
    sermon_profile: str  # "Exortação", "Ensino", "Consolo", "Testemunho", "Batalha Espiritual"
    is_exegese: bool  # True se densidade de citações bíblicas for alta
    central_promise: str  # Frase curta com verbos no futuro ("Deus vai...", "Você verá...")
    call_to_action: Optional[str]  # Tag se encontrar verbos de convite ("Venha", "Aceite")
    problem_solution: Dict[str, str]  # {problem: str, solution: str} (dor no início, cura no fim)
    divine_density_score: int  # Ocorrências de "Deus", "Jesus", "Espírito", etc.
    one_liner_summary: str  # "Moral da História" extraída via TextRank
    bible_cross_references: List[Dict[str, str]]  # [{term: str, cross_ref: str}] ex: Davi -> 1 Samuel
    heresy_flag: bool  # True se frases violarem doutrina pentecostal
    prophecy_marker: bool  # True se contiver "Deus mandou te dizer" (Altamente Viral)


class SEOMetadata(TypedDict):
    """Metadados de SEO, títulos otimizados, hashtags e cópias de redes sociais."""
    titles: List[str]  # As 3 variações de título
    hashtags: List[str]  # #IBPMCR #Pregação + 3 hashtags do TextRank
    youtube_chapters: List[Dict[str, Any]]  # Marcadores 00:00 para vídeos 16:9
    tiktok_keywords: List[str]  # Palavras-chave separadas por vírgula
    curiosity_title: str  # Título focado em curiosidade
    theological_title: str  # Título focado em exposição bíblica
    emotional_title: str  # Título focado em identificação emocional
    description: str  # Descrição completa do YouTube Shorts
    pinned_comment: str  # Pergunta gerada para forçar engajamento
    thumbnail_copy: str  # Texto de no máximo 4 palavras para capa
    instagram_post: str  # Adaptação para artigo curto no Instagram com emojis


class RetentionHooks(TypedDict):
    """Gatilhos de retenção, cold open, seamless loop e gamificação."""
    cold_open_text: str  # Frase mais dramática colocada nos primeiros 3s
    seamless_loop: bool  # True se última frase se conecta com a primeira
    cta_popup_at: float  # Timestamp (ex: duracao - 3.0) para "Siga a @ibpmcr7976"
    story_poll: Dict[str, str]  # {question: str, option_a: str, option_b: str}
    share_trigger: Optional[str]  # "Envie para alguém que precisa" se Consolo
    pattern_break_timestamps: List[float]  # Momentos onde WPM zera e sobe subitamente
    bible_quiz: Optional[Dict[str, Any]]  # Quiz de múltipla escolha se aula doutrinária
    part_separator_tag: Optional[str]  # "Comente PARTE 2 para continuar" se corte longo
    controversy_flag: bool  # True se houver questionamentos retóricos
    easter_egg_logo_timestamps: List[float]  # Momentos para piscar a logo da igreja


class MasterCutRecord(TypedDict):
    """Registro mestre completo de um corte minerado contendo todas as diretrizes."""
    cut_id: str
    sermon_id: str
    tipo: str  # "Short (9:16)" | "Mid (16:9)"
    start_sec: float
    end_sec: float
    duration: float
    score: float
    title_hook_a: str
    title_hook_b: str
    start_anchor_7_words: str
    end_anchor_7_words: str
    text_snippet: str
    visual_directives: VisualDirectives
    typography_directives: TypographyDirectives
    audio_directives: AudioDirectives
    theological_analysis: TheologicalAnalysis
    seo_metadata: SEOMetadata
    retention_hooks: RetentionHooks
