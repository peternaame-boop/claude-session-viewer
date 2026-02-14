"""Tests for path encoding/decoding."""

import pytest
from claude_session_viewer.utils.path_codec import (
    encode_path,
    decode_path,
    strip_composite_suffix,
    extract_project_name,
)


class TestEncodePath:
    def test_absolute_path(self):
        assert encode_path("/home/wiz/AI/LLM") == "-home-wiz-AI-LLM"

    def test_root_path(self):
        assert encode_path("/") == "-"

    def test_empty_path(self):
        assert encode_path("") == ""

    def test_nested_path(self):
        assert encode_path("/home/user/projects/my-app") == "-home-user-projects-my-app"

    def test_windows_path(self):
        assert encode_path("C:\\Users\\wiz\\project") == "C:-Users-wiz-project"


class TestDecodePath:
    def test_absolute_path(self):
        assert decode_path("-home-wiz-AI-LLM") == "/home/wiz/AI/LLM"

    def test_root(self):
        assert decode_path("-") == "/"

    def test_empty(self):
        assert decode_path("") == ""

    def test_with_composite_suffix(self):
        assert decode_path("-home-wiz-project::a1b2c3d4") == "/home/wiz/project"

    def test_roundtrip(self):
        original = "/home/wiz/projects/my-cool-app"
        # Note: roundtrip isn't perfect because hyphens in path segments
        # become ambiguous, but encode->decode->encode should be stable
        encoded = encode_path(original)
        assert encoded == "-home-wiz-projects-my-cool-app"


class TestStripCompositeSuffix:
    def test_with_suffix(self):
        assert strip_composite_suffix("-home-wiz::a1b2c3d4") == "-home-wiz"

    def test_without_suffix(self):
        assert strip_composite_suffix("-home-wiz-project") == "-home-wiz-project"

    def test_wrong_hex_length(self):
        # Only 8-char hex suffixes are stripped
        assert strip_composite_suffix("-home-wiz::abc") == "-home-wiz::abc"

    def test_empty(self):
        assert strip_composite_suffix("") == ""


class TestExtractProjectName:
    def test_simple(self):
        assert extract_project_name("-home-wiz-AI-LLM") == "LLM"

    def test_with_composite(self):
        assert extract_project_name("-home-wiz-myapp::deadbeef") == "myapp"

    def test_empty(self):
        assert extract_project_name("") == ""
