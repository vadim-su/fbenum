import enum
from typing import Annotated
from decimal import Decimal

import pytest
from pydantic import BaseModel
from fbenum.adapter import FallbackAdapter


@pytest.fixture(params=[None, 'MISSING'])
def unknown_name(request: pytest.FixtureRequest) -> str | None:
    return request.param


def test_fallback_adapter_init():
    adapter = FallbackAdapter(enable_type_casting=False, casting_type=int, unknown_name='MISSING')
    assert adapter.enable_type_casting is False
    assert adapter.casting_type is int
    assert adapter.unknown_name == 'MISSING'


def test_validator_with_unknown_name(
    enum_class: type[enum.Enum],
    invalid_value: int | float | str,
    validator_invalid_value_result: int | float | str | None,
    unknown_name: str | None,
):
    """Test the validator function with unknown_name.

    Validator works as a lax schema.
    It returns the enum member if the value is valid. Or if the value is invalid,
    it returns a pseudo-member with the name UNKNOWN and the value without conversion.
    """
    params = {}
    if unknown_name is not None:
        params['unknown_name'] = unknown_name
    validator = FallbackAdapter(**params)._validator_factory(enum_class)

    assert validator(enum_class.A) == enum_class.A  # type: ignore
    assert validator(enum_class.A.value) == enum_class.A  # type: ignore

    if validator_invalid_value_result:
        assert validator(invalid_value).name == unknown_name or 'UNKNOWN'
        assert validator(invalid_value).value == validator_invalid_value_result
    else:
        with pytest.raises(ValueError):
            validator(invalid_value)


def test_validator_with_enabled_type_casting():
    """Test the validator function with enable_type_casting set to True."""

    class TestEnum(int, enum.Enum):
        A = 1
        B = 2

    # enable_type_casting is True by default
    validator = FallbackAdapter()._validator_factory(TestEnum)

    assert validator(1) is TestEnum.A
    assert validator('1') is TestEnum.A
    assert validator(1.0) is TestEnum.A

    assert validator('22').name == 'UNKNOWN'
    assert validator('22').value == 22


def test_validator_with_disabled_type_casting():
    """Test the validator function with enable_type_casting set to False."""

    class TestEnum(int, enum.Enum):
        A = 1
        B = 2

    # enable_type_casting is True by default
    validator = FallbackAdapter(enable_type_casting=False)._validator_factory(TestEnum)

    assert validator(1) is TestEnum.A
    assert validator('1').name == 'UNKNOWN'
    assert validator('1').value == '1'

    with pytest.raises(ValueError):
        validator('1.0')

    with pytest.raises(ValueError):
        validator('invalid')


def test_casting_type_is_not_set():
    """Test the validator function with casting_type not set."""

    class TestEnum(enum.Enum):
        A = 1
        B = 2

    validator = FallbackAdapter()._validator_factory(TestEnum)
    assert validator(1) is TestEnum.A

    assert validator('1').name == 'UNKNOWN'
    assert validator('1').value == '1'
    assert validator(1.2).name == 'UNKNOWN'
    assert validator(1.2).value == 1.2


def test_casting_type_is_int():
    """Test the validator function with casting_type set to int."""

    class TestEnum(enum.Enum):
        A = 1
        B = 2

    validator = FallbackAdapter(casting_type=int)._validator_factory(TestEnum)

    assert validator(1) is TestEnum.A
    assert validator('1') is TestEnum.A

    assert validator('22').name == 'UNKNOWN'
    assert validator('22').value == 22

    # int will cast 1.2 to 1
    assert validator(1.2) is TestEnum.A


def test_casting_type_is_str():
    """Test the validator function with casting_type set to str."""

    class TestEnum(enum.Enum):
        A = '1'
        B = '2'

    validator = FallbackAdapter(casting_type=str)._validator_factory(TestEnum)

    assert validator('1') is TestEnum.A
    assert validator(1) is TestEnum.A

    assert validator(22).name == 'UNKNOWN'
    assert validator(22).value == '22'

    # str will not cast 1.2 to 1
    assert validator(1.2).name == 'UNKNOWN'
    assert validator(1.2).value == '1.2'


def test_casting_type_is_decimal():
    """Test the validator function with casting_type set to Decimal."""

    class TestEnum(enum.Enum):
        A = Decimal('1')
        B = Decimal('2')

    validator = FallbackAdapter(casting_type=Decimal)._validator_factory(TestEnum)

    assert validator(Decimal('1')) is TestEnum.A
    assert validator('1') is TestEnum.A
    assert validator('1.0') is TestEnum.A
    assert validator(1) is TestEnum.A
    assert validator(1.0) is TestEnum.A

    assert validator('22').name == 'UNKNOWN'
    assert validator('22').value == Decimal('22')

    # Decimal will not cast 1.2 to 1
    assert validator(Decimal('1.2')).name == 'UNKNOWN'
    assert validator(Decimal('1.2')).value == Decimal('1.2')


