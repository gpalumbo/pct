"""Tests for WikiLink parsing."""

from pct.board.wikilinks import extract_wikilinks, format_wikilink, parse_wikilink, resolve_wikilink


class TestParseWikilink:
    def test_feature_and_task(self):
        assert parse_wikilink("[[f1#task-1]]") == ("f1", "task-1")

    def test_feature_only(self):
        assert parse_wikilink("[[f1]]") == ("f1", None)

    def test_raw_inner(self):
        assert parse_wikilink("f1#task-1") == ("f1", "task-1")


class TestExtractWikilinks:
    def test_extract_from_text(self):
        text = "Depends on [[f1#task-a]] and [[f2#task-b]]"
        links = extract_wikilinks(text)
        assert links == ["f1#task-a", "f2#task-b"]

    def test_no_links(self):
        assert extract_wikilinks("No links here") == []


class TestFormatWikilink:
    def test_with_task(self):
        assert format_wikilink("f1", "task-1") == "[[f1#task-1]]"

    def test_feature_only(self):
        assert format_wikilink("f1") == "[[f1]]"


class TestResolveWikilink:
    def test_resolve(self):
        assert resolve_wikilink("[[f1#task-1]]") == ("f1", "task-1")
