#!/usr/bin/env python3
"""Receipt-backed camera proof summary for Alice's unified eye.

Truth label: ``SIFTA_CAMERA_UNIFIED_FIELD_PROOF_V1``.

This module does not open a camera and does not claim recognition from vibes.
It only summarizes existing ledgers:

* ``visual_stigmergy.jsonl`` for photon/math rows.
* ``active_eye_identity_frames.jsonl`` for frame identity receipts.
* ``face_detection_events.jsonl`` for face detector rows.
* ``kernel_process_table.json`` for organ health hints.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

_REPO = Path(__file__).resolve().parent.parent
_STATE = _REPO / ".sifta_state"
_LEDGER = "camera_unified_field_proof.jsonl"

TRUTH_LABEL = "SIFTA_CAMERA_UNIFIED_FIELD_PROOF_V1"
FRESH_S = 12.0


@dataclass(frozen=True)
class CameraUnifiedFieldProof:
    truth_label: str
    ok: bool
    status: str
    summary: str
    receipt_id: str
    device: str = ""
    frame_sha8: str = ""
    face_age_s: Optional[float] = None
    frame_age_s: Optional[float] = None
    visual_age_s: Optional[float] = None
    vision_health: str = "unknown"

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def _latest_jsonl(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = path.read_bytes()
    except OSError:
        return {}
    for raw in data.splitlines()[-200:][::-1]:
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw.decode("utf-8", errors="replace"))
        except Exception:
            continue
        if isinstance(obj, dict):
            return obj
    return {}


def _latest_json(path: Path) -> dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def _age(row: dict[str, Any], now: float) -> Optional[float]:
    for key in ("ts", "timestamp", "time"):
        try:
            return round(max(0.0, now - float(row.get(key))), 3)
        except Exception:
            pass
    return None


def _fresh(age: Optional[float]) -> bool:
    return age is not None and age <= FRESH_S


def _frame_sha8(state_dir: Path, frame_row: dict[str, Any], visual_row: dict[str, Any]) -> str:
    for row in (frame_row, visual_row):
        for key in ("frame_sha256", "sha256", "frame_hash", "image_sha256"):
            val = str(row.get(key) or "").strip()
            if len(val) >= 8:
                return val[:8]
    frame = state_dir / "visual_stigmergy_last_frame.jpg"
    if frame.exists():
        try:
            return hashlib.sha256(frame.read_bytes()).hexdigest()[:8]
        except OSError:
            return ""
    return ""


def _device(*rows: dict[str, Any]) -> str:
    for row in rows:
        for key in ("device", "device_label", "camera_label", "source", "camera"):
            val = str(row.get(key) or "").strip()
            if val:
                return val[:80]
    return ""


def _vision_health(face_row: dict[str, Any], visual_row: dict[str, Any], kpt: dict[str, Any]) -> str:
    for row in (face_row, visual_row):
        if row.get("error"):
            return f"error:{str(row.get('error'))[:48]}"
        if row.get("status"):
            return str(row.get("status"))[:64]
        if row.get("truth"):
            return str(row.get("truth"))[:64]
    if kpt:
        return "kernel_process_table_present"
    return "no_health_receipts"


def build_camera_unified_field_proof(
    state_dir: str | Path | None = None,
    *,
    write_receipt: bool = False,
) -> CameraUnifiedFieldProof:
    state = Path(state_dir) if state_dir is not None else _STATE
    now = time.time()

    visual = _latest_jsonl(state / "visual_stigmergy.jsonl")
    frame = _latest_jsonl(state / "active_eye_identity_frames.jsonl")
    face = _latest_jsonl(state / "face_detection_events.jsonl")
    kpt = _latest_json(state / "kernel_process_table.json")

    visual_age = _age(visual, now)
    frame_age = _age(frame, now)
    face_age = _age(face, now)
    has_fresh = any(_fresh(a) for a in (visual_age, frame_age, face_age))

    face_count = 0
    for key in ("faces_detected", "face_count", "faces"):
        try:
            val = face.get(key)
            face_count = len(val) if isinstance(val, list) else int(val)
            break
        except Exception:
            pass

    owner_match = bool(
        face.get("owner_match")
        or face.get("owner_recognized")
        or face.get("identity") == "owner"
    )
    if owner_match and _fresh(face_age):
        status = "OWNER_RECOGNIZED"
    elif face_count > 0 and _fresh(face_age):
        status = "FACE_DETECTED"
    elif has_fresh:
        status = "VISION_RECEIPTS_FRESH"
    else:
        status = "NO_FRESH_RECEIPTS"

    receipt_id = str(uuid.uuid4())
    parts = [status.lower().replace("_", " ")]
    if visual_age is not None:
        parts.append(f"visual={visual_age:.1f}s")
    if face_age is not None:
        parts.append(f"face={face_age:.1f}s")
    if frame_age is not None:
        parts.append(f"frame={frame_age:.1f}s")
    if len(parts) == 1:
        parts.append("waiting for eye ledgers")

    proof = CameraUnifiedFieldProof(
        truth_label=TRUTH_LABEL,
        ok=has_fresh,
        status=status,
        summary="eye proof: " + " · ".join(parts),
        receipt_id=receipt_id,
        device=_device(visual, frame, face),
        frame_sha8=_frame_sha8(state, frame, visual),
        face_age_s=face_age,
        frame_age_s=frame_age,
        visual_age_s=visual_age,
        vision_health=_vision_health(face, visual, kpt),
    )

    if write_receipt:
        state.mkdir(parents=True, exist_ok=True)
        with (state / _LEDGER).open("a", encoding="utf-8") as f:
            f.write(json.dumps(proof.to_json(), sort_keys=True) + "\n")

    return proof


__all__ = [
    "CameraUnifiedFieldProof",
    "TRUTH_LABEL",
    "build_camera_unified_field_proof",
]
