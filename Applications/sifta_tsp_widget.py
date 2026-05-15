#!/usr/bin/env python3
"""Small Traveling Salesman demo widget.

Truth label: ``SIFTA_TSP_DEMO_V1``.

The widget keeps the manifest target real on fresh installs. It uses a
deterministic nearest-neighbour route and writes a receipt for each solve.
That is enough for the desktop app surface and for the singleton guard; larger
ACO / OR-Tools solvers can replace ``solve_nearest_neighbor`` behind the same
receipt boundary later.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import sys
import time
from pathlib import Path
from typing import Iterable, Optional

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_STATE = _REPO / ".sifta_state"
_LEDGER = _STATE / "tsp_receipts.jsonl"

TRUTH_LABEL = "SIFTA_TSP_DEMO_V1"


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def solve_nearest_neighbor(points: Iterable[tuple[float, float]]) -> dict:
    pts = list(points)
    if not pts:
        return {"route": [], "distance": 0.0, "solver": "nearest_neighbor"}
    remaining = set(range(1, len(pts)))
    route = [0]
    while remaining:
        cur = route[-1]
        nxt = min(remaining, key=lambda i: (_dist(pts[cur], pts[i]), i))
        route.append(nxt)
        remaining.remove(nxt)
    total = sum(_dist(pts[a], pts[b]) for a, b in zip(route, route[1:]))
    if len(route) > 1:
        total += _dist(pts[route[-1]], pts[route[0]])
    return {
        "route": route,
        "distance": round(total, 4),
        "solver": "nearest_neighbor",
    }


def write_receipt(receipt: dict) -> dict:
    row = dict(receipt)
    row.setdefault("ts", time.time())
    row.setdefault("truth_label", TRUTH_LABEL)
    payload = json.dumps(row, sort_keys=True, separators=(",", ":"), default=str)
    row["sha256"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    _STATE.mkdir(parents=True, exist_ok=True)
    with _LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")
    return row


class _TSPCanvas(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.points: list[tuple[float, float]] = []
        self.route: list[int] = []
        self.setMinimumHeight(320)

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(11, 14, 24))
        if not self.points:
            return

        w = max(1, self.width())
        h = max(1, self.height())

        def map_point(p: tuple[float, float]) -> QPointF:
            return QPointF(30 + p[0] * (w - 60), 30 + p[1] * (h - 60))

        if len(self.route) > 1:
            painter.setPen(QPen(QColor(255, 210, 63), 3))
            ordered = self.route + [self.route[0]]
            for a, b in zip(ordered, ordered[1:]):
                painter.drawLine(map_point(self.points[a]), map_point(self.points[b]))

        painter.setPen(QPen(QColor(0, 255, 200), 2))
        painter.setBrush(QColor(0, 187, 249))
        for idx, p in enumerate(self.points):
            q = map_point(p)
            painter.drawEllipse(q, 6, 6)
            painter.drawText(q + QPointF(8, -8), str(idx + 1))


class TSPWidget(QWidget):
    _live_instance: Optional["TSPWidget"] = None
    _initialized_instance_ids: set[int] = set()

    def __new__(cls, *args, **kwargs):
        existing = cls._live_instance
        if existing is not None:
            try:
                _ = existing.isVisible()
                existing.show()
                existing.raise_()
                existing.activateWindow()
                return existing
            except RuntimeError:
                cls._live_instance = None
        return super().__new__(cls)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        if id(self) in type(self)._initialized_instance_ids:
            return
        super().__init__(parent)
        self.setWindowTitle("SIFTA — Traveling Salesman")
        self.resize(720, 560)
        self.setStyleSheet(
            "QWidget { background: #0b0e18; color: #e8edff; font-family: Menlo; }"
            "QPushButton, QSpinBox { background: #1b2340; color: #e8edff; "
            "border: 1px solid #41507d; border-radius: 6px; padding: 6px; }"
            "QPushButton:hover { border-color: #00ffc8; }"
        )

        self._rng = random.Random(42)
        self._points: list[tuple[float, float]] = []
        self._route: list[int] = []

        title = QLabel("Traveling Salesman")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: 800; color: #FFD23F;")
        self._status = QLabel("Ready.")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setWordWrap(True)

        self._count = QSpinBox(self)
        self._count.setRange(3, 30)
        self._count.setValue(12)
        self._canvas = _TSPCanvas(self)

        solve_btn = QPushButton("Solve")
        solve_btn.clicked.connect(self._solve)
        reshuffle_btn = QPushButton("New Map")
        reshuffle_btn.clicked.connect(self._new_map)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Cities"))
        controls.addWidget(self._count)
        controls.addWidget(reshuffle_btn)
        controls.addWidget(solve_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addLayout(controls)
        layout.addWidget(self._canvas, 1)
        layout.addWidget(self._status)

        self._new_map()
        type(self)._live_instance = self
        type(self)._initialized_instance_ids.add(id(self))

    def _new_map(self) -> None:
        n = int(self._count.value())
        self._points = [(self._rng.random(), self._rng.random()) for _ in range(n)]
        self._route = []
        self._canvas.points = self._points
        self._canvas.route = self._route
        self._canvas.update()
        self._status.setText(f"Generated {n} cities. Receipt will be written on solve.")

    def _solve(self) -> None:
        result = solve_nearest_neighbor(self._points)
        self._route = list(result["route"])
        self._canvas.route = self._route
        self._canvas.update()
        receipt = write_receipt({
            "event": "TSP_SOLVE",
            "solver": result["solver"],
            "city_count": len(self._points),
            "route": self._route,
            "distance": result["distance"],
        })
        self._status.setText(
            f"{result['solver']} distance {result['distance']:.2f}; "
            f"receipt {receipt['sha256'][:12]}..."
        )

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API
        type(self)._live_instance = None
        type(self)._initialized_instance_ids.discard(id(self))
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = TSPWidget()
    w.show()
    sys.exit(app.exec())
