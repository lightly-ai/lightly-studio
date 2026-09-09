from prepare_release import pr_body


def test_render_pr_body():
    body = pr_body.render_pr_body(section_body="### Added\n\n- Added thing one.", version="1.0.6")
    assert "Release notes for 1.0.6" in body
    assert "Added thing one" in body


def test_render_pr_body__review_checklist():
    body = pr_body.render_pr_body(section_body="### Added\n\n- Added thing one.", version="1.0.6")
    assert "## Review checklist" in body
    assert body.count("- [ ] ") == 5


def test_render_pr_body__says_merging_publishes_nothing():
    body = pr_body.render_pr_body(section_body="### Added\n\n- Added thing one.", version="1.0.6")
    assert "opens a **draft** GitHub release" in body
