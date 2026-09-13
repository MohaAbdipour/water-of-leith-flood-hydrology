from scripts.audit_repository import relative_readme_targets


def test_readme_target_parser_excludes_external_and_anchor_links():
    text = "[local](docs/a.md) [web](https://example.com) [section](#heading)"
    assert relative_readme_targets(text) == ["docs/a.md"]
