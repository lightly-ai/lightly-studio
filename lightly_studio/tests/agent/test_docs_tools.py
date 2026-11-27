from __future__ import annotations

from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.agent import docs_tools
from lightly_studio.agent.docs_tools import DocsSection, SearchDocsArgs
from tests import helpers_resolvers
from tests.agent import helpers_agent

_TAGS_PAGE = """\
---
title: Tags
---

# Tags

Tags organize samples.

## Tags in Python

```python
# Not a heading
sample.add_tag("train")
```

### Remove a tag

Call remove_tag.
"""

_EXPORT_PAGE = """\
# Export

## Export annotations

Export annotations in the COCO format with export_annotations.
"""

_API_STUB_PAGE = """\
# Sample

::: lightly_studio.core.sample
    options:
        members: [Sample]
"""


def test_search_docs(db_session: Session, mocker: MockerFixture, tmp_path: Path) -> None:
    _write_docs(docs_dir=tmp_path)
    mocker.patch.object(docs_tools, "_PACKAGED_DOCS_DIR", tmp_path)
    collection = helpers_resolvers.create_collection(session=db_session)
    context = helpers_agent.create_context(session=db_session, collection=collection)

    result = docs_tools.search_docs(context, SearchDocsArgs(query="export COCO annotations"))

    assert result["results"][0] == {
        "title": "Export > Export annotations",
        "url": "https://docs.lightly.ai/studio/workflows/export/",
        "text": "Export annotations in the COCO format with export_annotations.",
    }


def test_search_docs__no_docs(db_session: Session, mocker: MockerFixture, tmp_path: Path) -> None:
    mocker.patch.object(docs_tools, "_PACKAGED_DOCS_DIR", tmp_path / "missing")
    mocker.patch.object(docs_tools, "_SOURCE_DOCS_DIR", tmp_path / "missing")
    collection = helpers_resolvers.create_collection(session=db_session)
    context = helpers_agent.create_context(session=db_session, collection=collection)

    with pytest.raises(ValueError, match="docs are not available"):
        docs_tools.search_docs(context, SearchDocsArgs(query="tags"))


def test_find_docs_sections(tmp_path: Path) -> None:
    _write_docs(docs_dir=tmp_path)

    sections = docs_tools.find_docs_sections(docs_dir=tmp_path, query="remove tag", limit=1)

    assert [section.title for section in sections] == ["Tags > Remove a tag"]


def test_find_docs_sections__no_match(tmp_path: Path) -> None:
    _write_docs(docs_dir=tmp_path)

    assert docs_tools.find_docs_sections(docs_dir=tmp_path, query="kubernetes", limit=3) == []


def test_load_docs_sections(tmp_path: Path) -> None:
    _write_docs(docs_dir=tmp_path)

    sections = docs_tools.load_docs_sections(docs_dir=tmp_path)

    tags_url = "https://docs.lightly.ai/studio/"
    export_url = "https://docs.lightly.ai/studio/workflows/export/"
    # The API stub page has no prose, and the export page title has no text.
    assert sections == (
        DocsSection(
            page_path="index.md", title="Tags", text="Tags organize samples.", url=tags_url
        ),
        DocsSection(
            page_path="index.md",
            title="Tags > Tags in Python",
            text='```python\n# Not a heading\nsample.add_tag("train")\n```',
            url=tags_url,
        ),
        DocsSection(
            page_path="index.md",
            title="Tags > Remove a tag",
            text="Call remove_tag.",
            url=tags_url,
        ),
        DocsSection(
            page_path="workflows/export.md",
            title="Export > Export annotations",
            text="Export annotations in the COCO format with export_annotations.",
            url=export_url,
        ),
    )


def _write_docs(docs_dir: Path) -> None:
    (docs_dir / "workflows").mkdir()
    (docs_dir / "api").mkdir()
    (docs_dir / "index.md").write_text(_TAGS_PAGE)
    (docs_dir / "workflows" / "export.md").write_text(_EXPORT_PAGE)
    (docs_dir / "api" / "sample.md").write_text(_API_STUB_PAGE)
