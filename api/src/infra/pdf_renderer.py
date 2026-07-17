"""``PdfRenderer`` adapter that builds an ATS-safe CV PDF with fpdf2.

Deliberately simple: a single column, standard section headers, clean bullet
points, no tables or icons — the layout ``cv_coach.md`` asks for. Uses the
built-in Helvetica core font (latin-1), so text is sanitized to that range;
swap in a Unicode TTF later if full-glyph fidelity is needed.
"""

from __future__ import annotations

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from src.domain.entities import InterviewGuide, RewrittenCv

# Common non-latin-1 characters mapped to safe equivalents for the core font.
_REPLACEMENTS = {
    "–": "-",
    "—": "-",  # en / em dash
    "‘": "'",
    "’": "'",  # curly single quotes
    "“": '"',
    "”": '"',  # curly double quotes
    "…": "...",  # ellipsis
    "•": "-",  # bullet
    "→": "->",  # arrow
    " ": " ",  # non-breaking space
    "⚠": "",
    "️": "",
    "✅": "",  # warning / check emoji
    "✓": "",
    "✔": "",  # check marks
}

_ACCENT = (200, 60, 45)  # terracotta section-heading rule
_MUTED = (110, 110, 110)


def _s(text: str) -> str:
    """Sanitize text into the latin-1 range the core font can render."""
    for bad, good in _REPLACEMENTS.items():
        text = text.replace(bad, good)
    return text.encode("latin-1", "replace").decode("latin-1")


class _CvPdf(FPDF):
    def header(self) -> None:  # no running header
        pass

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*_MUTED)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")


class Fpdf2Renderer:
    """Renders a :class:`RewrittenCv` into a downloadable PDF."""

    def render(self, cv: RewrittenCv) -> bytes:
        pdf = _CvPdf(format="A4")
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_margins(18, 16, 18)
        pdf.add_page()

        self._name(pdf, cv.full_name)
        self._contact(pdf, cv.contact)

        if cv.professional_summary:
            self._heading(pdf, "Professional Summary")
            self._paragraph(pdf, cv.professional_summary)

        if cv.experience:
            self._heading(pdf, "Work Experience")
            for entry in cv.experience:
                self._experience(pdf, entry.title, entry.company, entry.dates, entry.bullets)

        if cv.skills:
            self._heading(pdf, "Skills")
            self._paragraph(pdf, ", ".join(cv.skills))

        if cv.education:
            self._heading(pdf, "Education")
            for ed in cv.education:
                self._line_item(pdf, ed.qualification, f"{ed.institution} · {ed.dates}")

        if cv.certifications:
            self._heading(pdf, "Certifications")
            for cert in cv.certifications:
                self._bullet(pdf, cert)

        # NB: cv.rewrite_note is deliberately NOT rendered into the CV — it's
        # coaching feedback for the candidate, surfaced in the app UI instead.
        return bytes(pdf.output())

    def render_guide(self, guide: InterviewGuide) -> bytes:
        pdf = _CvPdf(format="A4")
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_margins(18, 16, 18)
        pdf.add_page()

        self._name(pdf, guide.headline)
        if guide.overview:
            self._paragraph(pdf, guide.overview)

        if guide.questions:
            self._heading(pdf, "Likely Questions & Model Answers")
            for i, q in enumerate(guide.questions, 1):
                self._subheading(pdf, f"{i}. {q.question}")
                if q.what_they_assess:
                    self._kv(pdf, "What they're assessing", q.what_they_assess)
                if q.how_to_answer:
                    self._kv(pdf, "How to answer", q.how_to_answer)
                if q.sample_answer:
                    self._kv(pdf, "Sample answer", q.sample_answer)
                pdf.ln(1)

        if guide.star_stories:
            self._heading(pdf, "Your STAR Stories")
            for story in guide.star_stories:
                self._bullet(pdf, story)

        if guide.study_plan:
            self._heading(pdf, "Study Plan")
            for item in guide.study_plan:
                self._subheading(pdf, item.topic)
                if item.why_it_matters:
                    self._kv(pdf, "Why it matters", item.why_it_matters)
                for action in item.how_to_prepare:
                    self._bullet(pdf, action)
                pdf.ln(1)

        if guide.company_deep_dive:
            self._heading(pdf, "Company Deep Dive")
            self._paragraph(pdf, guide.company_deep_dive)

        if guide.questions_to_ask:
            self._heading(pdf, "Smart Questions to Ask Them")
            for question in guide.questions_to_ask:
                self._bullet(pdf, question)

        if guide.day_of_checklist:
            self._heading(pdf, "Day-of Checklist")
            for tip in guide.day_of_checklist:
                self._bullet(pdf, tip)

        return bytes(pdf.output())

    # -- building blocks ---------------------------------------------------- #

    def _name(self, pdf: FPDF, name: str) -> None:
        pdf.set_font("Helvetica", "B", 20)
        pdf.set_text_color(20, 20, 20)
        pdf.multi_cell(0, 8, _s(name), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def _contact(self, pdf: FPDF, contact: str) -> None:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*_MUTED)
        pdf.multi_cell(0, 5, _s(contact), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

    def _heading(self, pdf: FPDF, title: str) -> None:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*_ACCENT)
        pdf.cell(0, 6, _s(title.upper()), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        y = pdf.get_y()
        pdf.set_draw_color(*_ACCENT)
        pdf.set_line_width(0.4)
        pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
        pdf.ln(2)
        pdf.set_text_color(30, 30, 30)

    def _paragraph(self, pdf: FPDF, text: str) -> None:
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(0, 5, _s(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def _subheading(self, pdf: FPDF, text: str) -> None:
        pdf.ln(1)
        pdf.set_font("Helvetica", "B", 10.5)
        pdf.set_text_color(20, 20, 20)
        pdf.multi_cell(0, 5.5, _s(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def _kv(self, pdf: FPDF, label: str, value: str) -> None:
        """An inline bold label followed by wrapping normal text."""
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(*_ACCENT)
        pdf.write(5, _s(f"{label}: "))
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.write(5, _s(value))
        pdf.ln(6)

    def _experience(
        self, pdf: FPDF, title: str, company: str, dates: str, bullets: list[str]
    ) -> None:
        pdf.set_font("Helvetica", "B", 10.5)
        pdf.set_text_color(20, 20, 20)
        pdf.multi_cell(0, 5.5, _s(f"{title} - {company}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if dates:
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(*_MUTED)
            pdf.cell(0, 5, _s(dates), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        for bullet in bullets:
            self._bullet(pdf, bullet)
        pdf.ln(1.5)

    def _bullet(self, pdf: FPDF, text: str) -> None:
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        left = pdf.l_margin
        pdf.set_x(left + 4)
        pdf.multi_cell(
            0,
            5,
            _s(f"• {text}"),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.set_x(left)

    def _line_item(self, pdf: FPDF, primary: str, secondary: str) -> None:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(20, 20, 20)
        pdf.multi_cell(0, 5, _s(primary), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*_MUTED)
        pdf.multi_cell(0, 5, _s(secondary), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)
