"""Build-time hooks for the LightlyStudio docs.

Registered from `mkdocs.yml` under `hooks:`. MkDocs imports this file by path, so
it is not part of the `lightly_studio` package and nothing else imports it.
"""

from __future__ import annotations

import contextlib
import posixpath
from collections.abc import Iterable, Mapping, MutableMapping, Sequence
from importlib import metadata
from pathlib import Path
from typing import Any, NamedTuple

from mkdocs import plugins
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure import StructureItem
from mkdocs.structure.files import File, Files
from mkdocs.structure.nav import Navigation, Section
from mkdocs.structure.pages import Page

log = plugins.get_plugin_logger(__name__)

# Pages whose URL changed, mapped from the path that used to hold them to the
# page that replaced them. `on_post_build` writes a stub at each old URL, so a
# bookmark or an inbound link still lands on the page it was made for. The
# folder realignment described above `nav:` in mkdocs.yml moved all 17.
#
# A stub redirects from the browser, which answers 200 rather than the 301 that
# the host serving docs.lightly.ai should send. It is what keeps an old link
# working until those host rules are in place, and the fallback for readers
# after that. Drop an entry only once its old URL is no longer worth serving.
_REDIRECTS: Mapping[str, str] = {
    "dataset_setup/notebooks.md": "get_started/notebooks.md",
    "dataset_setup/reuse_datasets.md": "get_started/reuse_datasets.md",
    "dataset_setup/image_dataset.md": "workflows/image_dataset.md",
    "dataset_setup/video_dataset.md": "workflows/video_dataset.md",
    "dataset_setup/cloud_storage.md": "ecosystem/cloud_storage.md",
    "concepts_and_tools/search_and_filter.md": "workflows/search_and_filter.md",
    "concepts_and_tools/lightly_query_language.md": "workflows/lightly_query_language.md",
    "concepts_and_tools/dataset_distributions.md": "workflows/dataset_distributions.md",
    "concepts_and_tools/sampling.md": "workflows/sampling.md",
    "concepts_and_tools/annotations.md": "workflows/annotations.md",
    "concepts_and_tools/captions.md": "workflows/captions.md",
    "concepts_and_tools/evaluation.md": "workflows/evaluation.md",
    "concepts_and_tools/export.md": "workflows/export.md",
    "concepts_and_tools/tags.md": "core_concepts/tags.md",
    "concepts_and_tools/metadata.md": "core_concepts/metadata.md",
    "concepts_and_tools/embeddings.md": "core_concepts/embeddings.md",
    "concepts_and_tools/plugins.md": "ecosystem/plugins.md",
}

# The stub written at each old URL. The script carries over an anchor the reader
# arrived with, which the `meta refresh` alone cannot; the refresh is the
# fallback with JavaScript off. `rel=canonical` points search engines at the new
# URL, and the body is what a reader sees if both redirects fail.
_REDIRECT_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Redirecting</title>
<link rel="canonical" href="{url}">
<meta http-equiv="refresh" content="0; url={url}">
<script>var a=window.location.hash.substr(1);location.replace("{url}"+(a?"#"+a:""))</script>
</head>
<body>
<p>This page moved. Continue to <a href="{url}">its new location</a>.</p>
</body>
</html>
"""


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


def on_files(files: Files, *, config: MkDocsConfig) -> Files:
    """Records where each page landed, and checks the redirect map against it.

    `on_post_build` needs a page's built URL to point a stub at it, and by then
    the file list is gone, so it is stashed on the config here.

    Args:
        files: The files collected for this build.
        config: The site configuration, written to.

    Returns:
        The same files, unmodified.
    """
    page_urls = {page.src_uri: page.url for page in files.documentation_pages()}
    config.extra["ls_page_urls"] = page_urls
    _warn_on_redirect_drift(page_urls=page_urls)
    return files


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

    Malformed `extra.tabs` is warned about, not acted on: `_validated_tab_specs`
    drops a tab missing a `name` or `sections`, and warns about a tab claiming a
    section the nav lacks, two tabs sharing a name, and a count of `default` tabs
    other than one. Every warning fails the build under `mkdocs build --strict`,
    so a bad edit stops the docs instead of shipping a broken or unscoped strip.

    Args:
        nav: The navigation tree MkDocs has just built.
        config: The site configuration, read for `extra.tabs` and written to.
        files: The files collected for this build. Unused.

    Returns:
        The same navigation tree, unmodified.
    """
    sections: dict[str, StructureItem] = {
        item.title: item for item in nav.items if item.title is not None
    }
    specs = _validated_tab_specs(
        specs=config.extra.get("tabs") or [],
        section_titles=set(sections),
    )
    links, tab_sections = _resolve_tabs(specs=specs, sections=sections)
    config.extra["tab_links"] = links
    config.extra["tab_sections"] = tab_sections

    _warn_on_llmstxt_drift(nav=nav, config=config)
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


