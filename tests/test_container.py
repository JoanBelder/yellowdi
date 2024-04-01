from typing import Callable, TypedDict, Any, Literal, Annotated

import pytest

from yellowdi import Container, ResolveError, Token


class Call(TypedDict):
    args: list[Any]
    kwargs: dict[str, Any]


class record_calls:
    def __init__(self, function: Callable):
        self.calls: list[Call] = []
        self._function = function

    def __call__(self, *args, **kwargs):
        self.calls.append(
            {
                "args": args,
                "kwargs": kwargs,
            }
        )
        return self._function(*args, **kwargs)


class ForwardReferent: ...


def test_resolve_auto_no_dependencies() -> None:
    class T: ...

    container = Container()
    assert isinstance(container.resolve(T), T)


def test_resolve_with_register_invokes_the_factory() -> None:
    class T: ...

    container = Container()

    @record_calls
    def resolve():
        return T()

    container.register(T, resolve)
    assert isinstance(container.resolve(T), T)
    assert isinstance(container.resolve(T), T)
    assert len(resolve.calls) == 2


def test_resolve_with_register_value() -> None:
    class T: ...

    container = Container()
    instance = T()
    container.register_value(T, instance)
    assert container.resolve(T) is instance


def test_cannot_resolve_when_type_is_missing() -> None:
    class T:
        def __init__(self, _a):
            pass

    container = Container()
    with pytest.raises(ResolveError):
        container.resolve(T)


def test_can_resolve_when_type_is_missing_but_default_value_exists() -> None:
    class T:
        def __init__(self, _a=None): ...

    container = Container()
    assert isinstance(container.resolve(T), T)


def test_cannot_resolve_literals() -> None:
    class T:
        def __init__(self, a: Literal[0]): ...

    container = Container()
    with pytest.raises(ResolveError):
        container.resolve(T)


def test_cannot_resolve_literals_as_annotated() -> None:
    class T:
        def __init__(self, a: Annotated[Literal[0], ""]): ...

    container = Container()
    with pytest.raises(ResolveError):
        container.resolve(T)


def test_resolve_dependency_chain() -> None:
    class Registered: ...

    class Inner:
        def __init__(self, registered: Registered):
            self.registered = registered

    class Outer:
        def __init__(self, inner: Inner):
            self.inner = inner

    container = Container()
    registered_value = Registered()
    container.register_value(Registered, registered_value)
    outer = container.resolve(Outer)
    assert isinstance(outer, Outer)
    assert outer.inner.registered == registered_value


def test_resolve_module_forward_referred_class() -> None:
    class T:
        def __init__(self, registered: "ForwardReferent"):
            self.registered = registered

    assert isinstance(Container().resolve(T).registered, ForwardReferent)


def test_resolve_module_forward_referred_class_annotated() -> None:
    class T:
        def __init__(self, registered: Annotated["ForwardReferent", ""]):
            self.registered = registered

    assert isinstance(Container().resolve(T).registered, ForwardReferent)


@pytest.mark.parametrize(
    "to_resolve",
    [
        pytest.param("a-string", id="str"),
        pytest.param(0, id="int"),
        pytest.param((lambda: 0), id="function"),
        pytest.param([], id="list"),
        pytest.param({}, id="dict"),
    ],
)
def test_must_resolve_classes(to_resolve) -> None:
    container = Container()
    with pytest.raises(ResolveError):
        container.resolve(to_resolve)


def test_resolve_module_local_referent_fails() -> None:
    class T:
        def __init__(self, registered: "LocalReferent"):
            self.registered = registered

    class LocalReferent: ...

    with pytest.raises(ResolveError):
        Container().resolve(T)


def test_resolve_with_parameters() -> None:
    class Inner: ...

    class T:
        def __init__(self, a, /, b, *args, c, inner_from_container: Inner, **kwargs):
            self.a = a
            self.b = b
            self.c = c
            self.inner_from_container = inner_from_container
            self.args = args
            self.kwargs = kwargs

    container = Container()
    inner = Inner()
    container.register_value(Inner, inner)
    resolved = container.resolve(T, 1, 2, 5, 6, c=3, named="test")
    assert resolved.__dict__ == {
        "a": 1,
        "b": 2,
        "c": 3,
        "inner_from_container": inner,
        "args": (5, 6),
        "kwargs": {"named": "test"},
    }


def test_can_resolve_registered_class_with_metaclass() -> None:
    class Meta(type): ...

    class Base(metaclass=Meta): ...

    class Child(Base): ...

    container = Container()
    container.register(Child, Child)
    assert isinstance(container.resolve(Child), Child)


def test_cannot_auto_resolve_metaclassed_objects() -> None:
    class Meta(type): ...

    class Base(metaclass=Meta): ...

    class Child(Base): ...

    container = Container()
    with pytest.raises(ResolveError):
        container.resolve(Child)


def test_can_register_aliases():
    class Protocol:
        def something(self): ...

    class Implementer:
        def something(self): ...

    container = Container()
    container.register_alias(Protocol, Implementer)
    assert isinstance(container.resolve(Protocol), Implementer)


def test_can_resolve_annotated() -> None:
    test_value = "abcdefgh"

    class T:
        def __init__(self, resolved_value: Annotated[Any, Token("A")]):
            self.resolved_value = resolved_value

    container = Container()
    container.register_value(Token("A"), test_value)
    resolved_instance = container.resolve(T)

    assert isinstance(resolved_instance, T)
    assert resolved_instance.resolved_value == test_value


def test_will_fallback_to_type_when_token_is_unknown() -> None:
    class Inner: ...

    class T:
        def __init__(self, resolved_value: Annotated[Inner, Token("A")]):
            self.resolved_value = resolved_value

    resolved_instance = Container().resolve(T)

    assert isinstance(resolved_instance, T)
    assert isinstance(resolved_instance.resolved_value, Inner)


def test_will_fallback_to_first_known_token() -> None:
    class T:
        def __init__(
            self, resolved_value: Annotated[Any, Token("A"), Token("B"), Token("C")]
        ):
            self.resolved_value = resolved_value

    container = Container()
    container.register_value(Token("B"), "b")
    container.register_value(Token("C"), "c")
    resolved_instance = container.resolve(T)

    assert isinstance(resolved_instance, T)
    assert resolved_instance.resolved_value == "b"
