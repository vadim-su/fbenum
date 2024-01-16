"""Base class for enums that return a pseudo-member for unknown values.

It can be used to represent values from an API.

Example:

    >>> import enum
    >>> from fbenum import FallbackEnum
    ...
    >>> class UserStatus(enum.IntEnum, FallbackEnum):
    ...     ACTIVE = 1
    ...     INACTIVE = 2
    ...
    >>> class User(BaseModel):
    ...     status: UserStatus
    ...
    >>> User(status=1)
    User(status=<UserStatus.ACTIVE: 1>)
    >>> User(status=3)
    User(status=<UserStatus.UNKNOWN: 3>)
"""

from __future__ import annotations

import enum
from typing import Final

DEFAULT_UNKNOWN_NAME: Final[str] = 'UNKNOWN'


class FallbackEnum(enum.Enum):
    """Enum that returns a pseudo-member for unknown values.

    This is useful for enums that are used to represent values from an API.
    Sometimes, the API will return a value that is not in the enum (and docs).
    """

    __unknown_name__: str
    """Default name for unknown members."""

    __enable_type_casting__: bool
    """Enable casting the value to the enum type."""

    __casting_type__: type | None
    """Type to cast the value to.

    If None, the enum type is used. For example, if the enum is a subclass of str (enum.StrEnum),
    the value will be cast to str.
    If not None, the value will be cast to the given type.
    """

    @classmethod
    def _missing_(cls, value) -> FallbackEnum:
        """Return a pseudo-member for the given value if no other member matches.

        This is called by the enum metaclass when no other member matches.
        See how enum.Flag handles unknown values.
        """
        return _process_missing_member(
            enum_type=cls,
            value=value,
            enable_type_casting=cls.__enable_type_casting__,
            casting_type=cls.__casting_type__,
            unknown_name=cls.__unknown_name__,
        )

    @property
    def is_unknown(self) -> bool:
        """Return True if this is an unknown member."""
        return self.name == self.__unknown_name__


def _process_missing_member[ENUM_TYPE: enum.Enum](
    enum_type: type[ENUM_TYPE],
    value,
    enable_type_casting: bool,
    casting_type: type | None = None,
    unknown_name: str = DEFAULT_UNKNOWN_NAME,
) -> ENUM_TYPE:
    """Return a pseudo-member for the given value if no other member matches.

    This is called by the enum metaclass when no other member matches.
    See how enum.Flag handles unknown values.
    """
    if enable_type_casting:
        cast_type = _get_cast_type(enum_type, casting_type)
        if cast_type is not None and not isinstance(value, cast_type):
            try:
                value = cast_type(value)
                return enum_type(value)
            except ValueError:
                # The value can't be cast to the enum type or member
                # with the casted value doesn't exist
                pass

    if enum_type._member_type_ is object:  # type: ignore
        pseudo_member = object.__new__(enum_type)
    else:
        pseudo_member = enum_type._member_type_.__new__(enum_type, value)  # type: ignore

    if not hasattr(pseudo_member, '_value_'):
        pseudo_member._value_ = value

    pseudo_member._name_ = unknown_name
    return pseudo_member


def _get_cast_type(enum_type: type[enum.Enum], casting_type: type | None = None) -> type | None:
    """Return the type to cast the value to."""
    if casting_type:
        return casting_type

    if issubclass(enum_type, str):
        return str

    if issubclass(enum_type, int):
        return int

    if issubclass(enum_type, float):
        return float

    return None


# Initialize the class attributes
# Can't be set directly in the class definition because of an Enum metaclass behavior
FallbackEnum.__unknown_name__ = DEFAULT_UNKNOWN_NAME
FallbackEnum.__enable_type_casting__ = True
FallbackEnum.__casting_type__ = None
