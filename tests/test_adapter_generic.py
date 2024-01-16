"""This test set contains tests for FallbackAdapter with generic type arguments."""

import pytest
from pydantic import BaseModel
from fbenum.enum import FallbackEnum
from fbenum.adapter import FallbackAdapter


def test_get_pydantic_core_schema(enum_class: type[FallbackEnum]):
    """Test the __get_pydantic_core_schema__ method."""
    schema = FallbackAdapter.__get_pydantic_core_schema__(FallbackAdapter[enum_class], None)  # type: ignore
    assert schema is not None


def test_get_pydantic_core_schema_with_no_generic_args():
    """Test the __get_pydantic_core_schema__ method with no generic args."""
    with pytest.raises(ValueError):
        FallbackAdapter.__get_pydantic_core_schema__(FallbackAdapter, None)  # type: ignore


def test_validator(
    enum_class: type[FallbackEnum],
    invalid_value: int | float | str,
    validator_invalid_value_result: int | float | str | None,
):
    """Test the validator function.

    Validator works as a lax schema.
    It returns the enum member if the value is valid. Or if the value is invalid,
    it returns a pseudo-member with the name UNKNOWN and the value without conversion.
    """
    validator = FallbackAdapter._validator_factory(enum_class)

    assert validator(enum_class.A) == enum_class.A  # type: ignore
    assert validator(enum_class.A.value) == enum_class.A  # type: ignore

    if validator_invalid_value_result:
        assert validator(invalid_value).name == 'UNKNOWN'
        assert validator(invalid_value).value == validator_invalid_value_result
    else:
        with pytest.raises(ValueError):
            validator(invalid_value)


def test_pydantic_model_with_enum(
    enum_class: type[FallbackEnum],
    invalid_value: int | float | str,
    model_invalid_value_result: int | float | str | None,
):
    """Test a Pydantic model with an enum field.

    It's similar to the validator function, but it also checks input type.
    For example, if the enum is int, it will convert the value to int, but
    if the enum is str, it will not convert the value and raise an error.
    """

    class TestModel(BaseModel):
        field: FallbackAdapter[enum_class]

    model = TestModel(field=enum_class.A.value)  # type: ignore
    assert model.field == enum_class.A  # type: ignore

    if model_invalid_value_result:
        model = TestModel(field=invalid_value)  # type: ignore
        assert model.field.name == 'UNKNOWN'
        assert model.field.value == model_invalid_value_result
    else:
        # result is None, so it raises an error
        with pytest.raises(ValueError):
            TestModel(field=invalid_value)  # type: ignore


def test_pydantic_model_with_enum_list(
    enum_class: type[FallbackEnum],
    invalid_value: int | float | str,
    model_invalid_value_result: int | float | str | None,
):
    """Test a Pydantic model with a list of enum fields."""

    class TestModel(BaseModel):
        field: list[FallbackAdapter[enum_class]]

    if model_invalid_value_result:
        model = TestModel(field=[enum_class.A, enum_class.A.value, invalid_value])  # type: ignore
        assert model.field[0] is enum_class.A  # type: ignore
        assert model.field[1] is enum_class.A  # type: ignore
        assert model.field[2].name == 'UNKNOWN'
        assert model.field[2].value == model_invalid_value_result
    else:
        # result is None, so it raises an error
        with pytest.raises(ValueError):
            TestModel(field=[enum_class.A, enum_class.A.value, invalid_value])  # type: ignore


def test_pydantic_model_with_enum_dict(
    enum_class: type[FallbackEnum],
    invalid_value: int | float | str,
    model_invalid_value_result: int | float | str | None,
):
    """Test a Pydantic model with a dict of enum fields."""

    class TestModel(BaseModel):
        field: dict[str, FallbackAdapter[enum_class]]

    if model_invalid_value_result:
        model = TestModel(
            field={
                'a': enum_class.A,  # type: ignore
                'b': enum_class.A.value,  # type: ignore
                'c': invalid_value,  # type: ignore
            },
        )
        assert model.field['a'] is enum_class.A  # type: ignore
        assert model.field['b'] is enum_class.A  # type: ignore
        assert model.field['c'].name == 'UNKNOWN'
        assert model.field['c'].value == model_invalid_value_result
    else:
        # result is None, so it raises an error
        with pytest.raises(ValueError):
            TestModel(
                field={
                    'a': enum_class.A,  # type: ignore
                    'b': enum_class.A.value,  # type: ignore
                    'c': invalid_value,  # type: ignore
                },
            )
