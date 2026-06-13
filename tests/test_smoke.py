"""Smoke tests — confirm the package skeleton imports and tooling runs."""

import importlib

import pytest


@pytest.mark.parametrize("name", ["core", "data", "storage", "app", "jobs"])
def test_packages_import(name):
    importlib.import_module(name)


def test_disclaimer_present():
    from core.constants import NOT_FINANCIAL_ADVICE

    assert "not financial advice" in NOT_FINANCIAL_ADVICE.lower()
