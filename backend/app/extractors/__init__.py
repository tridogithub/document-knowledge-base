from collections.abc import Callable

from ..schema import Chunk

Extractor = Callable[..., list[Chunk]]

SUPPORTED_EXTENSIONS = {"pdf", "docx", "pptx", "xlsx", "xls", "md", "markdown", "txt"}


def get_extractor(ext: str) -> Extractor:
    ext = ext.lower().lstrip(".")
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '.{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    if ext in {"md", "markdown", "txt"}:
        from .text_extractor import extract_text_file

        return extract_text_file
    from .docling_extractor import extract_docling

    return extract_docling
