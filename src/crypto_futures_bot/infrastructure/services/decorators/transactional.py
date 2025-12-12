from collections.abc import Callable
from functools import wraps
from inspect import Signature, _empty, signature
from types import UnionType
from typing import Any, Union, get_args, get_origin

from sqlalchemy.ext.asyncio import AsyncSession


class transactional:
    def __init__(self, read_only: bool = False) -> None:
        self._read_only = read_only

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        self._func = func
        self._init_session_kwarg_name()

        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            session_kwarg_value = kwargs.get(self._session_kwarg_name)
            if session_kwarg_value is not None:
                result = await func(*args, **kwargs)
            else:
                from crypto_futures_bot.config.dependencies import get_application_container

                application_container = get_application_container()
                sessionmaker = application_container.infrastructure_container().database_container().sessionmaker()
                if not self._read_only:
                    sessionmaker = sessionmaker.begin
                async with sessionmaker() as session:
                    result = await func(*args, **{**kwargs, self._session_kwarg_name: session})
            return result

        return wrapper

    def _init_session_kwarg_name(self) -> str | None:
        func_signature: Signature = signature(self._func)
        func_parameters = list(func_signature.parameters.items())
        self._session_kwarg_name = None
        idx = 0
        while self._session_kwarg_name is None and idx < len(func_parameters):
            arg_name, arg_signature = func_parameters[idx]
            arg_type = arg_signature.annotation
            if self._is_optional_parameter(arg_type):
                arg_type, *_ = (
                    arg
                    for arg in get_args(arg_type)
                    if arg is not type(None)  # noqa: E721
                )
            if arg_type is AsyncSession:
                self._session_kwarg_name = arg_name
            idx += 1

        if self._session_kwarg_name is None:
            raise ValueError(
                f"function {repr(self._func)} must declare a 'sqlalchemy.orm.Session' "
                "or 'sqlalchemy.ext.asyncio.AsyncSession' parameter (as simple arg or kwarg) "
                "for using @Transactional decorator!"
            )

    def _is_optional_parameter(self, param_type: type[_empty] | Any) -> bool:
        """
            Checks if a type hint is Optional[T] or Union[..., None, ...] or "T | None"

            Args:
                param (Parameter): The checked parameters

        Returns:
            bool: True if it is an optional parameters. Otherwise, returns False
        """
        is_optional_parameter = False
        if self._is_union_type(param_type):
            param_type_args = get_args(param_type)
            if any(param_type_arg is type(None) for param_type_arg in param_type_args):  # noqa
                is_optional_parameter = True
        return is_optional_parameter

    def _is_union_type(self, param_type: type[_empty] | Any) -> bool:
        origin = get_origin(param_type)
        param_type_origin = origin if origin else param_type
        return param_type_origin is Union or param_type_origin is UnionType  # noqa
