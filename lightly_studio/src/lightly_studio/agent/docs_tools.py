"""The agent tool that searches the LightlyStudio docs, so the model can answer how-to questions.

The docs are the markdown sources of the docs website. The wheel ships a copy next to this
module. An editable install reads them from the source checkout.
"""

from __future__ import annotations

import functools
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from lightly_studio.agent.agent_tool import AgentContext, AgentTool

_DOCS_SITE_URL = "https://docs.lightly.ai/studio"
_PACKAGED_DOCS_DIR = Path(__file__).parent / "docs"
_SOURCE_DOCS_DIR = Path(__file__).parents[3] / "docs" / "docs"

# The number of sections that one search returns.
_MAX_RESULTS = 3

# The longest section text that the model gets. Long tutorial sections are mostly code.
_MAX_SECTION_CHARS = 3000

_HEADING_PATTERN = re.compile(r"^(#{1,3})\s+(.+?)\s*$")
_TERM_PATTERN = re.compile(r"[a-z0-9_]+")
_CODE_FENCE = "```"
_FRONT_MATTER_FENCE = "---"
_TITLE_SEPARATOR = " > "

# A query word in the section title counts this many times more than a word in the text.
_TITLE_MATCH_WEIGHT = 3.0

# Words that occur in almost every section, so a match tells nothing.
_STOP_WORDS = frozenset(
    {"a", "an", "and", "are", "can", "do", "does", "for", "how", "i", "in", "is", "it", "my"}
    | {"of", "on", "or", "the", "this", "to", "what", "with", "you"}
)

# Words of this length or shorter that end in "s", such as "has" and "was", are not plurals.
_MIN_PLURAL_LENGTH = 3

# A mkdocstrings directive. The website renders the API reference from it, so the source
# has no prose there.
_DIRECTIVE_PREFIX = ":::"


@dataclass(frozen=True)
class DocsSection:
    """One section of a docs page, from one heading to the next.

    Attributes:
        page_path: The path of the page in the docs folder, for example "workflows/tags.md".
        title: The page title, then the section heading, for example "Tags > Tags in Python".
        text: The markdown text of the section, without its heading.
        url: The URL of the page on the docs website.
    """

    page_path: str
    title: str
    text: str
    url: str


class SearchDocsArgs(BaseModel):
    """Arguments of ``search_docs``."""

    query: str = Field(
        min_length=1,
        description=(
            "The topic of the question in a few keywords, for example 'export annotations "
            "COCO' or 'compute typicality'."
        ),
    )


def search_docs(context: AgentContext, args: SearchDocsArgs) -> dict[str, Any]:
    """Find the docs sections that match the query best.

    Raises:
        ValueError: If this installation has no copy of the docs.
    """
    del context
    docs_dir = _find_docs_dir()
    if docs_dir is None:
        raise ValueError(
            f"The docs are not available in this installation. Refer the user to {_DOCS_SITE_URL}."
        )
    sections = find_docs_sections(docs_dir=docs_dir, query=args.query, limit=_MAX_RESULTS)
    return {
        "results": [
            {"title": section.title, "url": section.url, "text": section.text[:_MAX_SECTION_CHARS]}
            for section in sections
        ]
    }


DOCS_TOOLS: list[AgentTool[Any]] = [
    AgentTool(
        name="search_docs",
        description=(
            "Search the LightlyStudio documentation. Returns the best matching sections with "
            "the URL of their page. Use it for questions on how to use LightlyStudio: the GUI, "
            "the Python API, installation, import, export, and the workflows."
        ),
        args_model=SearchDocsArgs,
        run=search_docs,
    ),
]


def find_docs_sections(docs_dir: Path, query: str, limit: int) -> list[DocsSection]:
    """Get the sections that match the query, the best match first.

    Args:
        docs_dir: The folder with the markdown pages.
        query: The search words.
        limit: The largest number of sections to return.

    Returns:
        At most ``limit`` sections with a score above zero.
    """
    query_terms = _to_terms(text=query)
    scored_sections = [
        (_score_section(query_terms=query_terms, section=section), section)
        for section in load_docs_sections(docs_dir=docs_dir)
    ]
    matches = [(score, section) for score, section in scored_sections if score > 0]
    matches.sort(key=lambda match: match[0], reverse=True)
    return [section for _, section in matches[:limit]]


