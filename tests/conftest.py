"""Test configuration for local src-layout imports."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TESTS_DATA_DIR = ROOT / "tests" / "data"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dmsp_ssm._internal.format.definition import FormatDefinition


@pytest.fixture
def tests_data_dir() -> Path:
    return TESTS_DATA_DIR


@pytest.fixture
def ssm_format_definition() -> dict:
    return FormatDefinition().as_dict()
