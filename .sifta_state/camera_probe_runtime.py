import pathlib
import sys
import threading
import time

sys.path.insert(0, "/Users/computer/Documents/GitHub/ANTON-SIFTA/.venv/lib/python3.12/site-packages")

out = pathlib.Path("/tmp/sifta_python_runtime_camera_probe.txt")

import AVFoundation

VIDEO = AVFoundation.AVMediaTypeVideo
names = {0: "notDetermined", 1: "restricted", 2: "denied", 3: "authorized"}


def write(line: str) -> None:
    with out.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


before = int(AVFoundation.AVCaptureDevice.authorizationStatusForMediaType_(VIDEO))
write(f"before={names.get(before, before)}")

if before == 0:
    ev = threading.Event()

    def cb(ok):
        write(f"prompt_result={bool(ok)}")
        ev.set()

    AVFoundation.AVCaptureDevice.requestAccessForMediaType_completionHandler_(VIDEO, cb)
    ev.wait(60)

time.sleep(1)
after = int(AVFoundation.AVCaptureDevice.authorizationStatusForMediaType_(VIDEO))
write(f"after={names.get(after, after)}")
