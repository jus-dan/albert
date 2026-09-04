from fpdf import FPDF

from tools.text_utils import format_timestamp, split_about, swiss_de

INK = (0, 0, 0)


def build_wunschzettel_pdf(name: str, about: str, created_time: str, record_id: str) -> bytes:
    wish, why, idea = (swiss_de(part) for part in split_about(about or ""))
    wish = wish or swiss_de(name) or "etwas, das hier vor Ort besser wird"

    pdf = FPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(False)
    pdf.add_page()
    pdf.set_margins(20, 22, 20)
    pdf.set_text_color(*INK)
    pdf.set_draw_color(*INK)

    pdf.set_font("helvetica", "B", 26)
    pdf.cell(0, 12, "WUNSCHMASCHINE", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    pdf.set_font("helvetica", "B", 17)
    pdf.multi_cell(0, 9, f"Ich wünsche mir {wish}")

    pdf.ln(2)
    pdf.set_line_width(0.4)
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(8)

    if why:
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 6, "Warum?", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        pdf.set_font("helvetica", "", 12)
        pdf.multi_cell(0, 7, why)
        pdf.ln(3)

    if idea:
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 6, "Wie könnte man das umsetzen?", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        pdf.set_font("helvetica", "", 12)
        pdf.multi_cell(0, 7, idea)

    sketch_top = max(pdf.get_y() + 8, 160)
    sketch_bottom = 260
    pdf.set_line_width(0.3)
    pdf.rect(pdf.l_margin, sketch_top, pdf.w - pdf.l_margin - pdf.r_margin, sketch_bottom - sketch_top)
    pdf.set_font("helvetica", "", 8)
    pdf.set_xy(pdf.l_margin + 4, sketch_bottom - 8)
    pdf.cell(0, 5, "Platz für eine Skizze oder Ergänzungen")

    foot_y = 272
    pdf.line(pdf.l_margin, foot_y, pdf.w - pdf.r_margin, foot_y)
    pdf.set_xy(pdf.l_margin, foot_y + 2)
    pdf.set_font("helvetica", "", 8)
    pdf.cell(0, 5, format_timestamp(created_time))
    pdf.set_xy(pdf.l_margin, foot_y + 2)
    pdf.set_font("helvetica", "B", 8)
    pdf.cell(0, 5, f"ID {record_id}", align="R")

    return bytes(pdf.output())
