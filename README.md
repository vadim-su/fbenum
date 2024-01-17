# FBEnum

Enhance your enums with robust classes that gracefully handle unknown values
through a fallback mechanism, fully compatible with Pydantic.

It can be helpful to have a fallback value for enums, so that unknown values can be
handled gracefully. This is especially useful when working with external data sources
that may contain values that are not known at the time of writing the code.

## Installation

```bash
pip install fbenum
```

## Usage

`fbenum` provides two possible ways to use it:

- As a class mixin, which can be used to enhance any enum class
- As a pydantic validator, which can be used to validate enum values in pydantic models

### Class mixin

Class mixin can be used to enhance any enum class with fallback functionality.
It
```python
from enum import Enum
from fbenum.enum import FallbackEnum

@enum.unique
class MyEnum(enum.StrInt, FallbackEnum):
    __unknown_name__ = 'MISSING'

    A = 1
    B = 2

assert MyEnum(1) == MyEnum.A
assert MyEnum(44).name == 'MISSING'
assert MyEnum(44).value == 44
```

### Pydantic validator

As a pydantic validator, `fbenum` can be used to validate enum values in pydantic models.
In this cases, the enum class no longer needs to be a subclass of `FallbackEnum` or somehow
otherwise enhanced.
Two ways of using it are provided:

#### Annotated type validator

```python
from enum import Enum
from fbenum.adapter import FallbackAdapter

@enum.unique
class MyEnum(enum.StrInt):
    A = 1
    B = 2

class MyModel(BaseModel):
    value: Annotated[
        MyEnum, FallbackAdapter(unknown_name='MISSING'),
    ]

model = MyModel(value=1)
assert model.value == MyEnum.A

model = MyModel(value=44)
assert model.value.name == 'MISSING'
assert model.value.value == 44
```

#### Type wrapper

Type wrapper has restricted functionality, as it can only be used to wrap a single enum
class, and it does not support any additional arguments. However, it is more concise.

```python
from enum import Enum
from fbenum.adapter import FallbackAdapter

@enum.unique
class MyEnum(enum.StrInt):
    A = 1
    B = 2

class MyModel(BaseModel):
    value: FallbackAdapter[MyEnum]

model = MyModel(value=1)
assert model.value == MyEnum.A

model = MyModel(value=44)
assert model.value.name == 'MISSING'
assert model.value.value == 44
```


##### Or a more realistic and complex example:

```python
from enum import Enum
from fbenum.adapter import FallbackAdapter


@enum.unique
class UserStatus(enum.StrInt):
    """User status."""
    ACTIVE = 1
    INACTIVE = 2


class UserRequest(BaseModel):
    name: str
    email: str
    status: FallbackAdapter[UserStatus]


class UserResponse(BaseModel):
    name: str
    email: str
    status: FallbackAdapter[UserStatus]


def create_user(request: UserRequest) -> UserResponse:
    """Create a user."""
    # Do some stuff
    resp = ...
    return UserResponse.validate_model(resp)


def get_user(user_id: int) -> UserResponse:
    """Get a user."""
    # Do some stuff
    resp = ...
    return UserResponse.validate_model(resp)


def get_users() -> list[UserResponse]:
    """Get all users."""
    # Do some stuff
    resp = ...
    return UserResponse.validate_model(resp)


if __name__ == '__main__':
    user = create_user(
        UserRequest(
            name='John Doe',
            email='test@emaik.com',
            status=1,
        ),
    )
    # on user cretion status always will be known

    users = get_users()
    # on users_getting status can be unknown, so using fallback wrapper for response
    # model will be a good idea to handle unknown values gracefully.
```
