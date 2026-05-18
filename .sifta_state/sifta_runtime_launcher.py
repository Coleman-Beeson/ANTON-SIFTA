import os
import pathlib
import runpy
import sys

repo = pathlib.Path("/Users/computer/Documents/GitHub/ANTON-SIFTA")
site = repo / ".venv/lib/python3.12/site-packages"

os.chdir(repo)
sys.path.insert(0, str(repo))
sys.path.insert(0, str(site))
os.environ["PYTHONPATH"] = f"{repo}:{os.environ.get('PYTHONPATH', '')}"
os.environ.setdefault("SIFTA_DESKTOP_ENABLE_AUTOSTART", "1")
os.environ.setdefault("SIFTA_EYE_DELTA_ENABLE", "1")
os.environ.setdefault("SIFTA_LEDGER_COMPACT_ENABLE", "1")
os.environ.setdefault("SIFTA_BURN_HARNESS_ENABLE", "1")
os.environ["PATH"] = "/Applications/Ollama.app/Contents/Resources:" + os.environ.get("PATH", "")

runpy.run_path(str(repo / "sifta_os_desktop.py"), run_name="__main__")
