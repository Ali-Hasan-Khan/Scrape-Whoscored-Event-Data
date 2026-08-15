"""Tests for the match-centre parser."""

from __future__ import annotations

import pytest

from whoscored.exceptions import ParseError
from whoscored.parser import extract_match_id, find_args_script, parse_match_data


def test_find_args_script_present(match_html: str):
    assert "matchCentreData" in find_args_script(match_html)


def test_find_args_script_missing_raises():
    with pytest.raises(ParseError):
        find_args_script("<html><body>nothing here</body></html>")


def test_extract_match_id(match_html: str):
    assert extract_match_id(match_html) == 1650630


def test_extract_match_id_missing_raises():
    with pytest.raises(ParseError):
        extract_match_id("<html></html>")


def test_parse_match_data_structure(match_data):
    assert match_data["matchId"] == 1650630
    assert "matchCentreEventTypeJson" in match_data
    assert len(match_data["matchCentreEventTypeJson"]) > 100
    assert len(match_data["events"]) > 1000


def test_parse_match_data_metadata(match_data):
    assert match_data["league"] == "LaLiga"
    assert match_data["season"] == "2022/2023"
    assert match_data["region"] == "Spain"
    assert match_data["competitionType"] == "League"


def test_parse_match_data_teams(match_data):
    assert match_data["home"]["name"] == "Barcelona"
    assert match_data["away"]["name"] == "Rayo Vallecano"
    assert match_data["home"]["teamId"] == 65
    assert match_data["away"]["teamId"] == 64


def test_parse_match_data_keys_sorted(match_data):
    assert list(match_data) == sorted(match_data)
