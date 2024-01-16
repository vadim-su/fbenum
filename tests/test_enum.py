"""Tests for the FallbackEnum class."""

import pytest
from fbenum.enum import FallbackEnum, _get_cast_type


def test_setting_unknown_name_in_class():
    """Test setting the __unknown_name__ attribute in the class."""

    class TestEnum(str, FallbackEnum):
        __unknown_name__ = 'MISSING'

        A = '1'
        B = '2'

    assert TestEnum('1') is TestEnum.A

    missing_member = TestEnum('3')
    assert isinstance(missing_member, TestEnum)
    assert missing_member.name == 'MISSING'


def test_setting_unknown_name_after_class_creation(fallback_enum_class: type[FallbackEnum]):
    """Test setting the __unknown_name__ attribute after the class creation.

    I hade a bug where the __unknown_name__ attribute was not set in the class.
    This test is here to prevent that from happening again.
    """
    missing_member = fallback_enum_class('3')
    assert isinstance(missing_member, fallback_enum_class)
    assert missing_member.name == 'UNKNOWN'

    fallback_enum_class.__unknown_name__ = 'MISSING'

    assert fallback_enum_class(fallback_enum_class.A.value) is fallback_enum_class.A  # type: ignore

    missing_member = fallback_enum_class('3')
    assert isinstance(missing_member, fallback_enum_class)
    assert missing_member.name == 'MISSING'


def test_is_unknown_property(fallback_enum_class: type[FallbackEnum]):
    assert fallback_enum_class('3').is_unknown
    assert not fallback_enum_class.A.is_unknown  # type: ignore
    assert not fallback_enum_class(fallback_enum_class.A.value).is_unknown  # type: ignore


@pytest.mark.parametrize(
    'casting_type',
    [None, str, int],
)
def test_get_cast_type_method(fallback_enum_class: type[FallbackEnum], casting_type: type | None):
    """Test the _get_cast_type method.

    Too simple to test, but it's here for completeness.
    """
    if casting_type:
        fallback_enum_class.__casting_type__ = casting_type
        expected_cast_type = casting_type
    else:
        if issubclass(fallback_enum_class, str):
            expected_cast_type = str
        elif issubclass(fallback_enum_class, int):
            expected_cast_type = int
        elif issubclass(fallback_enum_class, float):
            expected_cast_type = float
        else:
            expected_cast_type = None

    assert _get_cast_type(enum_type=fallback_enum_class, casting_type=casting_type) is expected_cast_type


def test_type_casting_disabled():
    """Test disabling type casting."""

    class TestEnum(str, FallbackEnum):
        __enable_type_casting__ = False

        A = '1'
        B = '2'

    if issubclass(TestEnum, str):
        invalid_value = 5
    elif issubclass(TestEnum, int | float):
        invalid_value = '-1'
    else:
        invalid_value = 'INVALID'

    assert TestEnum(TestEnum.A.value) is TestEnum.A  # type: ignore
    assert TestEnum(invalid_value).value == invalid_value


def test_type_casting_disabled_after_creation(fallback_enum_class: type[FallbackEnum]):
    """Test disabling type casting after the class creation."""
    fallback_enum_class.__enable_type_casting__ = False

    if issubclass(fallback_enum_class, str):
        invalid_value = 5
    elif issubclass(fallback_enum_class, int | float):
        invalid_value = '-1'
    else:
        invalid_value = 'INVALID'

    assert fallback_enum_class(fallback_enum_class.A.value) is fallback_enum_class.A  # type: ignore
    assert fallback_enum_class(invalid_value).value == invalid_value
