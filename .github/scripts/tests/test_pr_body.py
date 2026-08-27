from prepare_release import pr_body


def test_render_pr_body():
    body = pr_body.render_pr_body(
        section_body="### Added\n\n- Added thing one.",
        coverage_checklist="- abc123 Some PR title (#42)",
    )
    assert "Draft release notes" in body
    assert "Added thing one" in body
    assert "Coverage checklist" in body
    assert "#42" in body


def test_render_pr_body__empty_checklist_shows_placeholder():
    body = pr_body.render_pr_body(
        section_body="### Fixed\n\n- A fix.",
        coverage_checklist="",
    )
    assert "_None found._" in body