def on_post_build(*, config: MkDocsConfig) -> None:
    """Writes a redirecting stub at every URL that `_REDIRECTS` retires.

    Runs after the site is written, so a stub lands beside the built pages and
    ships with them. Two entries are skipped: one whose target the build did not
    produce, whose stub would point nowhere, and one whose source holds a page
    again, whose stub would overwrite that page. `on_files` warns about both,
    which fails the build under `--strict`, but that abort lands after the site
    is written, so the skip here is what keeps the built site correct.

    Args:
        config: The site configuration, read for the site directory, the URL
            style, and the page URLs `on_files` stashed.
    """
    page_urls: Mapping[str, str] = config.extra.get("ls_page_urls") or {}
    use_directory_urls: bool = config.use_directory_urls
    site_dir = Path(config.site_dir)

    written = 0
    for old_src, new_src in _REDIRECTS.items():
        new_url = page_urls.get(new_src)
        # A stub that points nowhere, and one that would overwrite the page its
        # own source now holds.
        if new_url is None or old_src in page_urls:
            continue
        old_dest = _dest_path(src_path=old_src, use_directory_urls=use_directory_urls)
        target = _relative_url(
            from_dest=old_dest, to_url=new_url, use_directory_urls=use_directory_urls
        )
        stub = site_dir / old_dest
        stub.parent.mkdir(parents=True, exist_ok=True)
        stub.write_text(_REDIRECT_TEMPLATE.format(url=target), encoding="utf-8")
        written += 1
    log.info(f"Wrote {written} redirect stubs for pages that moved.")


def _validated_tab_specs(
    *, specs: Sequence[Mapping[str, Any]], section_titles: set[str]
) -> list[Mapping[str, Any]]:
    """Warns on every malformed tab and returns only the well-formed ones.

    Each warning fails the build under `mkdocs build --strict`. A tab missing a
    `name` or `sections` is dropped so the rest of the strip still resolves;
    every other problem is warned about but left in, since the tab is otherwise
    usable.

    Args:
        specs: The raw `extra.tabs` entries, straight from the YAML.
        section_titles: The titles of the top-level `nav:` sections.

    Returns:
        The subset of `specs` that carry both a `name` and a `sections` key, in
        their original order.
    """
    well_formed: list[Mapping[str, Any]] = []
    for spec in specs:
        if "name" not in spec or "sections" not in spec:
            log.warning(
                f"Dropping a tab in `extra.tabs` that is missing a `name` or "
                f"`sections` key: {spec!r}."
            )
            continue
        _warn_on_missing_sections(spec=spec, section_titles=section_titles)
        well_formed.append(spec)

    names = [spec["name"] for spec in well_formed]
    for name in sorted({n for n in names if names.count(n) > 1}):
        log.warning(
            f"Two or more tabs in `extra.tabs` are named {name!r}. Tab names "
            f"must be unique; the sidebar scoping keys on them."
        )

    defaults = [spec["name"] for spec in well_formed if spec.get("default")]
    if well_formed and len(defaults) != 1:
        log.warning(
            f"`extra.tabs` must mark exactly one tab `default: true`, found "
            f"{len(defaults)}: {', '.join(repr(name) for name in defaults)}. The "
            f"default tab is where nav sections no tab claims are shown."
        )
    return well_formed


