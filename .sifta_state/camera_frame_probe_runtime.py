import pathlib
import sys

sys.path.insert(0, "/Users/computer/Documents/GitHub/ANTON-SIFTA/.venv/lib/python3.12/site-packages")

out = pathlib.Path("/tmp/sifta_python_runtime_frame_probe.txt")

from PyQt6.QtCore import QCoreApplication, QTimer
from PyQt6.QtMultimedia import QCamera, QMediaCaptureSession, QMediaDevices, QVideoSink


def write(line: str) -> None:
    with out.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


app = QCoreApplication([])
devs = QMediaDevices.videoInputs()
write(f"video_inputs={len(devs)}")
for dev in devs:
    write(f"device={dev.description()}")
if not devs:
    raise SystemExit(3)

cam = QCamera(devs[0])
session = QMediaCaptureSession()
sink = QVideoSink()
session.setCamera(cam)
session.setVideoSink(sink)
state = {"frames": 0}


def on_frame(frame):
    state["frames"] += 1
    write("frame_received=YES")
    write(f"frame_valid={frame.isValid()}")
    cam.stop()
    app.quit()


def on_error(error, error_string):
    write(f"camera_error={error_string}")
    cam.stop()
    app.quit()


sink.videoFrameChanged.connect(on_frame)
cam.errorOccurred.connect(on_error)
QTimer.singleShot(8000, app.quit)
cam.start()
app.exec()
write(f"frames={state['frames']}")
raise SystemExit(0 if state["frames"] else 2)
