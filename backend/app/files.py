"""Uploaded files in a provider-neutral form.

Each AI service turns an `Attachment` into its own format (Claude content
block, Gemini inline data, Ollama image list). PDFs also get their text
extracted, so text-only models and demo mode can read them too.
"""

from __future__ import annotations

import base64
import io
import re
from dataclasses import dataclass

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
TEXT_EXT = re.compile(r"\.(txt|md|markdown|csv|rtf|html?)$", re.I)
MAX_TEXT_CHARS = 100_000


class UploadError(ValueError):
    """Raised for files we can't use; becomes a 400 response."""


@dataclass
class Upload:
    data: bytes
    content_type: str
    filename: str


@dataclass
class Attachment:
    kind: str  # "pdf" | "image" | "text"
    media_type: str
    filename: str
    data_b64: str  # base64 of the original bytes ("" for text files)
    text: str | None  # readable text: the text file itself, or text extracted from a PDF

    def anthropic_block(self) -> dict:
        if self.kind == "pdf":
            return {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": self.data_b64}}
        if self.kind == "image":
            return {"type": "image", "source": {"type": "base64", "media_type": self.media_type, "data": self.data_b64}}
        return {"type": "text", "text": self.as_prompt_text()}

    def as_prompt_text(self) -> str:
        return f'Assignment file "{self.filename}":\n\n{self.text or ""}'


def extract_pdf_text(data: bytes) -> str | None:
    """Best-effort PDF text extraction. Returns None for scanned PDFs or if pypdf is missing."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return None
    try:
        reader = PdfReader(io.BytesIO(data))
        text = "\n".join((page.extract_text() or "") for page in reader.pages[:30]).strip()
    except Exception:
        return None
    return text[:MAX_TEXT_CHARS] or None


def to_attachment(f: Upload) -> Attachment:
    if not f.data:
        raise UploadError("The file is empty.")
    if len(f.data) > MAX_UPLOAD_BYTES:
        raise UploadError("Files must be 10 MB or smaller.")

    ctype = (f.content_type or "").split(";")[0].strip().lower()
    name = f.filename or "file"
    b64 = lambda: base64.standard_b64encode(f.data).decode()  # noqa: E731

    if ctype == "application/pdf" or name.lower().endswith(".pdf"):
        return Attachment("pdf", "application/pdf", name, b64(), extract_pdf_text(f.data))
    if ctype in IMAGE_TYPES:
        return Attachment("image", ctype, name, b64(), None)
    if ctype.startswith("text/") or TEXT_EXT.search(name):
        return Attachment("text", "text/plain", name, "", f.data.decode("utf-8", errors="replace")[:MAX_TEXT_CHARS])

    raise UploadError("Upload a PDF, an image (PNG, JPG, WebP, GIF) or a text file. For Word files, save as PDF first.")
