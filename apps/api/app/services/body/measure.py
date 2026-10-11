"""
Body measurement and pose analysis service.

Extracts bodily proportions from full-body images using MediaPipe PoseLandmarker
with a segmentation mask. Measurements are taken from the subject mask itself,
not from a legacy mp.solutions fallback.
"""

import io
import json
from typing import Any, cast

import numpy as np
from PIL import Image

from app.core.crypto import decrypt_field, encrypt_field
from app.core.logging import get_logger

logger = get_logger("body.measure")


class VisualMeasurementError(ValueError):
    """Raised when visual body estimation fails validation."""


def encrypt_measurements(measurements: dict[str, Any]) -> bytes:
    """Encrypt raw measurements dict to bytes using envelope encryption."""
    payload = json.dumps(measurements)
    return encrypt_field(payload)


def decrypt_measurements(blob: bytes) -> dict[str, Any]:
    """Decrypt encrypted measurements blob to dict."""
    plaintext = decrypt_field(blob)
    return cast(dict[str, Any], json.loads(plaintext))


def _count_connected_components(mask: np.ndarray) -> int:
    """Count connected foreground components in a binary mask."""
    visited = np.zeros_like(mask, dtype=bool)
    count = 0
    height, width = mask.shape
    for y in range(height):
        for x in range(width):
            if not mask[y, x] or visited[y, x]:
                continue
            count += 1
            stack = [(y, x)]
            visited[y, x] = True
            while stack:
                cy, cx = stack.pop()
                for ny in range(max(0, cy - 1), min(height, cy + 2)):
                    for nx in range(max(0, cx - 1), min(width, cx + 2)):
                        if mask[ny, nx] and not visited[ny, nx]:
                            visited[ny, nx] = True
                            stack.append((ny, nx))
    return count


def _measure_band_width(mask: np.ndarray, center_y: int, band_fraction: float, prefer_min: bool) -> float:
    height = mask.shape[0]
    band = max(6, int(height * band_fraction))
    rows = range(max(0, center_y - band), min(height, center_y + band + 1))
    widths: list[int] = []

    for row in rows:
        indices = np.where(mask[row])[0]
        if indices.size:
            widths.append(int(indices[-1] - indices[0] + 1))

    if not widths:
        raise VisualMeasurementError("Low visibility: no clear subject mask detected in the body frame")

    if prefer_min:
        return float(min(widths))
    return float(max(widths))


def _validate_pose_and_mask(mask: np.ndarray, landmarks: dict[str, Any], width: int, height: int) -> None:
    """Reject cropped, side-view, multi-person, and low-visibility scenarios."""
    if mask.size == 0 or float(mask.mean()) < 0.02:
        raise VisualMeasurementError("Low visibility: the subject mask is too faint or fragmented")

    if _count_connected_components(mask) > 1:
        raise VisualMeasurementError("Multiple figures detected; ensure only one person is in frame")

    shoulder_left = landmarks.get("left_shoulder")
    shoulder_right = landmarks.get("right_shoulder")
    hip_left = landmarks.get("left_hip")
    hip_right = landmarks.get("right_hip")
    if not all([shoulder_left, shoulder_right, hip_left, hip_right]):
        raise VisualMeasurementError("Could not detect full-body pose landmarks in photo")

    for landmark in (shoulder_left, shoulder_right, hip_left, hip_right):
        if getattr(landmark, "visibility", 1.0) < 0.35:
            raise VisualMeasurementError("Low visibility: body landmarks are not sufficiently clear")

    shoulder_center_x = (shoulder_left.x + shoulder_right.x) / 2.0
    hip_center_x = (hip_left.x + hip_right.x) / 2.0
    if abs(shoulder_center_x - hip_center_x) > 0.18:
        raise VisualMeasurementError("Side-view detected; please use a front-facing full-body photo")

    shoulder_pair_width = abs(shoulder_left.x - shoulder_right.x)
    hip_pair_width = abs(hip_left.x - hip_right.x)
    if shoulder_pair_width < 0.05 or hip_pair_width < 0.05:
        raise VisualMeasurementError("Cropped or incomplete body detection; please include the full figure")

    shoulder_y = (shoulder_left.y + shoulder_right.y) / 2.0
    hip_y = (hip_left.y + hip_right.y) / 2.0
    if shoulder_y > 0.38 or hip_y < 0.28:
        raise VisualMeasurementError("Cropped or incomplete body detection; please include the full figure")

    if width < 120 or height < 180:
        raise VisualMeasurementError("Cropped or incomplete body detection; please include the full figure")


