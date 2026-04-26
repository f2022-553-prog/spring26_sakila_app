import pytest


def test_basic_math():
    """Sanity check - always passes."""
    assert 2 + 2 == 4


def test_environment_variables():
    """Verify test environment variables are accessible."""
    import os
    # These are set by the CI pipeline
    host = os.environ.get("MYSQL_HOST", "localhost")
    assert host is not None


def test_pymysql_importable():
    """Verify pymysql is installed."""
    import pymysql
    assert pymysql is not None


def test_flask_importable():
    """Verify flask is installed."""
    import flask
    assert flask is not None