@functools.lru_cache(maxsize=1)
def load_docs_sections(docs_dir: Path) -> tuple[DocsSection, ...]:
    """Read every markdown page of the docs folder and split it into sections."""
    sections: list[DocsSection] = []
    for page in sorted(docs_dir.rglob("*.md")):
        sections.extend(
            _split_page(
                page_path=page.relative_to(docs_dir).as_posix(),
                markdown=page.read_text(encoding="utf-8"),
            )
        )
    return tuple(sections)


def _find_docs_dir() -> Path | None:
    for docs_dir in (_PACKAGED_DOCS_DIR, _SOURCE_DOCS_DIR):
        if docs_dir.is_dir():
            return docs_dir
    return None


def _split_page(page_path: str, markdown: str) -> list[DocsSection]:
    """Split a page at its headings of level 1 to 3. A heading in a code block does not count."""
    page_title = ""
    heading = ""
    body: list[str] = []
    is_in_code = False
    sections: list[DocsSection] = []
    for line in _drop_front_matter(markdown=markdown).splitlines():
        if line.lstrip().startswith(_CODE_FENCE):
            is_in_code = not is_in_code
        match = None if is_in_code else _HEADING_PATTERN.match(line)
        if match is None:
            body.append(line)
            continue
        sections.append(
            _make_section(page_path=page_path, page_title=page_title, heading=heading, body=body)
        )
        heading = match.group(2)
        page_title = page_title or heading
        body = []
    sections.append(
        _make_section(page_path=page_path, page_title=page_title, heading=heading, body=body)
    )
    return [section for section in sections if _has_prose(text=section.text)]


def _make_section(
    page_path: str, page_title: str, heading: str, body: Sequence[str]
) -> DocsSection:
    is_page_title = heading == page_title
    title = page_title if is_page_title else f"{page_title}{_TITLE_SEPARATOR}{heading}"
    return DocsSection(
        page_path=page_path,
        title=title,
        text="\n".join(body).strip(),
        url=_page_url(page_path=page_path),
    )


def _drop_front_matter(markdown: str) -> str:
    if not markdown.startswith(_FRONT_MATTER_FENCE):
        return markdown
    _, _, rest = markdown[len(_FRONT_MATTER_FENCE) :].partition(f"\n{_FRONT_MATTER_FENCE}")
    return rest


def _has_prose(text: str) -> bool:
    """Check if the text has a line that is not a mkdocstrings directive or its options."""
    return any(
        line.strip() and not line.startswith((_DIRECTIVE_PREFIX, " ")) for line in text.splitlines()
    )


def _page_url(page_path: str) -> str:
    """Get the website URL of a page. An ``index.md`` page is the URL of its folder."""
    parts = page_path.removesuffix(".md").split("/")
    if parts[-1] == "index":
        parts.pop()
    return "/".join([_DOCS_SITE_URL, *parts, ""])


def _to_terms(text: str) -> list[str]:
    """Split a text into lowercase words without stop words.

    A plural word becomes singular, so "tags" finds "tag".
    """
    words = _TERM_PATTERN.findall(text.lower())
    return [_to_singular(word=word) for word in words if word not in _STOP_WORDS]


def _to_singular(word: str) -> str:
    is_plural = len(word) > _MIN_PLURAL_LENGTH and word.endswith("s") and not word.endswith("ss")
    return word[:-1] if is_plural else word


def _score_section(query_terms: Sequence[str], section: DocsSection) -> float:
    """Rate how well a section answers a query. A higher score is a better match.

    Args:
        query_terms: The lowercase words of the query.
        section: The docs section to rate.

    Each query word counts once, so a section that has all the words ranks above a section
    that repeats one word. A word in the title counts more than a word in the text.

    Args:
        query_terms: The words of the query, from ``_to_terms``.
        section: The docs section to rate.

    Returns:
        The score. Zero means that the section does not match.
    """
    title_terms = set(_to_terms(text=section.title))
    text_terms = set(_to_terms(text=section.text))
    score = 0.0
    for term in set(query_terms):
        if term in title_terms:
            score += _TITLE_MATCH_WEIGHT
        if term in text_terms:
            score += 1
    return score
