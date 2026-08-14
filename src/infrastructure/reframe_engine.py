"""
Motor de Visão Computacional e Reframe Inteligente 9:16 - IBPM CR Automation System.

Implementa o algoritmo de rastreamento facial do pregador com filtro de Média Móvel
Exponencial (EMA) e Zona Morta de Histerese (Deadband) para garantir movimentação cinematográfica
suave de câmera sem tremores em telas verticais (1080x1920).
"""

import cv2
import numpy as np
from typing import Tuple, Optional

try:
    import mediapipe as mp
    HAS_MEDIAPIPE = True
except ImportError:
    HAS_MEDIAPIPE = False

from src.core.logger import get_logger

logger = get_logger("SmoothAutoReframe")


class SmoothAutoReframe:
    """
    Rastreia a posição do pregador no palco e calcula o enquadramento vertical 9:16.
    """

    def __init__(
        self,
        target_width: int = 1080,
        target_height: int = 1920,
        alpha: float = 0.10,
        deadband_px: int = 35
    ):
        self.target_w = target_width
        self.target_h = target_height
        self.alpha = alpha
        self.deadband_px = deadband_px
        self.prev_center_x: Optional[int] = None

        self.face_detector = None
        if HAS_MEDIAPIPE:
            try:
                self.mp_face_detection = mp.solutions.face_detection
                self.face_detector = self.mp_face_detection.FaceDetection(
                    model_selection=1,  # Modelo otimizado para rostos a média distância (palco)
                    min_detection_confidence=0.5
                )
                logger.info("Detector Facial MediaPipe inicializado com sucesso.")
            except Exception as e:
                logger.warning("Falha ao inicializar MediaPipe. Usando fallback de centro de tela.", error=str(e))

    def process_frame(self, frame: np.ndarray) -> Tuple[int, int, int, int]:
        """
        Processa um frame individual e retorna as coordenadas de crop (left, top, crop_w, crop_h).
        """
        img_h, img_w, _ = frame.shape
        crop_w = int(img_h * (self.target_w / self.target_h))
        crop_h = img_h

        face_center_x = img_w // 2  # Padrão: centro do vídeo

        # Rastreamento Facial via MediaPipe
        if self.face_detector:
            try:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.face_detector.process(rgb_frame)

                if results and results.detections:
                    detection = results.detections[0]
                    bbox = detection.location_data.relative_bounding_box
                    face_center_x = int((bbox.xmin + bbox.width / 2.0) * img_w)
            except Exception:
                pass

        # Aplicação da Zona Morta (Deadband) e Média Móvel Exponencial (EMA)
        if self.prev_center_x is None:
            smooth_x = face_center_x
        else:
            delta = face_center_x - self.prev_center_x
            if abs(delta) < self.deadband_px:
                # Mantém a câmera 100% estática dentro da zona morta
                smooth_x = self.prev_center_x
            else:
                # Amortecimento suave por Média Móvel Exponencial
                smooth_x = int(self.alpha * face_center_x + (1.0 - self.alpha) * self.prev_center_x)

        self.prev_center_x = smooth_x

        # Limites laterais do canvas
        left = smooth_x - (crop_w // 2)
        left = max(0, min(left, img_w - crop_w))
        top = 0

        return (left, top, crop_w, crop_h)
