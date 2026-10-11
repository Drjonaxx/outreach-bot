"""Face tracking and 16:9 -> 9:16 reframing plans."""

from __future__ import annotations

import json
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path

OUT_W, OUT_H = 1080, 1920

YUNET_URLS = [
    "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
]
MODEL_PATH = Path.home() / ".cache" / "clipper" / "face_detection_yunet_2023mar.onnx"


@dataclass
class VideoInfo:
    width: int
    height: int
    fps: float
    duration: float


@dataclass
class Face:
    cx: float
    cy: float
    w: float
    h: float

    @property
    def area(self) -> float:
        return self.w * self.h


@dataclass
class CropPlan:
    mode: str  # "crop" follows a face; "fit" shows the whole frame over a blurred background
    crop_w: int
    keyframes: list[tuple[float, int]]  # (seconds from clip start, crop x)


def probe(path: str) -> VideoInfo:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate:format=duration",
         "-of", "json", path],
        check=True, capture_output=True, text=True,
    ).stdout
    data = json.loads(out)
    stream = data["streams"][0]
    num, den = stream["r_frame_rate"].split("/")
    return VideoInfo(
        int(stream["width"]), int(stream["height"]),
        float(num) / float(den or 1), float(data["format"]["duration"]),
    )


def _model_path() -> Path:
    if MODEL_PATH.exists() and MODEL_PATH.stat().st_size > 100_000:
        return MODEL_PATH
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    for url in YUNET_URLS:
        try:
            urllib.request.urlretrieve(url, MODEL_PATH)
        except OSError:
            continue
        if MODEL_PATH.stat().st_size > 100_000:  # not a Git LFS pointer or an error page
            return MODEL_PATH
    raise RuntimeError(f"No pude descargar el modelo de detección de caras en {MODEL_PATH}")


def detect_faces(path: str, start: float, end: float, sample_fps: float = 3.0) -> list[tuple[float, list[Face]]]:
    """Sample frames in [start, end) and return detected faces per sample time (relative to start)."""
    import cv2

    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.set(cv2.CAP_PROP_POS_MSEC, start * 1000)
    step = max(1, round(fps / sample_fps))
    total = int((end - start) * fps)

    detector = None
    scale = 1.0
    samples: list[tuple[float, list[Face]]] = []
    for i in range(total):
        if i % step:
            if not cap.grab():
                break
            continue
        ok, frame = cap.read()
        if not ok:
            break
        if detector is None:
            h, w = frame.shape[:2]
            scale = min(1.0, 640 / w)
            size = (int(w * scale), int(h * scale))
            detector = cv2.FaceDetectorYN.create(str(_model_path()), "", size, 0.7, 0.3, 50)
        small = cv2.resize(frame, None, fx=scale, fy=scale) if scale != 1.0 else frame
        _, found = detector.detect(small)
        faces = [
            Face((x + fw / 2) / scale, (y + fh / 2) / scale, fw / scale, fh / scale)
            for x, y, fw, fh, *_ in (found if found is not None else [])
        ]
        samples.append((i / fps, faces))
    cap.release()
    return samples


def plan_crop(
    samples: list[tuple[float, list[Face]]],
    info: VideoInfo,
    deadzone: float = 0.12,
    confirm: int = 2,
    min_hold: float = 1.0,
) -> CropPlan:
    """Turn face samples into a steady, cut-friendly crop path.

    Podcasts are mostly static shots with hard cuts between speakers, so the crop
    stays put until the target face leaves a dead zone for `confirm` samples in a
    row, then jumps (backdated to the first deviating sample).
    """
    crop_w = min(info.width, int(info.height * 9 / 16)) // 2 * 2
    max_x = info.width - crop_w
    center_x = max_x // 2

    if crop_w >= info.width or not samples:
        return CropPlan("crop", crop_w, [(0.0, center_x)])

    # Wide two-shot: two big faces further apart than the crop can show.
    wide = 0
    for _, faces in samples:
        if len(faces) >= 2:
            big = sorted(faces, key=lambda f: f.area, reverse=True)
            a, b = big[0], big[1]
            if b.area >= 0.5 * a.area and abs(a.cx - b.cx) + (a.w + b.w) / 2 > crop_w:
                wide += 1
    if wide > len(samples) / 2:
        return CropPlan("fit", crop_w, [(0.0, center_x)])

    # Pick a target face per sample: the largest, but stick with the previous
    # target when a comparable face sits near it.
    targets: list[tuple[float, float | None]] = []
    prev: float | None = None
    for t, faces in samples:
        if not faces:
            targets.append((t, None))
            continue
        largest = max(faces, key=lambda f: f.area)
        choice = largest
        if prev is not None:
            near = min(faces, key=lambda f: abs(f.cx - prev))
            if near.area >= 0.6 * largest.area and abs(near.cx - prev) < crop_w * 0.25:
                choice = near
        targets.append((t, choice.cx))
        prev = choice.cx

    def to_x(cx: float) -> int:
        return int(min(max(cx - crop_w / 2, 0), max_x)) // 2 * 2

    first = next((cx for _, cx in targets if cx is not None), None)
    if first is None:
        return CropPlan("crop", crop_w, [(0.0, center_x)])

    keyframes = [(0.0, to_x(first))]
    current = first
    pending_since: float | None = None
    pending_vals: list[float] = []
    for t, cx in targets:
        if cx is None or abs(cx - current) <= deadzone * crop_w:
            pending_since, pending_vals = None, []
            continue
        if pending_since is None:
            pending_since = t
        pending_vals.append(cx)
        if len(pending_vals) >= confirm:
            new = sorted(pending_vals)[len(pending_vals) // 2]
            x = to_x(new)
            if pending_since - keyframes[-1][0] < min_hold:
                # Too soon after the last jump: replace it instead of flickering.
                keyframes[-1] = (keyframes[-1][0], x)
            elif x != keyframes[-1][1]:
                keyframes.append((round(pending_since, 3), x))
            current = new
            pending_since, pending_vals = None, []

    # Collapse consecutive keyframes that ended up at the same x.
    merged = [keyframes[0]]
    for t, x in keyframes[1:]:
        if x != merged[-1][1]:
            merged.append((t, x))
    return CropPlan("crop", crop_w, merged)


def x_expression(keyframes: list[tuple[float, int]]) -> str:
    """Piecewise-constant ffmpeg expression for the crop x over time."""
    expr = str(keyframes[-1][1])
    for i in range(len(keyframes) - 2, -1, -1):
        expr = f"if(lt(t,{keyframes[i + 1][0]}),{keyframes[i][1]},{expr})"
    return expr


def video_filter(plan: CropPlan, info: VideoInfo) -> str:
    """Filter chain from [0:v] to a 1080x1920 stream labelled [base]."""
    if plan.mode == "fit":
        return (
            f"[0:v]split[bgsrc][fgsrc];"
            f"[bgsrc]scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase,"
            f"crop={OUT_W}:{OUT_H},gblur=sigma=40,eq=brightness=-0.08[bg];"
            f"[fgsrc]scale={OUT_W}:-2[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[base]"
        )
    x = x_expression(plan.keyframes)
    return (
        f"[0:v]crop={plan.crop_w}:{info.height}:'{x}':0,"
        f"scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase,"
        f"crop={OUT_W}:{OUT_H},setsar=1[base]"
    )