def test_validate_model_with_unknown_name(
    enum_class: type[enum.Enum],
    invalid_value: int | float | str,
    model_invalid_value_result: int | float | str | None,
    unknown_name: str | None,
):
    """Test a Pydantic model with an enum field.

    It's similar to the validator function, but it also checks input type.
    For example, if the enum is int, it will convert the value to int, but
    if the enum is str, it will not convert the value and raise an error.
    """

    params = {}
    if unknown_name is not None:
        params['unknown_name'] = unknown_name

    class TestModel(BaseModel):
        field: Annotated[enum_class, FallbackAdapter(**params)]

    model = TestModel(field=enum_class.A.value)  # type: ignore
    assert model.field == enum_class.A  # type: ignore

    if model_invalid_value_result:
        model = TestModel(field=invalid_value)  # type: ignore
        assert model.field.name == unknown_name or 'UNKNOWN'
        assert model.field.value == model_invalid_value_result
    else:
        # result is None, so it raises an error
        with pytest.raises(ValueError):
            TestModel(field=invalid_value)  # type: ignore


@pytest.mark.parametrize('enable_type_casting', [True, False])
def test_validate_model_with_enabled_type_casting_without_casting_type(
    enum_class: type[enum.Enum],
    enable_type_casting: bool,
):
    """Test a Pydantic model with an enum field with enable_type_casting without casting_type.

    Even with enable_type_casting set to True, it will not cast the value to the enum type.
    It happens because by default casting_type is None and the python schema waits for the
    enum type or it's mixin.

    Example:

        In the example below, the enum is a subclass of str (enum.StrEnum),
        so the model will be waiting for a str or enum.StrEnum value. It will be weird
        if it accepts an int, for example.

        >>> class MyEnum(enum.StrEnum, FallbackEnum):
        ...     A = '1'
        ...     B = '2'
        ...
        >>> class TestModel(BaseModel):
        ...     field: Annotated[MyEnum, FallbackAdapter(enable_type_casting=True)]
        ...
        >>> model = TestModel(field=1)
        Traceback (most recent call last):
        ...
        pydantic.error_wrappers.ValidationError: 1 is not a valid MyEnum...
    """

    class TestModel(BaseModel):
        field: Annotated[enum_class, FallbackAdapter(enable_type_casting=enable_type_casting)]

    model = TestModel(field=enum_class.A)  # type: ignore
    assert model.field == enum_class.A  # type: ignore

    if issubclass(enum_class, int | float):
        model = TestModel(field=enum_class.A.value)  # type: ignore
        assert model.field is enum_class.A  # type: ignore

        model = TestModel(field=str(enum_class.A.value))  # type: ignore
        assert model.field is enum_class.A  # type: ignore

    elif issubclass(enum_class, str):
        model = TestModel(field=str(enum_class.A.value))  # type: ignore
        assert model.field is enum_class.A  # type: ignore

    if not issubclass(enum_class, int | float | str):  # if enum.Enum
        model = TestModel(field=enum_class.A.value)  # type: ignore
        assert model.field is enum_class.A  # type: ignore

        model = TestModel(field=22)  # type: ignore
        assert model.field.name == 'UNKNOWN'
        assert model.field.value == 22

        model = TestModel(field='22')  # type: ignore
        assert model.field.name == 'UNKNOWN'
        assert model.field.value == '22'


@pytest.mark.parametrize('enable_type_casting', [True, False])
@pytest.mark.parametrize(
    [
        'casting_type',
        'input_value',
        'expected_value_on_enabled_type_casting',
        'expected_value_on_disabled_type_casting',
    ],
    [
        [int, 1, 1, 1],
        [int, 1.2, 1, 1.2],
        [float, 1.0, 1, 1.0],
        [float, 3.0, 3.0, 3.0],
        [float, '1.2', 1.2, '1.2'],
        [str, 1, 1, 1],
        [str, 3, '3', 3],
        [str, '1.2', '1.2', '1.2'],
        [Decimal, 1, 1, 1],
        [Decimal, '1.2', Decimal('1.2'), '1.2'],
    ],
)
def test_validate_model_with_enabled_type_casting_with_casting_type(
    enable_type_casting: bool,
    casting_type: type[int | float | str | Decimal],
    input_value: int | float | str | Decimal,
    expected_value_on_enabled_type_casting: int | float | str | Decimal,
    expected_value_on_disabled_type_casting: int | float | str | Decimal,
):
    """Test a Pydantic model with an enum field with enable_type_casting and casting_type.

    It will cast the value to the given type before passing it to the enum.
    """

    class TestEnum(enum.Enum):
        A = 1
        B = 2

    class TestModel(BaseModel):
        field: Annotated[
            TestEnum,
            FallbackAdapter(
                enable_type_casting=enable_type_casting,
                casting_type=casting_type,
            ),
        ]

    if enable_type_casting:
        assert TestModel(field=input_value).field.value == expected_value_on_enabled_type_casting  # type: ignore
    else:
        assert TestModel(field=input_value).field.value == expected_value_on_disabled_type_casting  # type: ignore