def _warn_on_missing_sections(*, spec: Mapping[str, Any], section_titles: set[str]) -> None:
    """Warns when a tab claims a `nav:` section that does not exist.

    Args:
        spec: One well-formed `extra.tabs` entry.
        section_titles: The titles of the top-level `nav:` sections.
    """
    missing = [title for title in spec["sections"] if title not in section_titles]
    if missing:
        log.warning(
            f"Tab {spec['name']!r} claims nav sections that do not exist: "
            f"{', '.join(repr(title) for title in missing)}. Update "
            f"`extra.tabs` in mkdocs.yml to match `nav:`."
        )


def _resolve_tabs(
    *, specs: Sequence[Mapping[str, Any]], sections: Mapping[str, StructureItem]
) -> tuple[list[Tab], dict[str, frozenset[str]]]:
    """Builds the tab strip and each tab's sidebar scope from validated specs.

    A tab lands on the first page under the sections it claims. The `default` tab
    also takes every section no other *surviving* tab claims, so a section stays
    reachable even when the only tab that named it is dropped for want of a page.

    Args:
        specs: The well-formed `extra.tabs` entries, in strip order.
        sections: The top-level `nav:` sections, keyed by title.

    Returns:
        The strip as a list of `Tab`, and the map from tab name to the frozenset
        of section titles its sidebar shows.
    """
    explicit = {
        spec["name"]: [title for title in spec["sections"] if title in sections] for spec in specs
    }
    landing = {
        name: _first_landing_url(owned=owned, sections=sections) for name, owned in explicit.items()
    }
    # A dropped tab (no landing page) must not keep its sections out of the
    # default tab, so only tabs that survive count as claiming a section.
    claimed = {
        title
        for spec in specs
        if landing[spec["name"]] is not None
        for title in explicit[spec["name"]]
    }

    links: list[Tab] = []
    tab_sections: dict[str, frozenset[str]] = {}
    for spec in specs:
        name = spec["name"]
        owned = list(explicit[name])
        if spec.get("default"):
            owned += [title for title in sections if title not in claimed and title not in owned]
        url = landing[name] or _first_landing_url(owned=owned, sections=sections)
        if url is None:
            log.warning(f"Tab {name!r} has no page to link to and was dropped.")
            continue
        links.append(Tab(name=name, url=url))
        tab_sections[name] = frozenset(owned)
    return links, tab_sections


def _first_landing_url(
    *, owned: Iterable[str], sections: Mapping[str, StructureItem]
) -> str | None:
    """Returns the landing URL of the first section in `owned` that holds a page.

    Args:
        owned: Section titles, in the order the tab claims them.
        sections: The top-level `nav:` sections, keyed by title.

    Returns:
        A URL relative to the site root, or None when no owned section holds a
        page.
    """
    for title in owned:
        url = _landing_url(sections[title])
        if url is not None:
            return url
    return None


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
        # A local `uv run mypy .` resolves the default groups only, so mkdocs is
        # absent and every symbol from it is `Any`; the annotation is what keeps
        # `--warn-return-any` quiet there. See the `mkdocs.*` override in
        # `pyproject.toml`. CI installs all groups and types this properly.
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


