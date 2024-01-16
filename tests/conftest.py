import enum

import pytest
from fbenum.enum import FallbackEnum


@pytest.fixture(
    params=[
        [FallbackEnum],
        [str, FallbackEnum],
        [enum.StrEnum, FallbackEnum],
        [int, FallbackEnum],
        [enum.IntEnum, FallbackEnum],
        [float, FallbackEnum],
    ],
    ids=[
        'SimpleFallbackEnum',
        'RawStrFallbackEnum',
        'StrFallbackEnum',
        'RawIntFallbackEnum',
        'IntFallbackEnum',
        'FloatFallbackEnum',
    ],
)
def fallback_enum_class(request: pytest.FixtureRequest) -> type[FallbackEnum]:
    """Return a subclass of FallbackEnum."""

    class TestEnum(*request.param):
        A = 1
        B = 2

    return TestEnum


@pytest.fixture(
    params=[
        [enum.Enum],
        [str, enum.Enum],
        [enum.StrEnum],
        [int, enum.Enum],
        [enum.IntEnum],
        [float, enum.Enum],
    ],
    ids=['SimpleEnum', 'RawStrEnum', 'StrEnum', 'RawIntEnum', 'IntEnum', 'FloatEnum'],
)
def enum_class(request: pytest.FixtureRequest) -> type[enum.Enum]:
    """Return enum class."""

    class TestEnum(*request.param):
        A = '1'
        B = '2'

    return TestEnum


@pytest.fixture(
    params=[3, '3', 3.0, '3.0', 'INVALID'],
    ids=['int', 'str_int', 'float', 'str_float', 'str'],
)
def invalid_value(request: pytest.FixtureRequest) -> int | float | str:
    """Invalid value for the enum."""
    return request.param


@pytest.fixture
def validator_invalid_value_result(
    enum_class: type[enum.Enum],
    invalid_value: int | float | str,
) -> int | float | str | None:
    """Return the expected result of the validator function."""
    if issubclass(enum_class, int | float):
        if isinstance(invalid_value, str) and invalid_value.isalpha():
            return None

    if issubclass(enum_class, str):
        return str(invalid_value)

    if issubclass(enum_class, int):
        if isinstance(invalid_value, str) and '.' in invalid_value:
            # models convert the value to float, but validators don't
            # because validator uses type casting
            # e.g. int('3') == 3 and int('3.0') -> ValueError
            return None
        return int(invalid_value)

    if issubclass(enum_class, float):
        return float(invalid_value)

    return invalid_value


@pytest.fixture
def model_invalid_value_result(
    enum_class: type[enum.Enum],
    invalid_value: int | float | str,
) -> int | float | str | None:
    """Return the expected result of the model."""
    if issubclass(enum_class, int | float):
        if isinstance(invalid_value, str) and invalid_value.isalpha():
            return None

    if issubclass(enum_class, str):
        if not isinstance(invalid_value, str):
            # models don't convert the value to str
            return None
        return str(invalid_value)

    if issubclass(enum_class, int):
        return int(float(invalid_value))

    if issubclass(enum_class, float):
        return float(invalid_value)

    return invalid_value
