from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SUPPORTED_SUFFIXES = {
	".md",
	".txt",
	".py",
	".js",
	".ts",
	".json",
	".yaml",
	".yml",
	".csv",
}
IGNORED_DIRECTORIES = {".git", ".venv", "venv", "__pycache__", "node_modules"}


@dataclass(frozen=True)
class SourceDocument:
	source: str
	text: str


@dataclass(frozen=True)
class DocumentChunk:
	text: str
	source: str
	chunk_id: int


def _read_file(path: Path) -> str:
	if path.suffix.lower() == ".pdf":
		from pypdf import PdfReader

		return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
	return path.read_text(encoding="utf-8", errors="ignore")


def load_documents(path: str | Path) -> list[SourceDocument]:
	root = Path(path).expanduser().resolve()
	paths = [root] if root.is_file() else sorted(
		file_path
		for file_path in root.rglob("*")
		if not any(directory in IGNORED_DIRECTORIES for directory in file_path.parts)
	)
	documents = []
	for file_path in paths:
		if not file_path.is_file() or file_path.suffix.lower() not in SUPPORTED_SUFFIXES | {".pdf"}:
			continue
		text = _read_file(file_path).strip()
		if text:
			documents.append(SourceDocument(str(file_path), text))
	return documents


def chunk_documents(
	documents: Iterable[SourceDocument],
	chunk_size: int = 800,
	overlap: int = 120,
) -> list[DocumentChunk]:
	if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
		raise ValueError("chunk_size must be positive and overlap must be smaller than chunk_size")

	chunks: list[DocumentChunk] = []
	for document in documents:
		words = document.text.split()
		step = chunk_size - overlap
		for start in range(0, len(words), step):
			text = " ".join(words[start : start + chunk_size]).strip()
			if text:
				chunks.append(DocumentChunk(text, document.source, len(chunks)))
			if start + chunk_size >= len(words):
				break
	return chunks


__all__ = ["DocumentChunk", "SourceDocument", "chunk_documents", "load_documents"]