def _warn_on_llmstxt_drift(*, nav: Navigation, config: MkDocsConfig) -> None:
    """Warns when `llmstxt.sections` and `nav:` list different pages.

    The two are hand-maintained copies of the same page set. The llmstxt plugin
    silently drops any page missing from its `sections`, and `mkdocs build
    --strict` stays green, so the page vanishes from llms.txt with no signal.
    This turns that drift into a warning — a build error under `--strict`.

    Skipped when `sections` uses glob patterns, which a set comparison cannot
    resolve against resolved page paths.

    Args:
        nav: The navigation tree MkDocs has just built.
        config: The site configuration, read for the llmstxt plugin's sections.
    """
    plugin = config.plugins.get("llmstxt")
    if plugin is None:
        return
    sections = plugin.config.get("sections") or {}
    listed = {
        item if isinstance(item, str) else next(iter(item))
        for pages in sections.values()
        for item in pages
    }
    if any("*" in path for path in listed):
        return
    in_nav = {page.file.src_uri for page in nav.pages}
    only_nav = sorted(in_nav - listed)
    only_llms = sorted(listed - in_nav)
    if only_nav or only_llms:
        log.warning(
            "`llmstxt.sections` and `nav:` list different pages. Only in `nav:`: "
            f"{only_nav}. Only in `llmstxt.sections`: {only_llms}. Update "
            "`sections` in mkdocs.yml to match."
        )


def _warn_on_redirect_drift(page_urls: Mapping[str, str]) -> None:
    """Warns when `_REDIRECTS` disagrees with the pages this build produced.

    Each warning fails the build under `mkdocs build --strict`, which is what
    reports the drift. It is not what protects the built site: the abort lands
    after the site is written, and `mkdocs serve` does not use `--strict` at
    all, so `on_post_build` skips both cases as well. Two ways it can go wrong:
    a target that no longer exists, which would publish a stub pointing
    nowhere, and a source a page has since reclaimed, where the stub would
    overwrite that built page and hide it behind a redirect.

    Args:
        page_urls: The built URL of every page, keyed by source path.
    """
    missing = sorted({new for new in _REDIRECTS.values() if new not in page_urls})
    if missing:
        log.warning(
            f"`_REDIRECTS` in mkdocs_hooks.py points at pages that do not exist: "
            f"{missing}. Repoint each entry at the page that replaced it, or drop "
            f"it if the old URL is no longer worth serving."
        )

    shadowed = sorted(old for old in _REDIRECTS if old in page_urls)
    if shadowed:
        log.warning(
            f"`_REDIRECTS` in mkdocs_hooks.py redirects away from paths that hold "
            f"a page again: {shadowed}. Its stub would overwrite that page. Drop "
            f"the entry, or move the new page elsewhere."
        )


def _dest_path(src_path: str, use_directory_urls: bool) -> str:
    """Returns the path a source page builds to, relative to the site directory.

    Args:
        src_path: A page path relative to `docs_dir`, such as `a/b.md`.
        use_directory_urls: The site's URL style, which decides whether the page
            builds to `a/b/index.html` or to `a/b.html`.

    Returns:
        The built path, with forward slashes on every platform.
    """
    # MkDocs owns this mapping, so a `File` computes it rather than this hook
    # restating the rule. The source and destination directories are irrelevant
    # to `dest_uri` and are left empty. `dest_uri` is forward-slashed on every
    # platform, unlike the discouraged `dest_path`, which uses backslashes on
    # Windows. The annotation is there for the reason given in `_landing_url`.
    dest_uri: str = File(src_path, "", "", use_directory_urls).dest_uri
    return dest_uri


def _relative_url(from_dest: str, to_url: str, use_directory_urls: bool) -> str:
    """Returns the link from a built page to a site URL.

    The stubs link relatively so that they hold wherever the site is mounted,
    which matters here because this one is served under `/studio` rather than at
    a domain root.

    Args:
        from_dest: The built path of the page holding the link.
        to_url: The target's URL, relative to the site root.
        use_directory_urls: The site's URL style. Directory URLs end in a slash,
            which `posixpath.relpath` drops and this restores.

    Returns:
        The target as a URL relative to `from_dest`.
    """
    relative = posixpath.relpath(to_url, start=posixpath.dirname(from_dest))
    return f"{relative}/" if use_directory_urls else relative
