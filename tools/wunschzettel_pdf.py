from datetime import datetime

from fpdf import FPDF

from tools.text_utils import swiss_de

INK = (28, 28, 28)
INK_SOFT = (107, 107, 107)
LINE = (217, 215, 210)


def _split_about(about: str) -> tuple[str, str]:
    marker = "Konkrete lokale Idee:"
    idx = about.find(marker)
    wish_section = about if idx == -1 else about[:idx]
    wish = wish_section.replace("Urspruenglicher Wunsch:", "").strip()
    idea = "" if idx == -1 else about[idx + len(marker):].strip()
    return wish, idea


MONTHS_DE = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]


def _format_timestamp(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return f"{dt.day}. {MONTHS_DE[dt.month - 1]} {dt.year} · {dt.hour:02d}:{dt.minute:02d} Uhr"
    except Exception:
        return ""


def build_wunschzettel_pdf(name: str, about: str, created_time: str, record_id: str) -> bytes:
    name = swiss_de(name)
    wish, idea = (swiss_de(part) for part in _split_about(about or ""))

    pdf = FPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(False)
    pdf.add_page()
    pdf.set_margins(20, 22, 20)

    pdf.set_text_color(*INK)
    pdf.set_font("helvetica", "B", 26)
    pdf.cell(0, 12, "WUNSCHMASCHINE", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.set_font("helvetica", "B", 9)
    pdf.set_text_color(*INK_SOFT)
    pdf.cell(0, 5, "IM GESPRAECH ERFASST", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("helvetica", "I", 15)
    pdf.set_text_color(*INK)
    pdf.multi_cell(0, 8, name or "Ein Wunsch fuer hier", align="C")

    pdf.ln(3)
    pdf.set_draw_color(*INK)
    pdf.set_line_width(0.4)
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(8)

    pdf.set_font("helvetica", "I", 13)
    pdf.set_text_color(*INK)
    pdf.multi_cell(0, 8, f'"{wish or "-"}"')

    if idea:
        pdf.ln(4)
        pdf.set_font("helvetica", "B", 8)
        pdf.set_text_color(*INK_SOFT)
        pdf.cell(0, 5, "UND WAS DAS HIER VOR ORT BEDEUTEN KOENNTE", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        pdf.set_font("helvetica", "", 12)
        pdf.set_text_color(*INK)
        pdf.multi_cell(0, 7, idea)

    sketch_top = max(pdf.get_y() + 8, 160)
    sketch_bottom = 260
    pdf.set_draw_color(*LINE)
    pdf.set_line_width(0.5)
    pdf.rect(pdf.l_margin, sketch_top, pdf.w - pdf.l_margin - pdf.r_margin, sketch_bottom - sketch_top)
    pdf.set_font("helvetica", "", 8)
    pdf.set_text_color(*INK_SOFT)
    pdf.set_xy(pdf.l_margin + 4, sketch_bottom - 8)
    pdf.cell(0, 5, "Platz fuer eine Skizze")

    foot_y = 272
    pdf.set_draw_color(*LINE)
    pdf.line(pdf.l_margin, foot_y, pdf.w - pdf.r_margin, foot_y)
    pdf.set_xy(pdf.l_margin, foot_y + 2)
    pdf.set_font("helvetica", "", 8)
    pdf.set_text_color(*INK_SOFT)
    pdf.cell(0, 5, _format_timestamp(created_time))
    pdf.set_xy(pdf.l_margin, foot_y + 2)
    pdf.set_font("helvetica", "B", 8)
    pdf.set_text_color(*INK)
    pdf.cell(0, 5, f"ID {record_id}", align="R")

    return bytes(pdf.output())
