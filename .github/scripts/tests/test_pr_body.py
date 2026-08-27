from prepare_release import pr_body


def test_render_pr_body():
    body = pr_body.render_pr_body(section_body="### Added\n\n- Added thing one.")
    assert "Draft release notes" in body
    assert "Added thing one" in body
