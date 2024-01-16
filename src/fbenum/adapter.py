"""Pydantic type adapter for fallback enums.

This adapter allows pydanitc to accept values that are not in the enum and return a
pseudo-member with the name UNKNOWN and the value without conversion. This is useful
for enums that are used to represent values from an API.
Sometimes, the API will return a value that is not in the enum (and docs).

Examples:
    Adapter wihtout options:

    >>> class MessageTypes(enum.IntEnum):
    ...     TEXT = 0
    ...     IMAGE = 1
    ...
    >>> class Message(BaseModel):
    ...     type: FallbackAdapter[MessageTypes]
    ...     content: Any
    ...
    >>> Message(type=MessageTypes.TEXT, content='Hello')
    Message(type=<MessageTypes.TEXT: 0>, content='Hello')
    >>> Message(type=2, content='Hello')
    Message(type=<MessageTypes.UNKNOWN: 2>, content='Hello')

    Adapter with options:

    >>> class MessageTypes(enum.IntEnum):
    ...     TEXT = 0
    ...     IMAGE = 1
    ...
    >>> class Message(BaseModel):
    ...     type: Annotated[MessageTypes, FallbackAdapter(unknown_name='MISSING')]
    ...     content: Any
    ...
    >>> Message(type=MessageTypes.TEXT, content='Hello')
    Message(type=<MessageTypes.TEXT: 0>, content='Hello')
    >>> Message(type=2, content='Hello')
    Message(type=<MessageTypes.MISSING: 2>, content='Hello')
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING, get_args, get_origin
from functools import wraps

from pydantic_core import core_schema

from fbenum.enum import DEFAULT_UNKNOWN_NAME, _process_missing_member

if TYPE_CHECKING:
    from typing import Any, Self, ClassVar

    from pydantic import GetCoreSchemaHandler
    from pydantic_core import CoreSchema


class _classinstancemethod:
    """Class instance method descriptor.

    This descriptor allows to use class instance methods as class methods.

    Example:

        class A:
            value: ClassVar[int] = 0

            def __init__(self, value):
                self.value = value

            @_classinstancemethod
            def add(cls_or_self, other):
                return cls_or_self.value + other

        assert A.add(2) == 2
        assert A(1).add(2) == 3
    """

    def __init__(self, method, instance=None, owner=None):
        """Initialize the descriptor.

        Args:
            method: Method to call.
            instance: Instance to use.
            owner: Owner of the method.
                Usually the class that owns the method.
        """
        self.method = method
        self.instance = instance
        self.owner = owner

        # Get method metadata like __name__ and __doc__ and __text_signature__
        # from the original method and set it to the descriptor instance.
        wraps(method)(self)

    def __get__(self, instance, owner):
        return self.__class__(self.method, instance, owner)

    def __call__(self, *args, **kwargs):
        if self.instance:
            return self.method(self.instance, *args, **kwargs)
        return self.method(self.owner, *args, **kwargs)


class FallbackAdapter[ENUM_TYPE: enum.Enum]:  # type: ignore
    """Pydantic type adapter for fallback enums."""

    enable_type_casting: ClassVar[bool] | bool = True
    """Enable casting the value to the enum type."""

    casting_type: ClassVar[type | None] | type | None = None
    """Type to cast the value to."""

    unknown_name: ClassVar[str] | str = DEFAULT_UNKNOWN_NAME
    """Default name for unknown members."""

    def __init__(
        self,
        *,
        enable_type_casting: bool = True,
        casting_type: type | None = None,
        unknown_name: str = DEFAULT_UNKNOWN_NAME,
    ):
        """Initialize the adapter.

        Args:
            enable_type_casting: Enable casting the value to the enum type.
            casting_type: Type to cast the value to.
            unknown_name: Default name for unknown members.
        """
        self.enable_type_casting = enable_type_casting
        self.casting_type = casting_type
        self.unknown_name = unknown_name

    @_classinstancemethod
    def __get_pydantic_core_schema__(
        cls_or_self: type[Self] | Self,
        source_type: type[FallbackAdapter[ENUM_TYPE] | ENUM_TYPE],
        _handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """Pydantic auxiliary method to get schema.

        Args:
            source: Source field type.
            _handler: Handler of schema.

        Returns:
            Pydantic core schema.
        """
        enum_type = cls_or_self._get_enum_type(source_type)
        to_enum = cls_or_self._validator_factory(enum_type)

        strict_python_schema = core_schema.is_instance_schema(enum_type)
        to_enum_validator = core_schema.no_info_plain_validator_function(to_enum)

        if issubclass(enum_type, str):
            lax_schema = core_schema.chain_schema([core_schema.str_schema(), to_enum_validator])
            strict_schema = core_schema.json_or_python_schema(
                json_schema=core_schema.no_info_after_validator_function(to_enum, core_schema.str_schema()),
                python_schema=strict_python_schema,
            )
        elif issubclass(enum_type, int):
            lax_schema = core_schema.chain_schema([core_schema.int_schema(), to_enum_validator])
            strict_schema = core_schema.json_or_python_schema(
                json_schema=core_schema.no_info_after_validator_function(to_enum, core_schema.int_schema()),
                python_schema=strict_python_schema,
            )
        elif issubclass(enum_type, float):
            lax_schema = core_schema.chain_schema([core_schema.float_schema(), to_enum_validator])
            strict_schema = core_schema.json_or_python_schema(
                json_schema=core_schema.no_info_after_validator_function(to_enum, core_schema.float_schema()),
                python_schema=strict_python_schema,
            )
        else:
            lax_schema = to_enum_validator
            strict_schema = core_schema.json_or_python_schema(
                json_schema=to_enum_validator,
                python_schema=strict_python_schema,
            )

        return core_schema.lax_or_strict_schema(lax_schema=lax_schema, strict_schema=strict_schema)

    @_classinstancemethod
    def _validator_factory(
        cls_or_self: type[Self] | Self,
        enum_type: type[ENUM_TYPE],
    ) -> core_schema.NoInfoValidatorFunction:
        """Pydantic validator factory.

        Args:
            enum_type: Enum type.

        Returns:
            Pydantic validator with no info.
        """

        def validator(value) -> ENUM_TYPE:
            """Pydantic auxiliary validation method.

            Args:
                value: Value to validate.

            Raises:
                ValueError: If value is not valid snowflake.
            """
            if isinstance(value, enum_type):
                return value

            try:
                return enum_type(value)
            except ValueError:
                return _process_missing_member(
                    enum_type=enum_type,
                    value=value,
                    enable_type_casting=cls_or_self.enable_type_casting,
                    casting_type=cls_or_self.casting_type,
                    unknown_name=cls_or_self.unknown_name,
                )

        return validator

    @classmethod
    def _get_enum_type(cls, source_type: type[FallbackAdapter[ENUM_TYPE] | ENUM_TYPE]) -> type[ENUM_TYPE]:
        """Get enum type from the source type.

        Args:
            source_type: Source field type.

        Returns:
            Enum type.
        """

        origin = get_origin(source_type)

        # If the source type is FallbackAdapter, get the enum type from the generic args.
        if origin and issubclass(origin, FallbackAdapter):
            generic_args = get_args(source_type)
            if len(generic_args) != 1:
                raise ValueError(
                    'Please specify enum type in generic args. For example: FallbackAdapter[MyEnum]',
                )
            return generic_args[0]

        # If the source type is enum, return it.
        if issubclass(source_type, enum.Enum):
            return source_type

        raise ValueError(
            f'Please specify enum type in generic args. For example: {FallbackAdapter.__name__}[MyEnum]'
            + f' or use {FallbackAdapter.__name__} as a field type.'
            + f"For example: Annotated[MyEnum, {FallbackAdapter.__name__}(unknown_name='MISSING')]",
        )


if TYPE_CHECKING:
    # Type checking shold see in FallbackAdapter the same methods as in Enum
    # Neccessary for Pydantic models
    class FallbackAdapter[ENUM_TYPE: enum.Enum]:
        _name_: str
        _value_: Any
        _member_type_: type
        _member_map_: dict[str, Any]
        _member_names_: list[str]

        enable_type_casting: ClassVar[bool] | bool = True
        casting_type: ClassVar[type | None] | type | None = None
        unknown_name: ClassVar[str] | str = DEFAULT_UNKNOWN_NAME

        def __init__(
            self,
            *,
            enable_type_casting: bool = True,
            casting_type: type | None = None,
            unknown_name: str = DEFAULT_UNKNOWN_NAME,
        ):
            ...

        def name(self) -> str:
            ...

        def value(self) -> Any:
            ...

        def _generate_next_value_(
            name: str,
            start: int,
            count: int,
            last_values: list[Any],
        ) -> Any:
            ...

        @classmethod
        def _missing_(cls, value: Any) -> Any:
            ...

        @classmethod
        def __get_pydantic_core_schema__(
            cls,
            source_type: type[Self],
            _handler: GetCoreSchemaHandler,
        ) -> CoreSchema:
            ...

        @_classinstancemethod
        def _validator_factory(
            cls_or_self: type[Self] | Self, enum_type: type[ENUM_TYPE]
        ) -> core_schema.WithInfoValidatorFunction:
            ...
