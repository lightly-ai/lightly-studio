"""Build-time hooks for the LightlyStudio docs.

Registered from `mkdocs.yml` under `hooks:`. MkDocs imports this file by path, so
it is not part of the `lightly_studio` package and nothing else imports it.
"""

from __future__ import annotations

import contextlib
from collections.abc import Mapping, MutableMapping
from importlib import metadata
from typing import Any, NamedTuple

from mkdocs import plugins
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure import StructureItem
from mkdocs.structure.files import Files
from mkdocs.structure.nav import Navigation, Section
from mkdocs.structure.pages import Page

log = plugins.get_plugin_logger(__name__)


class Tab(NamedTuple):
    """One tab of the header strip, resolved against the nav tree.

    Attributes:
        name: The label the strip prints.
        url: Where the tab lands, as a URL relative to the site root.
    """

    name: str
    url: str


def on_config(config: MkDocsConfig) -> MkDocsConfig:
    """Publishes the installed LightlyStudio version to the page templates.

    The footer prints it as the version the docs were built from, which keeps
    `pyproject.toml` the only place the version is written down. Building from a
    tree where the package is not installed leaves the key unset, and the footer
    then omits the version rather than printing a stale one.

    The key is `package_version` rather than `version`, which Material reserves
    for its mike-backed version selector.

    Args:
        config: The configuration MkDocs has just loaded.

    Returns:
        The same configuration, with `extra.package_version` set when the
        package is installed.
    """
    with contextlib.suppress(metadata.PackageNotFoundError):
        config.extra["package_version"] = metadata.version("lightly-studio")
    return config


def on_nav(
    nav: Navigation,
    *,
    config: MkDocsConfig,
    files: Files,  # noqa: ARG001
) -> Navigation:
    """Resolves the header tab strip against the nav tree.

    Each tab authored under `extra.tabs` claims a set of top-level `nav:` section
    titles, and lands on the first page beneath the first section it claims.
    Deriving that landing page from the nav rather than writing a URL down keeps
    the strip pointing somewhere real when the content branch moves a section.

    Sections no tab claims are added to the tab marked `default`, so a section
    added later is reachable from somewhere instead of falling out of every tab.

    Writes two keys the templates read: `extra.tab_links`, the strip itself, and
    `extra.tab_sections`, which maps each tab to the section titles the sidebar
    shows while that tab is active.

    Warns — and so, under `mkdocs build --strict`, fails the build — when a tab
    claims a section the nav does not have. Without that check, renaming a
    section on the content branch would silently unscope it.

    Args:
        nav: The navigation tree MkDocs has just built.
        config: The site configuration, read for `extra.tabs` and written to.
        files: The files collected for this build. Unused.

    Returns:
        The same navigation tree, unmodified.
    """
    specs = config.extra.get("tabs") or []
    sections = {item.title: item for item in nav.items}
    claimed = {title for spec in specs for title in spec["sections"]}

    links: list[Tab] = []
    tab_sections: dict[str, frozenset[str]] = {}
    for spec in specs:
        name = spec["name"]
        missing = [title for title in spec["sections"] if title not in sections]
        if missing:
            log.warning(
                f"Tab {name!r} claims nav sections that do not exist: "
                f"{', '.join(repr(title) for title in missing)}. Update "
                f"`extra.tabs` in mkdocs.yml to match `nav:`."
            )

        owned = [title for title in spec["sections"] if title in sections]
        if spec.get("default"):
            owned += [title for title in sections if title not in claimed]

        # The first section the tab claims that actually holds a page.
        candidates = (_landing_url(sections[title]) for title in owned)
        url = next((candidate for candidate in candidates if candidate is not None), None)
        if url is None:
            log.warning(f"Tab {name!r} has no page to link to and was dropped.")
            continue

        links.append(Tab(name=name, url=url))
        tab_sections[name] = frozenset(owned)

    if specs and not any(spec.get("default") for spec in specs):
        log.warning(
            "No tab in `extra.tabs` is marked `default: true`, so a nav section "
            "no tab claims would be reachable from no tab at all."
        )

    config.extra["tab_links"] = links
    config.extra["tab_sections"] = tab_sections
    return nav


def on_page_context(
    context: MutableMapping[str, Any],
    *,
    page: Page,
    config: MkDocsConfig,
    nav: Navigation,  # noqa: ARG001
) -> MutableMapping[str, Any]:
    """Tells the templates which tab this page belongs to.

    `ls_active_tab` marks the tab in the strip; `ls_nav_sections` is the set of
    top-level section titles the sidebar renders, which is what scopes it. Both
    are unset on templates MkDocs builds without a page — 404.html — where the
    strip draws with nothing marked and the sidebar shows every section, since a
    reader who is lost should see all the routes rather than one tab's.

    Args:
        context: The template context MkDocs has just built for the page.
        page: The page being rendered.
        config: The site configuration, read for what `on_nav` resolved.
        nav: The navigation tree. Unused.

    Returns:
        The same context, with the two keys above added.
    """
    tab_sections: Mapping[str, frozenset[str]] = config.extra.get("tab_sections") or {}
    active = _active_tab_name(page=page, tab_sections=tab_sections)
    context["ls_active_tab"] = active
    context["ls_nav_sections"] = tab_sections[active] if active is not None else None
    return context


def _landing_url(item: StructureItem) -> str | None:
    """Returns the URL of the first page under `item`, depth first.

    Args:
        item: A nav section, page or link.

    Returns:
        A URL relative to the site root, or None when the item holds no page —
        an external link, or a section of nothing but links. Narrowing by type
        rather than by `is_page`, which is a plain attribute the type checker
        cannot read as a guard.
    """
    if isinstance(item, Page):
        # `mypy .` runs without the `docs` dependency group, where every mkdocs
        # symbol is `Any`; the annotation is what keeps `--warn-return-any` quiet
        # there. See the `mkdocs.*` override in `pyproject.toml`.
        page_url: str = item.url
        return page_url
    if isinstance(item, Section):
        for child in item.children:
            url = _landing_url(child)
            if url is not None:
                return url
    return None


def _active_tab_name(page: Page, tab_sections: Mapping[str, frozenset[str]]) -> str | None:
    """Returns the name of the tab whose sections contain `page`.

    Args:
        page: The page being rendered.
        tab_sections: Section titles per tab, as resolved by `on_nav`.

    Returns:
        The tab name, or None for a page that sits at the top level of `nav:`
        and so belongs to no section.
    """
    ancestors = list(page.ancestors)
    if not ancestors:
        return None
    root = ancestors[-1].title
    return next((name for name, titles in tab_sections.items() if root in titles), None)
