import pytest  # type: ignore
from constructor_manager_cli.utils.versions import (
    is_stable_version,
    parse_version,
    sort_versions,
)


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("0.4", True),
        ("0.4.15", True),
        ("0.4.15rc1", False),
        ("0.4.15dev0", False),
        ("0.4.15beta", False),
        ("0.4.15alfa", False),
        (("0", "4"), True),
        (("0", "4", "15"), True),
        (("0", "4", "15", "rc1"), False),
        (("0", "4", "15", "beta"), False),
    ],
)
def test_is_stable_version(test_input, expected):
    assert is_stable_version(test_input) == expected


@pytest.mark.parametrize(
    "test_input",
    [
        "0.4",
        "0.4.15",
        "0.4.15rc1",
        "0.4.15dev0",
        "0.4.15beta",
        "0.4.15alfa",
        "whatever",
    ],
)
def test_parse_version(test_input):
    str(parse_version(test_input)) == test_input


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (
            ["0.4.1", "0.4.1dev1", "0.1.1", "0.4.1dev0", "0.4.1a1"],
            ["0.1.1", "0.4.1dev0", "0.4.1dev1", "0.4.1a1", "0.4.1"],
        ),
    ],
)
def test_sort_versions(test_input, expected):
    assert sort_versions(test_input) == expected
