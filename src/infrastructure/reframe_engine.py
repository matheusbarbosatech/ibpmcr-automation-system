"""
Motor de Visão Computacional e Reframe Inteligente 9:16 - IBPM CR Automation System.

Implementa o algoritmo de rastreamento facial do pregador com filtro de Média Móvel
Exponencial (EMA) e Zona Morta de Histerese (Deadband) para garantir movimentação cinematográfica
suave de câmera sem tremores em telas verticais (1080x1920).
"""

import os
import cv2
import numpy as np
from typing import Tuple, Optional

try:
    # pyrefly: ignore [missing-import]
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
        self.cv2_cascade = None

        if HAS_MEDIAPIPE:
            try:
                self.mp_face_detection = mp.solutions.face_detection
                self.face_detector = self.mp_face_detection.FaceDetection(
                    model_selection=1,  # Modelo otimizado para rostos a média distância (palco)
                    min_detection_confidence=0.5
                )
                logger.info("Detector Facial MediaPipe inicializado com sucesso.")
            except Exception as e:
                logger.warning("Falha ao inicializar MediaPipe. Tentando fallback OpenCV HaarCascade.", error=str(e))

        if not self.face_detector:
            try:
                cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                if os.path.exists(cascade_path):
                    self.cv2_cascade = cv2.CascadeClassifier(cascade_path)
                    logger.info("Detector Facial OpenCV HaarCascade inicializado como fallback.")
            except Exception as e:
                logger.warning(f"Não foi possível carregar o detector HaarCascade: {e}")

    def process_frame(self, frame: np.ndarray) -> Tuple[int, int, int, int]:
        """
        Processa um frame individual e retorna as coordenadas de crop (left, top, crop_w, crop_h).
        """
        img_h, img_w, _ = frame.shape
        crop_w = int(img_h * (self.target_w / self.target_h))
        crop_h = img_h

        face_center_x = img_w // 2  # Padrão: centro do vídeo

        # 1. Rastreamento Facial via MediaPipe
        if self.face_detector:
            try:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.face_detector.process(rgb_frame)

                if results and results.detections:
                    best_detection = results.detections[0]
                    if len(results.detections) > 1 and self.prev_center_x is not None:
                        # Seleciona o rosto mais próximo da posição anterior do pregador
                        min_dist = float('inf')
                        for det in results.detections:
                            b = det.location_data.relative_bounding_box
                            cx = int((b.xmin + b.width / 2.0) * img_w)
                            dist = abs(cx - self.prev_center_x)
                            if dist < min_dist:
                                min_dist = dist
                                best_detection = det

                    bbox = best_detection.location_data.relative_bounding_box
                    face_center_x = int((bbox.xmin + bbox.width / 2.0) * img_w)
            except Exception:
                pass

        # 2. Fallback via OpenCV HaarCascade
        elif self.cv2_cascade:
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.cv2_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
                if len(faces) > 0:
                    best_face = faces[0]
                    if len(faces) > 1 and self.prev_center_x is not None:
                        min_dist = float('inf')
                        for f_cand in faces:
                            cx = f_cand[0] + (f_cand[2] // 2)
                            dist = abs(cx - self.prev_center_x)
                            if dist < min_dist:
                                min_dist = dist
                                best_face = f_cand

                    (fx, fy, fw, fh) = best_face
                    face_center_x = fx + (fw // 2)
            except Exception:
                pass

        # Aplicação da Zona Morta (Deadband) e Média Móvel Exponencial (EMA)
        if self.prev_center_x is None:
            smooth_x = face_center_x
        else:
            delta = face_center_x - self.prev_center_x
            if abs(delta) < self.deadband_px:
                smooth_x = self.prev_center_x
            else:
                smooth_x = int(self.alpha * face_center_x + (1.0 - self.alpha) * self.prev_center_x)

        self.prev_center_x = smooth_x

        # Limites laterais do canvas
        left = smooth_x - (crop_w // 2)
        left = max(0, min(left, img_w - crop_w))
        top = 0

        return (left, top, crop_w, crop_h)

    def analyze_video_smart_crop(self, video_path: str, start_sec: float, duration_sec: float, sample_fps: int = 2) -> str:
        """
        Amostra o vídeo durante o intervalo do corte e calcula a posição X ideal de enquadramento.
        Retorna a expressão de crop do FFmpeg `crop=w:h:x:y`.
        """
        if not os.path.exists(video_path):
            return "crop=ih*(9/16):ih:(iw-ow)/2:0"

        # Reseta o centro anterior para a nova amostragem
        self.prev_center_x = None

        cap = None
        try:
            cap = cv2.VideoCapture(str(video_path))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            start_frame = int(start_sec * fps)
            end_frame = min(total_frames, int((start_sec + duration_sec) * fps))

            step = max(1, int(fps / sample_fps))
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

            x_positions = []
            curr_frame = start_frame

            while curr_frame < end_frame:
                ret, frame = cap.read()
                if not ret:
                    break

                if (curr_frame - start_frame) % step == 0:
                    left, top, crop_w, crop_h = self.process_frame(frame)
                    x_positions.append(left)

                curr_frame += 1

            if x_positions:
                # Usa a mediana para ignorar movimentos espúrios ou falsos positivos
                optimal_x = int(np.median(x_positions))
                logger.info(f"Enquadramento Inteligente calculado: crop_x={optimal_x} para {video_path}")
                return f"crop=ih*(9/16):ih:{optimal_x}:0"

        except Exception as e:
            logger.warning(f"Erro na análise do Enquadramento Inteligente: {e}. Usando corte central.")

        finally:
            if cap is not None:
                cap.release()

        return "crop=ih*(9/16):ih:(iw-ow)/2:0"


