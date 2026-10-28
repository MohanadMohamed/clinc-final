"""Windows-only onedir test client; backend and React assets live on doctor host."""
import sys
from pathlib import Path

if sys.platform != "win32":
    raise RuntimeError("Build the Windows client on Windows, never cross-compile")

root = Path(SPECPATH).resolve().parents[1]  # noqa: F821
a = Analysis(  # noqa: F821
    [str(root / "desktop" / "launcher.py")],
    pathex=[], binaries=[], datas=[],
    hiddenimports=["webview.platforms.winforms", "webview.platforms.edgechromium"],
    # pywebview supplies its own PyInstaller hook for JS and native DLLs.
    # Upstream WinForms can fall back even when edgechromium was requested.
    # Excluding MSHTML makes a missing WebView2 fail instead in this frozen client.
    excludes=["webview.platforms.mshtml", "PyQt5", "PyQt6", "PySide2", "PySide6", "cefpython3", "gi",
              "fastapi", "sqlalchemy", "psycopg", "app"],
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821
exe = EXE(  # noqa: F821
    pyz, a.scripts, [], exclude_binaries=True, name="ClinicClient",
    console=True, debug=False, strip=False, upx=False,
    uac_admin=False,
)
coll = COLLECT(  # noqa: F821
    exe, a.binaries, a.datas, strip=False, upx=False, name="ClinicClient",
)
