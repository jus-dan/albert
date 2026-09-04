import logging
import time
import uuid
from pathlib import Path

logger = logging.getLogger("albert.printing")

try:
    import win32api
    import win32print

    PRINTING_AVAILABLE = True
except ImportError:
    PRINTING_AVAILABLE = False

PRINT_TEMP_DIR = Path(__file__).resolve().parent.parent / "data" / "print_temp"


def list_printers() -> list[str]:
    if not PRINTING_AVAILABLE:
        return []
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    printers = win32print.EnumPrinters(flags)
    return sorted(p[2] for p in printers)


def print_pdf_bytes(pdf_bytes: bytes, printer_name: str) -> None:
    if not PRINTING_AVAILABLE:
        raise RuntimeError("Drucken ist auf diesem System nicht verfuegbar (pywin32 fehlt).")

    PRINT_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = PRINT_TEMP_DIR / f"wunschzettel-{uuid.uuid4().hex}.pdf"
    temp_path.write_bytes(pdf_bytes)

    # ShellExecute mit "printto" delegiert an die registrierte
    # PDF-Anwendung (z.B. Edge/Acrobat), die den Druckauftrag asynchron
    # an den angegebenen Drucker schickt -- die Datei muss dafuer noch
    # eine Weile bestehen bleiben, wird also nicht sofort geloescht.
    win32api.ShellExecute(0, "printto", str(temp_path), f'"{printer_name}"', ".", 0)
    logger.info("Druckauftrag an '%s' gesendet: %s", printer_name, temp_path.name)
    _cleanup_old_temp_files()


def _cleanup_old_temp_files(max_age_seconds: int = 300) -> None:
    if not PRINT_TEMP_DIR.exists():
        return
    now = time.time()
    for f in PRINT_TEMP_DIR.glob("*.pdf"):
        try:
            if now - f.stat().st_mtime > max_age_seconds:
                f.unlink()
        except OSError:
            pass
