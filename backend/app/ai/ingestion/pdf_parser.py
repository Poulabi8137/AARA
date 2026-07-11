from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ParsedSection:
    heading: str
    content: str
    page_number: int = 0


@dataclass
class ParsedPaper:
    title: str
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    body: str = ""
    sections: list[ParsedSection] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    page_count: int = 0
    extraction_method: str = "unknown"


SECTION_PATTERNS = re.compile(
    r"^(?:\d+\s*[.)]\s*)?"
    r"(abstract|introduction|background|related\s*work|"
    r"method(?:ology)?|approach|framework|system|"
    r"experiment(?:s)?|evaluation|results|discussion|"
    r"conclusion|conclusions|future\s*work|"
    r"references|acknowledgments?|appendix|"
    r"limitations|contributions|overview|"
    r"preliminaries|problem\s*definition|"
    r"implementation|dataset(?:s)?|data|"
    r"analysis|findings|discussion|"
    r"ethical\s*considerations)"
    r"(?:\s*:*\s*)$",
    re.IGNORECASE,
)


class PdfParser:
    def parse(self, file_path: str) -> ParsedPaper:
        try:
            return self._parse_pymupdf(file_path)
        except Exception:
            pass
        try:
            return self._parse_pdfplumber(file_path)
        except Exception:
            pass
        return ParsedPaper(
            title="", body="", page_count=0, extraction_method="failed",
        )

    def _parse_pymupdf(self, file_path: str) -> ParsedPaper:
        import fitz

        doc = fitz.open(file_path)
        page_count = doc.page_count
        pages_text = []
        for page_num in range(page_count):
            page = doc[page_num]
            text = page.get_text("text")
            pages_text.append(text)

        full_text = "\n".join(pages_text)
        title, authors, abstract, body, sections, references = (
            self._extract_structure(full_text)
        )

        doc.close()
        return ParsedPaper(
            title=title,
            authors=authors,
            abstract=abstract,
            body=body,
            sections=sections,
            references=references,
            page_count=page_count,
            extraction_method="pymupdf",
        )

    def _parse_pdfplumber(self, file_path: str) -> ParsedPaper:
        import pdfplumber

        with pdfplumber.open(file_path) as pdf:
            page_count = len(pdf.pages)
            pages_text = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages_text.append(text)

        full_text = "\n".join(pages_text)
        title, authors, abstract, body, sections, references = (
            self._extract_structure(full_text)
        )
        return ParsedPaper(
            title=title,
            authors=authors,
            abstract=abstract,
            body=body,
            sections=sections,
            references=references,
            page_count=page_count,
            extraction_method="pdfplumber",
        )

    def _extract_structure(
        self,
        text: str,
    ) -> tuple[str, list[str], str, str, list[ParsedSection], list[str]]:
        lines = text.split("\n")
        title = ""
        authors: list[str] = []
        abstract = ""
        sections: list[ParsedSection] = []
        references: list[str] = []
        body_lines: list[str] = []
        current_section: ParsedSection | None = None
        in_abstract = False
        in_references = False
        abstract_lines: list[str] = []

        for i, line in enumerate(lines):
            stripped = line.strip()

            if not stripped:
                if current_section is not None:
                    body_lines.append("")
                continue

            if in_references:
                if self._is_reference_line(stripped):
                    references.append(stripped)
                    body_lines.append(stripped)
                else:
                    body_lines.append(stripped)
                continue

            if not title and len(stripped) > 10 and i < 10:
                title = stripped
                body_lines.append(stripped)
                continue

            section_match = SECTION_PATTERNS.match(stripped)
            if section_match:
                heading = section_match.group(1).strip().lower()
                if heading == "abstract":
                    in_abstract = True
                    current_section = ParsedSection(
                        heading="Abstract", content="", page_number=0,
                    )
                    sections.append(current_section)
                    continue
                elif heading == "references":
                    in_references = True
                    current_section = ParsedSection(
                        heading="References", content="", page_number=0,
                    )
                    sections.append(current_section)
                    continue
                else:
                    in_abstract = False
                    current_section = ParsedSection(
                        heading=heading.capitalize(), content="", page_number=0,
                    )
                    sections.append(current_section)
                    body_lines.append(stripped)
                    continue

            if in_abstract:
                abstract_lines.append(stripped)
                abstract = " ".join(abstract_lines)
                if current_section is not None:
                    current_section.content = abstract
                body_lines.append(stripped)
                continue

            if current_section is not None:
                cur_heading = current_section.heading
                if cur_heading not in ("Abstract", "References"):
                    current_section.content += stripped + "\n"

            body_lines.append(stripped)

        body = "\n".join(body_lines)

        if not authors:
            authors = self._extract_authors_from_first_page(text)

        if not abstract:
            abstract = self._extract_abstract_from_first_page(text)

        return title, authors, abstract, body, sections, references

    def _is_reference_line(self, line: str) -> bool:
        patterns = [
            r"^\[\d+\]",
            r"^\d+\.\s",
            r"^[A-Z][a-z]+(?:\s+et\s+al\.?)?,?\s+\d{4}",
            r"^https?://",
            r"^arXiv:",
            r"^DOI:",
        ]
        return any(re.match(p, line) for p in patterns)

    def _extract_authors_from_first_page(self, text: str) -> list[str]:
        lines = text.split("\n")
        authors: list[str] = []
        for i, line in enumerate(lines[:50]):
            stripped = line.strip()
            if not stripped:
                continue
            if i < 3:
                continue
            if SECTION_PATTERNS.match(stripped):
                break
            if re.match(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*", stripped):
                parts = [p.strip() for p in stripped.replace(",", "").split()]
                name_parts = [
                    p for p in parts
                    if not re.match(r"^\d+$", p)
                    and not re.match(r"^[*,†‡§¶#]+$", p)
                ]
                if 2 <= len(name_parts) <= 4:
                    candidate = " ".join(name_parts)
                    if candidate not in authors and len(candidate) > 3:
                        authors.append(candidate)
            if len(authors) >= 2:
                break
        return authors

    def _extract_abstract_from_first_page(self, text: str) -> str:
        m = re.search(
            r"abstract[:\s]+(.+?)(?:introduction|1\.?\s*introduction)",
            text, re.DOTALL | re.IGNORECASE,
        )
        if m:
            abstract = m.group(1).strip()
            abstract = re.sub(r"\s+", " ", abstract)
            return abstract[:1000]
        return ""
