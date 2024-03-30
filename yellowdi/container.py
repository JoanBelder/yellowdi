import inspect
import typing
from inspect import Parameter
from typing import TypeVar, Callable, Literal, ParamSpec
from collections.abc import Hashable

T = TypeVar("T")
P = ParamSpec("P")


class ResolveError(TypeError):
    def __init__(self, *args):
        super().__init__(*args)


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
        if argument.annotation is Parameter.empty:
            raise ResolveError(
                f"Cannot resolve argument {argument.name} for {_type.__name__}: no type annotation"
            )
        if typing.get_origin(argument.annotation) is Literal:
            raise ResolveError(
                f"Cannot resolve argument {argument.name} for {_type.__name__}: literal"
            )

        if isinstance(argument.annotation, str):
            return self._resolve_forward_declaration(_type, argument)
        return self.resolve(argument.annotation)

    def _resolve_forward_declaration(
        self, _type: type[T], argument: Parameter
    ) -> typing.Any:
        try:
            resolved_type = getattr(inspect.getmodule(_type), argument.annotation)
        except AttributeError:
            raise ResolveError(
                f"Cannot resolve argument {argument.name} for {_type.__name__}: "
                "class declaration not available in module"
            )
        return self.resolve(resolved_type)

    def register_value(self, _type: type[T], value: T) -> None:
        self.register(_type, lambda: value)

    def register(self, _type: type[T], factory: Callable[[], T]) -> None:
        self._registrations[_type] = factory

    def register_protocol(self, _type: type[T], value: type[T]) -> None:
        self.register(_type, lambda: self.resolve(value))
