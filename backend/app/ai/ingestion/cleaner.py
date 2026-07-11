from __future__ import annotations

import re
import unicodedata

from app.ai.ingestion.pdf_parser import ParsedPaper, ParsedSection


def sanitize_filename(name: str) -> str:
    name = re.sub(r"[^\w\-_. ]", "", name)
    name = name.strip()
    if not name:
        name = "unnamed"
    return name


class DocumentCleaner:
    def clean(self, parsed: ParsedPaper) -> ParsedPaper:
        body = parsed.body
        body = self._unicode_normalize(body)
        body = self._clean_whitespace(body)
        body = self._remove_headers_footers(body)
        body = self._remove_duplicate_lines(body)
        body = self._remove_empty_pages(body)

        cleaned_sections = []
        for sec in parsed.sections:
            content = sec.content
            content = self._unicode_normalize(content)
            content = self._clean_whitespace(content)
            content = self._remove_headers_footers(content)
            cleaned_sections.append(
                ParsedSection(
                    heading=sec.heading,
                    content=content.strip(),
                    page_number=sec.page_number,
                )
            )

        title = self._unicode_normalize(parsed.title).strip()
        abstract = self._unicode_normalize(parsed.abstract).strip()
        abstract = self._clean_whitespace(abstract)

        return ParsedPaper(
            title=title,
            authors=parsed.authors,
            abstract=abstract,
            body=body.strip(),
            sections=cleaned_sections,
            references=parsed.references,
            page_count=parsed.page_count,
            extraction_method=parsed.extraction_method,
        )

    def _unicode_normalize(self, text: str) -> str:
        return unicodedata.normalize("NFC", text)

    def _clean_whitespace(self, text: str) -> str:
        text = re.sub(r"\r\n", "\n", text)
        text = re.sub(r"\r", "\n", text)
        text = re.sub(r"\t", " ", text)
        text = re.sub(r"[ \t]+(?=\n)", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[^\S\n]+", " ", text)
        return text.strip()

    def _remove_headers_footers(self, text: str) -> str:
        lines = text.split("\n")
        if len(lines) < 6:
            return text
        page_pattern = re.compile(r"^\s*\d+\s*$")
        header_footer_pattern = re.compile(
            r"^(arxiv|doi|vol\.|no\.|page|p\.\s*\d+|"
            r"proceedings of|journal of|ieee|acm|springer)",
            re.IGNORECASE,
        )

        cleaned = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                cleaned.append(line)
                continue
            if page_pattern.match(stripped):
                continue
            if (
                header_footer_pattern.match(stripped)
                and len(stripped) < 80
                and (i < 3 or i > len(lines) - 3)
            ):
                continue
            cleaned.append(line)

        return "\n".join(cleaned)

    def _remove_duplicate_lines(self, text: str) -> str:
        lines = text.split("\n")
        if len(lines) < 2:
            return text
        cleaned = [lines[0]]
        for i in range(1, len(lines)):
            curr = lines[i].strip()
            prev = lines[i - 1].strip()
            if curr and curr == prev:
                continue
            cleaned.append(lines[i])
        return "\n".join(cleaned)

    def _remove_empty_pages(self, text: str) -> str:
        pages = text.split("\f")
        if len(pages) <= 1:
            return text
        non_empty = [
            p for p in pages
            if len(p.strip()) > 100
        ]
        return "\f".join(non_empty) if non_empty else text



