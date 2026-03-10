"""Orchestration: depends only on ports, never on adapters."""

from __future__ import annotations

from pathlib import Path

from .domain import Article, PaperFile, RenameAction
from .ports import FileSystem, PdfReader, SlugGenerator


class PaperRenamer:
    """
    Plan-then-execute orchestration.
    .plan() is side-effect-free (reads only).
    .execute() writes to the filesystem.
    """

    def __init__(
        self,
        fs: FileSystem,
        reader: PdfReader,
        slugger: SlugGenerator,
    ) -> None:
        self._fs = fs
        self._reader = reader
        self._slugger = slugger

    def list_pdfs(self, folder: Path) -> list[Path]:
        """Delegate PDF listing to the filesystem port."""
        return self._fs.list_pdfs(folder)

    # -- planning (read-only) ------------------------------------------------

    def plan(self, folder: Path) -> list[RenameAction]:
        """Produce an ordered rename plan. Reads PDFs + calls LLM, no renames."""
        paths = self._fs.list_pdfs(folder)
        used: set[str] = set()
        actions: list[RenameAction] = []

        for path in paths:
            paper = PaperFile.from_path(path)
            if paper is None:
                actions.append(RenameAction.skip(path, "no numeric ID prefix"))
                continue

            text = self._reader.extract_text(path)
            if not text:
                actions.append(RenameAction.skip(path, "no text extracted"))
                continue

            slug = self._slugger.generate(text)
            article = Article(slug=slug)
            new_name = paper.target_name(article)

            # deduplicate within the batch
            new_name = self._deduplicate(new_name, used)
            used.add(new_name)

            if new_name == paper.original_name:
                actions.append(RenameAction.keep(path))
            else:
                actions.append(RenameAction(source=path, new_name=new_name))

        return actions

    @staticmethod
    def _deduplicate(name: str, used: set[str]) -> str:
        if name not in used:
            return name
        counter = 2
        base = name.removesuffix(".pdf")
        while True:
            candidate = f"{base}_{counter}.pdf"
            if candidate not in used:
                return candidate
            counter += 1

    # -- execution (writes) --------------------------------------------------

    def execute(self, actions: list[RenameAction], dry_run: bool = False) -> None:
        """Apply a plan to the filesystem."""
        for action in actions:
            print(f"  {action.source.name}")

            if action.skipped:
                print(f"    -> skipped: {action.reason}")
                continue

            if action.is_noop:
                print(f"    -> already named correctly")
                continue

            if dry_run:
                print(f"    -> {action.new_name}  (dry-run)")
                continue

            target = action.source.parent / action.new_name
            if self._fs.exists(target):
                print(f"    -> target exists on disk, skipping: {action.new_name}")
                continue

            self._fs.rename(action.source, target)
            print(f"    => {action.new_name}")


def make_renamer(model: str) -> PaperRenamer:
    """Wire concrete adapters into the service."""
    from .adapters import LocalFileSystem, OpenAiSlugGenerator, PyMuPdfReader

    return PaperRenamer(
        fs=LocalFileSystem(),
        reader=PyMuPdfReader(max_pages=5, max_chars=4000),
        slugger=OpenAiSlugGenerator(model=model),
    )