def _detect_pose_and_mask(image: Image.Image) -> tuple[np.ndarray, dict[str, Any]]:
    """Use MediaPipe PoseLandmarker plus segmentation to get a subject mask and key landmarks."""
    try:
        from mediapipe import Image as MpImage
        from mediapipe import ImageFormat
        from mediapipe.tasks.python.vision import ImageSegmenter, PoseLandmarker
    except Exception as exc:  # pragma: no cover - model dependency guard
        raise VisualMeasurementError(
            "MediaPipe PoseLandmarker is unavailable. Install mediapipe and the pose model assets to analyze body photos."
        ) from exc

    image_np = np.asarray(image.convert("RGB"))
    mp_image = MpImage(image_format=ImageFormat.SRGB, data=image_np)
    # The exact model asset path is environment-specific. We rely on the runtime-provided model bundle.
    try:
        pose_landmarker = PoseLandmarker.create_from_model_path("pose_landmarker.task")
    except Exception as exc:  # pragma: no cover - runtime external dependency
        raise VisualMeasurementError(
            "MediaPipe PoseLandmarker model asset is unavailable. Load a pose model before measuring body proportions."
        ) from exc

    try:
        segmenter = ImageSegmenter.create_from_model_path("selfie_segmenter.task")
    except Exception as exc:  # pragma: no cover - runtime external dependency
        raise VisualMeasurementError(
            "MediaPipe image segmentation model is unavailable. Add a segmentation model asset to run body analysis."
        ) from exc

    pose_result = pose_landmarker.detect(mp_image)
    if not pose_result or not pose_result.pose_landmarks:
        raise VisualMeasurementError("Could not detect full-body pose landmarks in photo")

    segmentation_result = segmenter.segment(mp_image)
    if not segmentation_result or not getattr(segmentation_result, "confidence_masks", None):
        raise VisualMeasurementError("Could not produce a body-segmentation mask for this image")

    mask = segmentation_result.confidence_masks[0].numpy_view()
    if mask.ndim == 3:
        mask = mask[:, :, 0]
    mask = mask > 0.5
    pose_landmarks = pose_result.pose_landmarks[0]

    landmarks: dict[str, Any] = {
        "left_shoulder": pose_landmarks[11],
        "right_shoulder": pose_landmarks[12],
        "left_hip": pose_landmarks[23],
        "right_hip": pose_landmarks[24],
    }
    return mask.astype(bool), landmarks


def estimate_proportions_from_image(image_bytes: bytes) -> dict[str, float]:
    """Estimate bodily proportions from a front-facing full-body image using a subject mask."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img = img.convert("RGB")
            width, height = img.size
            if height < width * 1.1:
                raise VisualMeasurementError("Full body not visible; please ensure head-to-toe frame in portrait orientation")

            mask, landmarks = _detect_pose_and_mask(img)
            _validate_pose_and_mask(mask, landmarks, width, height)

            shoulder_center_y = int(((landmarks["left_shoulder"].y + landmarks["right_shoulder"].y) / 2.0) * height)
            hip_center_y = int(((landmarks["left_hip"].y + landmarks["right_hip"].y) / 2.0) * height)
            waist_center_y = int((shoulder_center_y + hip_center_y) / 2.0)

            shoulder_width = _measure_band_width(mask, shoulder_center_y, band_fraction=0.08, prefer_min=False)
            hip_width = _measure_band_width(mask, hip_center_y, band_fraction=0.10, prefer_min=False)
            waist_width = _measure_band_width(mask, waist_center_y, band_fraction=0.05, prefer_min=True)

            if shoulder_width <= 0 or hip_width <= 0 or waist_width <= 0:
                raise VisualMeasurementError("Low visibility: could not estimate reliable shoulder, waist, and hip widths")

            return {
                "shoulder": round(float(shoulder_width), 1),
                "waist": round(float(waist_width), 1),
                "hip": round(float(hip_width), 1),
            }
    except (OSError, ValueError, TypeError) as exc:
        raise VisualMeasurementError("Could not decode body image; please upload a valid full-body photo") from exc
