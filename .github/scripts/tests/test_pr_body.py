from prepare_release import packages, pr_body

SERVE = packages.get("lightly-studio-serve")
STUDIO = packages.get("lightly-studio")
SECTION = "### Added\n\n- Added thing one."


def test_render_pr_body():
    body = pr_body.render_pr_body(section_body=SECTION, version="1.0.6", package=STUDIO)
    assert "Release notes for 1.0.6" in body
    assert "Added thing one" in body


def test_render_pr_body__review_checklist():
    body = pr_body.render_pr_body(section_body=SECTION, version="1.0.6", package=STUDIO)
    assert "## Review checklist" in body
    assert body.count("- [ ] ") == 5


def test_render_pr_body__says_merging_publishes_nothing():
    body = pr_body.render_pr_body(section_body=SECTION, version="1.0.6", package=STUDIO)
    assert "opens a **draft** GitHub release" in body


def test_render_pr_body__names_the_package_it_prepares():
    body = pr_body.render_pr_body(section_body=SECTION, version="0.1.1", package=SERVE)
    assert "LightlyStudio Serve 0.1.1" in body
    assert "`lightly_studio_serve/CHANGELOG.md`" in body
    assert "`lightly_studio_serve/pyproject.toml`" in body
