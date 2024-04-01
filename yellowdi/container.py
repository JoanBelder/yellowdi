import inspect
import typing
from inspect import Parameter
from typing import (
    TypeVar,
    Callable,
    Literal,
    ParamSpec,
    final,
    Annotated,
    get_args,
    ForwardRef,
)
from collections.abc import Hashable

T = TypeVar("T")
P = ParamSpec("P")


class ResolveError(TypeError):
    def __init__(self, *args):
        super().__init__(*args)


@final
class Token:
    _tokens: dict[str, "Token"] = {}

    def __init__(self, name: str | None = None):
        self.name = name

    def __new__(cls, name: str | None = None) -> "Token":
        if name is None:
            return super().__new__(cls)
        if name not in cls._tokens:
            cls._tokens[name] = super().__new__(cls)
        return cls._tokens[name]

    def __class_getitem__(cls, item: str) -> "Token":
        return cls(item)


class Container:
    def __init__(self):
        self._registrations = {}

    def resolve(self, _type: type[T], *args: P.args, **kwargs: P.kwargs) -> T:
        if not isinstance(_type, Hashable):
            raise ResolveError("Can only resolve classes")
        if not inspect.isclass(_type):
            raise ResolveError("Can only resolve classes")

        if _type in self._registrations:
            return self._registrations[_type]()

        if type(_type) is not type:
            raise ResolveError("Cannot auto-resolve classes with custom meta-class")

        bound = inspect.signature(_type.__init__).bind_partial(None, *args, **kwargs)
        for parameter in bound.signature.parameters.values():
            if parameter.name not in bound.arguments:
                bound.arguments[parameter.name] = self._resolve_argument(
                    _type, parameter
                )

        return _type(*bound.args[1:], **bound.kwargs)

    def _resolve_argument(self, _type: type[T], argument: Parameter) -> typing.Any:
        if argument.default is not Parameter.empty:
            return argument.default
        if argument.kind is Parameter.VAR_POSITIONAL:
            return ()
        if argument.kind is Parameter.VAR_KEYWORD:
            return {}
        type_annotation = argument.annotation

        if type_annotation is Parameter.empty:
            raise ResolveError(
                f"Cannot resolve argument {argument.name} for {_type.__name__}: no type annotation"
            )
        if typing.get_origin(type_annotation) is Annotated:
            annotations = get_args(type_annotation)
            type_annotation = annotations[0]

            for annotation in annotations[1:]:
                if isinstance(annotation, Token) and annotation in self._registrations:
                    return self._registrations[annotation]()

        if typing.get_origin(type_annotation) is Literal:
            raise ResolveError(
                f"Cannot resolve argument {argument.name} for {_type.__name__}: literal"
            )
        if isinstance(type_annotation, str):
            return self._resolve_forward_declaration(
                _type, argument.name, type_annotation
            )
        if isinstance(type_annotation, ForwardRef):
            return self._resolve_forward_declaration(
                _type, argument.name, type_annotation.__forward_arg__
            )
        return self.resolve(type_annotation)

    def _resolve_forward_declaration(
        self, _type: type[T], argument_name: str, class_name: str
    ) -> typing.Any:
        try:
            resolved_type = getattr(inspect.getmodule(_type), class_name)
        except AttributeError:
            raise ResolveError(
                f"Cannot resolve argument {argument_name} for {_type.__name__}: "
                "class declaration not available in module"
            )
        return self.resolve(resolved_type)

    def register_value(self, _type: type[T] | Token, value: T) -> None:
        self.register(_type, lambda: value)

    def register(self, _type: type[T] | Token, factory: Callable[[], T]) -> None:
        self._registrations[_type] = factory

    def register_alias(self, _type: type[T], alias: type[T]) -> None:
        self.register(_type, lambda: self.resolve(alias))
