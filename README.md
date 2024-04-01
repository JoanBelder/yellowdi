# Yellow DI

A dependency injection for python. That will automatically resolve dependencies based on type
and optionally dependency injection tokens. The library has been designed with the following
ideas in mind:

- Simple API
- Can work with third party classes, without modifying these classes
- Type annotations by default, or optional tokens.
- Resolve types based on partial information. You can provide partial construction arguments
  to a class and let the container figure the rest out.


## Example usage
```python
from typing import Annotated

from yellowdi import yellowdi, Token

## During setup
yellowdi.register(DbConnection, lambda: createConnection("username", "password"))
yellowdi.register_value(Token("UserTable"), "users")

# During usage
class ExampleUsersRepository():
    def __init__(self, connection: DbConnection, table: Annotated[str, Token("UserTable")]):
        ...
    
class ExampleClass():
    def __init__(self, users: ExampleUsersRepository):
        ...

yellowdi.resolve(ExampleClass) # Fully created instance of ExampleClass
```

## API Documentation

### `Container()`
This represents an dependency injection container. The container takes no arguments for initialization.
For convenience also a global container is provided by the `yellowdi` import.

```python
from yellowdi import yellowdi, Container

mycontainer = Container()  # Create a new empty container
isinstance(yellowdi, Container) # True, a global container provided for convenience.
```

It has the following methods:

#### `register_value(type_: Type|Token, value: Any) -> None`
Bind a value to class or token. When the container needs to resolve this class or token it will always resolve with the
given `value`. The same value is used, also when multiple resolutions are needed, effectively using this type as
a singleton in the application.

#### `register(type_: Type|Token, factory: Callable[[], Any]) -> None`
Bind a factory to a class or token.  Whenever the container needs to resolve this class it will invoke the given factory
function. The factory function is not allowed to take any arguments. The factory function will be invoked every time it
is needed for resolution. If this unwanted behavior you can wrap the factory method with 
[`functools.cache`](https://docs.python.org/3/library/functools.html#functools.cache)
or consider using `register_value` instead.

```python
def example_factory():
   return someclass_instance

yellowdi.register(SomeClass, example_factory)
```

#### `resolve(type_: type[T], *args, **kwargs) -> T`
Starts the resolution of a class. If the class is known already it will use the registered value. In any other case the
container will inspect the arguments of the `__init__` method of the given class and try to resolve each argument, apply the
`*args*` and `**kwargs**` to the resolve method. If there are still arguments to resolve they will be recursively tried to be
resolved by the container, and the new instance is returned. When it fails a `ResolveError` will be raised.

##### Resolution order or injecting argument values

Resolution of arguments for an object or call will be done in the following order.
1. When provided as an `arg` or `kwarg` in the [`resolve`](#resolvetype_-typet---t) method.
2. When present in the function signature: The default value of the argument.
3. When the type is annotated with an injection token. And the token is registered in the container.
4. Based on the type annotation of the argument.
5. If none of the above, an error is given.

### `Token(name: str|None)`
Tokens represent injection tokens. They can be used as values for `container.register_value` and `container.register`.
Constructing a token with the same name twice will result in the same token. Which is making it more convenient for 
annotating types. However when the name is omitted a new token is always constructed.

```python
# Constructing named tokens with the same name multiple times results in the same object.
Token("A") is Token("A")  # True
Token("B") is Token("B")  # True
Token("A") is not Token("B")  # True

# This does not hold for tokens without a name
Token() is not Token() # True
```

Tokens can provided to an argument using [`typing.Annotated`](https://docs.python.org/3/library/typing.html#typing.Annotated). For example:
```python
class MyClass:
  def __init__(self, my_type: Annotated[Any, Token("MyToken")]):
     ...
```

It is allowed to provide multiple tokens. When `conainer.resolve` is invoked. It will first check if `Token("FirstChoice")` is registered. If this 
is the case this token will be used for resolution, otherwise it will continue with checking for `Token("SecondChoice")` and so on. The order of
resolution is always the same provided in the `Annotated` block.
```python
class MyClass:
  def __init__(self, my_type: Annotated[Any, Token("FirstChoice"), Token("SecondChoice"), Token("FinalChoice")]):
     ...
```
