import logging
from datetime import datetime

logger = logging.getLogger("albert.printing")

try:
    import win32con
    import win32print
    import win32ui

    PRINTING_AVAILABLE = True
except ImportError:
    PRINTING_AVAILABLE = False


def list_printers() -> list[str]:
    if not PRINTING_AVAILABLE:
        return []
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    printers = win32print.EnumPrinters(flags)
    return sorted(p[2] for p in printers)


def _wrap_by_width(hdc, text: str, max_width_px: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        width, _ = hdc.GetTextExtent(candidate)
        if width > max_width_px:
            lines.append(current)
            current = word
        else:
            current = candidate
    lines.append(current)
    return lines


def _rgb(r: int, g: int, b: int) -> int:
    return r | (g << 8) | (b << 16)


INK = _rgb(28, 28, 28)
INK_SOFT = _rgb(107, 107, 107)
LINE_GRAY = _rgb(217, 215, 210)


def print_wunschzettel_directly(
    printer_name: str, name: str, about: str, created_time: str, record_id: str
) -> None:
    """Druckt direkt ueber GDI/den Windows-Druckertreiber -- keine PDF-Datei,
    keine externe Anwendung, die ein Fenster oeffnen oder haengenbleiben
    koennte. Layout spiegelt bewusst 1:1 das Layout von
    tools/wunschzettel_pdf.py (Vorschau-PDF), damit beide immer gleich
    aussehen."""
    if not PRINTING_AVAILABLE:
        raise RuntimeError("Drucken ist auf diesem System nicht verfuegbar (pywin32 fehlt).")

    from tools.text_utils import format_timestamp, split_about, swiss_de

    name = swiss_de(name) or "Ein Wunsch für hier"
    wish, idea = (swiss_de(part) for part in split_about(about or ""))
    timestamp = format_timestamp(created_time)

    hdc = win32ui.CreateDC()
    hdc.CreatePrinterDC(printer_name)
    dpi_x = hdc.GetDeviceCaps(win32con.LOGPIXELSX)
    dpi_y = hdc.GetDeviceCaps(win32con.LOGPIXELSY)
    page_width_px = hdc.GetDeviceCaps(win32con.HORZRES)

    def mm_x(mm: float) -> int:
        return int(mm / 25.4 * dpi_x)

    def mm_y(mm: float) -> int:
        return int(mm / 25.4 * dpi_y)

    def pt(size_pt: float) -> int:
        return -int(size_pt * dpi_y / 72)

    margin_mm = 20
    left_px = mm_x(margin_mm)
    right_px = page_width_px - mm_x(margin_mm)
    max_text_width_px = right_px - left_px

    def centered(text: str, y_mm: float) -> None:
        width, _ = hdc.GetTextExtent(text)
        hdc.TextOut((page_width_px - width) // 2, mm_y(y_mm), text)

    def right_aligned(text: str, y_mm: float) -> None:
        width, _ = hdc.GetTextExtent(text)
        hdc.TextOut(right_px - width, mm_y(y_mm), text)

    def hline(y_mm: float, color: int) -> None:
        hdc.SelectObject(win32ui.CreatePen(win32con.PS_SOLID, 1, color))
        hdc.MoveTo((left_px, mm_y(y_mm)))
        hdc.LineTo((right_px, mm_y(y_mm)))

    hdc.StartDoc("Wunschzettel")
    hdc.StartPage()

    y = 25.0
    hdc.SetTextColor(INK)
    hdc.SelectObject(win32ui.CreateFont({"name": "Arial", "height": pt(26), "weight": 700}))
    centered("WUNSCHMASCHINE", y)
    y += 15

    hdc.SetTextColor(INK_SOFT)
    hdc.SelectObject(win32ui.CreateFont({"name": "Arial", "height": pt(9), "weight": 700}))
    centered("IM GESPRÄCH ERFASST", y)
    y += 10

    hdc.SetTextColor(INK)
    hdc.SelectObject(win32ui.CreateFont({"name": "Arial", "height": pt(15), "italic": 1}))
    for line in _wrap_by_width(hdc, name, max_text_width_px):
        centered(line, y)
        y += 8
    y += 3

    hline(y, INK)
    y += 8

    hdc.SelectObject(win32ui.CreateFont({"name": "Arial", "height": pt(13), "italic": 1}))
    for line in _wrap_by_width(hdc, f'"{wish or "-"}"', max_text_width_px):
        hdc.TextOut(left_px, mm_y(y), line)
        y += 8
    y += 4

    if idea:
        hdc.SetTextColor(INK_SOFT)
        hdc.SelectObject(win32ui.CreateFont({"name": "Arial", "height": pt(8), "weight": 700}))
        hdc.TextOut(left_px, mm_y(y), "UND WAS DAS HIER VOR ORT BEDEUTEN KÖNNTE")
        y += 6
        hdc.SetTextColor(INK)
        hdc.SelectObject(win32ui.CreateFont({"name": "Arial", "height": pt(12)}))
        for line in _wrap_by_width(hdc, idea, max_text_width_px):
            hdc.TextOut(left_px, mm_y(y), line)
            y += 7

    sketch_top = max(y + 8, 160)
    sketch_bottom = 260
    hdc.SelectObject(win32ui.CreatePen(win32con.PS_SOLID, 1, LINE_GRAY))
    x0, x1 = left_px, right_px
    y0, y1 = mm_y(sketch_top), mm_y(sketch_bottom)
    hdc.MoveTo((x0, y0))
    hdc.LineTo((x1, y0))
    hdc.LineTo((x1, y1))
    hdc.LineTo((x0, y1))
    hdc.LineTo((x0, y0))
    hdc.SetTextColor(INK_SOFT)
    hdc.SelectObject(win32ui.CreateFont({"name": "Arial", "height": pt(8)}))
    hdc.TextOut(left_px + mm_x(4), mm_y(sketch_bottom - 8), "Platz für eine Skizze")

    foot_y = 272
    hline(foot_y, LINE_GRAY)
    hdc.SetTextColor(INK_SOFT)
    hdc.SelectObject(win32ui.CreateFont({"name": "Arial", "height": pt(8)}))
    hdc.TextOut(left_px, mm_y(foot_y + 2), timestamp)
    hdc.SetTextColor(INK)
    hdc.SelectObject(win32ui.CreateFont({"name": "Arial", "height": pt(8), "weight": 700}))
    right_aligned(f"ID {record_id}", foot_y + 2)

    hdc.EndPage()
    hdc.EndDoc()
    logger.info("Direkt gedruckt auf '%s' (Record %s)", printer_name, record_id)


def print_test_page(printer_name: str) -> None:
    """Einfache Testseite, um zu pruefen, dass ein Drucker grundsaetzlich
    funktioniert -- unabhaengig von einem Gespraech mit Albert."""
    if not PRINTING_AVAILABLE:
        raise RuntimeError("Drucken ist auf diesem System nicht verfuegbar (pywin32 fehlt).")

    hdc = win32ui.CreateDC()
    hdc.CreatePrinterDC(printer_name)
    dpi_x = hdc.GetDeviceCaps(win32con.LOGPIXELSX)
    dpi_y = hdc.GetDeviceCaps(win32con.LOGPIXELSY)

    def mm_x(mm: float) -> int:
        return int(mm / 25.4 * dpi_x)

    def mm_y(mm: float) -> int:
        return int(mm / 25.4 * dpi_y)

    def pt(size_pt: float) -> int:
        return -int(size_pt * dpi_y / 72)

    hdc.StartDoc("Albert Testseite")
    hdc.StartPage()

    hdc.SelectObject(win32ui.CreateFont({"name": "Arial", "height": pt(20), "weight": 700}))
    hdc.TextOut(mm_x(20), mm_y(25), "WUNSCHMASCHINE — Testseite")

    hdc.SelectObject(win32ui.CreateFont({"name": "Arial", "height": pt(11)}))
    hdc.TextOut(mm_x(20), mm_y(40), f"Drucker: {printer_name}")
    hdc.TextOut(mm_x(20), mm_y(48), datetime.now().strftime("%d.%m.%Y, %H:%M Uhr"))
    hdc.TextOut(mm_x(20), mm_y(60), "Wenn du das hier siehst, funktioniert der Drucker.")

    hdc.EndPage()
    hdc.EndDoc()
    logger.info("Testseite gedruckt auf '%s'", printer_name)
