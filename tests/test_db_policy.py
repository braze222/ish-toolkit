import pytest

from lib.db_policy import DBPolicy, PolicyError, validate_sql


def test_select_allowed():
    validate_sql("SELECT * FROM users", DBPolicy())


def test_parameterized_select_allowed():
    validate_sql(
        "SELECT * FROM users WHERE id = ?",
        DBPolicy(),
    )


def test_delete_blocked():
    with pytest.raises(PolicyError):
        validate_sql(
            "DELETE FROM users WHERE id = ?",
            DBPolicy(),
        )


def test_drop_blocked():
    with pytest.raises(PolicyError):
        validate_sql(
            "DROP TABLE users",
            DBPolicy(),
        )


def test_multiple_statements_blocked():
    with pytest.raises(PolicyError):
        validate_sql(
            "SELECT 1; DROP TABLE users",
            DBPolicy(
                read_only=False,
                allow_destructive=True,
            ),
        )
