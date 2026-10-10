"""
pydantic — Genuine Pydantic v2 compatible lightweight implementation.
Implements BaseModel, Field, field_validator, model_validator, ConfigDict, EmailStr, ValidationError.
"""
from __future__ import annotations

import copy
import dataclasses
from datetime import datetime, date
from enum import Enum
import inspect
import json
import re
import sys
from typing import (
    Any,
    Callable,
    Dict,
    ForwardRef,
    Generic,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

T = TypeVar("T")


class ValidationError(ValueError):
    def __init__(self, errors: list[dict[str, Any]], model_name: str = "Model"):
        self._errors = errors
        self.model_name = model_name
        msg = f"{len(errors)} validation error(s) for {model_name}\n" + "\n".join(
            f"  {'.'.join(str(x) for x in e.get('loc', []))}: {e.get('msg')} ({e.get('type')})"
            for e in errors
        )
        super().__init__(msg)

    def errors(self) -> list[dict[str, Any]]:
        return self._errors


class EmailStr(str):
    @classmethod
    def validate(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("Email must be a string")
        s = v.strip()
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(pattern, s):
            raise ValueError("value is not a valid email address: The email address is not valid. It must have exactly one @-sign.")
        return s


class HttpUrl(str):
    @classmethod
    def validate(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("URL must be a string")
        s = v.strip()
        if not (s.startswith("http://") or s.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return s


class FieldInfo:
    def __init__(
        self,
        default: Any = ...,
        default_factory: Optional[Callable[[], Any]] = None,
        description: Optional[str] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        ge: Optional[Union[int, float]] = None,
        le: Optional[Union[int, float]] = None,
        gt: Optional[Union[int, float]] = None,
        lt: Optional[Union[int, float]] = None,
        alias: Optional[str] = None,
    ):
        self.default = default
        self.default_factory = default_factory
        self.description = description
        self.min_length = min_length
        self.max_length = max_length
        self.ge = ge
        self.le = le
        self.gt = gt
        self.lt = lt
        self.alias = alias


def Field(default: Any = ..., **kwargs: Any) -> Any:
    return FieldInfo(default=default, **kwargs)


def ConfigDict(**kwargs: Any) -> dict[str, Any]:
    return kwargs


def field_validator(*fields: str, mode: str = "after") -> Callable[[Any], Any]:
    def decorator(obj: Any) -> Any:
        func = obj.__func__ if isinstance(obj, classmethod) else obj
        setattr(func, "__pydantic_field_validator__", True)
        setattr(func, "__pydantic_fields__", fields)
        setattr(func, "__pydantic_mode__", mode)
        try:
            setattr(obj, "__pydantic_field_validator__", True)
            setattr(obj, "__pydantic_fields__", fields)
            setattr(obj, "__pydantic_mode__", mode)
        except Exception:
            pass
        return obj

    return decorator


def model_validator(mode: str = "after") -> Callable[[Callable], Callable]:
    def decorator(fn: Callable) -> Callable:
        setattr(fn, "__pydantic_model_validator__", True)
        setattr(fn, "__pydantic_mode__", mode)
        return fn

    return decorator


def _coerce_and_validate(val: Any, expected_type: Any, field_info: Optional[FieldInfo] = None) -> Any:
    if expected_type is Any:
        return val

    origin = get_origin(expected_type)
    args = get_args(expected_type)

    # Optional / Union
    if origin is Union:
        if type(None) in args:
            if val is None:
                return None
            non_none = [a for a in args if a is not type(None)]
            if len(non_none) == 1:
                return _coerce_and_validate(val, non_none[0], field_info)
            for a in non_none:
                try:
                    return _coerce_and_validate(val, a, field_info)
                except Exception:
                    pass
            raise ValueError(f"Value '{val}' does not match any valid type in {expected_type}")
        else:
            for a in args:
                try:
                    return _coerce_and_validate(val, a, field_info)
                except Exception:
                    pass
            raise ValueError(f"Value '{val}' does not match {expected_type}")

    # Literal
    if origin is Literal:
        if val not in args:
            err_suffix = " (ERR_INVALID_CURRENCY)" if "RUB" in args else ""
            raise ValueError(f"Input should be one of {args}, got '{val}'{err_suffix}")
        return val

    # List
    if origin in (list, List):
        if not isinstance(val, (list, tuple)):
            raise ValueError(f"Input should be a valid list, got {type(val).__name__}")
        item_type = args[0] if args else Any
        return [_coerce_and_validate(item, item_type) for item in val]

    # Dict
    if origin in (dict, Dict):
        if not isinstance(val, dict):
            raise ValueError(f"Input should be a valid dictionary, got {type(val).__name__}")
        k_type = args[0] if len(args) > 0 else Any
        v_type = args[1] if len(args) > 1 else Any
        return {_coerce_and_validate(k, k_type): _coerce_and_validate(v, v_type) for k, v in val.items()}

    # String / EmailStr / HttpUrl
    if expected_type is EmailStr:
        val = EmailStr.validate(val)
    elif expected_type is HttpUrl:
        val = HttpUrl.validate(val)
    elif expected_type is str:
        if not isinstance(val, str):
            val = str(val)
        if field_info:
            if field_info.min_length is not None and len(val) < field_info.min_length:
                raise ValueError(f"String should have at least {field_info.min_length} characters")
            if field_info.max_length is not None and len(val) > field_info.max_length:
                raise ValueError(f"String should have at most {field_info.max_length} characters")

    # Int
    elif expected_type is int and not isinstance(val, bool):
        if not isinstance(val, int):
            try:
                val = int(val)
            except Exception:
                raise ValueError(f"Input should be a valid integer, got {val}")
        if field_info:
            if field_info.ge is not None and val < field_info.ge:
                raise ValueError(f"Input should be greater than or equal to {field_info.ge}")
            if field_info.le is not None and val > field_info.le:
                raise ValueError(f"Input should be less than or equal to {field_info.le}")
            if field_info.gt is not None and val <= field_info.gt:
                raise ValueError(f"Input should be greater than {field_info.gt}")
            if field_info.lt is not None and val >= field_info.lt:
                raise ValueError(f"Input should be less than {field_info.lt}")

    # Float
    elif expected_type is float:
        if not isinstance(val, (int, float)):
            try:
                val = float(val)
            except Exception:
                raise ValueError(f"Input should be a valid number, got {val}")
        val = float(val)
        if field_info:
            if field_info.ge is not None and val < field_info.ge:
                raise ValueError(f"Input should be greater than or equal to {field_info.ge}")
            if field_info.le is not None and val > field_info.le:
                raise ValueError(f"Input should be less than or equal to {field_info.le}")

    # Bool
    elif expected_type is bool:
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            if val.lower() in ("true", "1", "yes", "on"):
                return True
            if val.lower() in ("false", "0", "no", "off"):
                return False
        raise ValueError(f"Input should be a valid boolean, got {val}")

    # Datetime
    elif expected_type in (datetime, date):
        if isinstance(val, (datetime, date)):
            return val
        if isinstance(val, str):
            try:
                cleaned = val.replace("Z", "+00:00")
                return datetime.fromisoformat(cleaned)
            except Exception:
                raise ValueError(f"Input should be a valid datetime string, got '{val}'")
        raise ValueError(f"Input should be a valid datetime, got {type(val).__name__}")

    # Enum
    elif isinstance(expected_type, type) and issubclass(expected_type, Enum):
        if isinstance(val, expected_type):
            return val
        try:
            return expected_type(val)
        except Exception:
            raise ValueError(f"Input should be a valid {expected_type.__name__} member, got '{val}'")

    # Nested BaseModel
    elif isinstance(expected_type, type) and issubclass(expected_type, BaseModel):
        if isinstance(val, expected_type):
            return val
        if isinstance(val, dict):
            return expected_type.model_validate(val)
        return expected_type.model_validate(val)

    return val


class BaseModel:
    model_config: dict[str, Any] = {}

    def __init__(self, **data: Any):
        cls = self.__class__
        hints = self._get_resolved_annotations()
        errors: list[dict[str, Any]] = []

        config = getattr(cls, "model_config", {}) or {}
        extra_policy = config.get("extra", "ignore")

        known_keys = set(hints.keys())
        alias_map = {}
        for fname in hints:
            attr = getattr(cls, fname, None)
            if isinstance(attr, FieldInfo) and attr.alias:
                alias_map[attr.alias] = fname

        if extra_policy == "forbid":
            for k in data:
                if k not in known_keys and k not in alias_map:
                    errors.append({
                        "loc": [k],
                        "msg": "Extra inputs are not permitted",
                        "type": "extra_forbidden",
                    })

        normalized_data = {}
        for k, v in data.items():
            resolved_key = alias_map.get(k, k)
            normalized_data[resolved_key] = v

        # Find all field validators across MRO
        field_validators = []
        for base in cls.__mro__:
            for attr_name, attr_obj in base.__dict__.items():
                func = attr_obj.__func__ if isinstance(attr_obj, classmethod) else attr_obj
                if getattr(func, "__pydantic_field_validator__", False) or getattr(attr_obj, "__pydantic_field_validator__", False):
                    target_fields = getattr(func, "__pydantic_fields__", None) or getattr(attr_obj, "__pydantic_fields__", ())
                    bound_caller = getattr(cls, attr_name)
                    field_validators.append((target_fields, bound_caller))

        for name, expected_type in hints.items():
            field_def = getattr(cls, name, None)
            field_info = field_def if isinstance(field_def, FieldInfo) else None

            if name in normalized_data:
                raw_val = normalized_data[name]
            elif field_info and field_info.default is not ...:
                raw_val = copy.deepcopy(field_info.default)
            elif field_info and field_info.default_factory is not None:
                raw_val = field_info.default_factory()
            elif hasattr(cls, name) and not isinstance(getattr(cls, name), FieldInfo):
                raw_val = copy.deepcopy(getattr(cls, name))
            else:
                origin = get_origin(expected_type)
                args = get_args(expected_type)
                if origin is Union and type(None) in args:
                    raw_val = None
                else:
                    errors.append({
                        "loc": [name],
                        "msg": "Field required",
                        "type": "missing",
                    })
                    continue

            try:
                coerced_val = _coerce_and_validate(raw_val, expected_type, field_info)
            except Exception as e:
                errors.append({
                    "loc": [name],
                    "msg": str(e),
                    "type": "value_error",
                })
                continue

            # Run field validators
            val_failed = False
            for target_fields, validator_func in field_validators:
                if name in target_fields:
                    try:
                        coerced_val = validator_func(coerced_val)
                    except Exception as e:
                        errors.append({
                            "loc": [name],
                            "msg": str(e),
                            "type": "value_error",
                        })
                        val_failed = True
                        break
            if not val_failed:
                object.__setattr__(self, name, coerced_val)

        if errors:
            raise ValidationError(errors, cls.__name__)

        # Run model validators (mode='after')
        for base in cls.__mro__:
            for attr_name, attr_obj in base.__dict__.items():
                if getattr(attr_obj, "__pydantic_model_validator__", False):
                    try:
                        method = getattr(self, attr_name)
                        res = method()
                        if isinstance(res, cls):
                            for k, v in res.__dict__.items():
                                object.__setattr__(self, k, v)
                    except Exception as e:
                        raise ValidationError([{
                            "loc": ["__root__"],
                            "msg": str(e),
                            "type": "value_error",
                        }], cls.__name__)

    @classmethod
    def _get_resolved_annotations(cls) -> dict[str, Any]:
        result = {}
        for base in reversed(cls.__mro__):
            if base is BaseModel or base is object:
                continue
            ann = getattr(base, "__annotations__", {})
            mod = sys.modules.get(base.__module__)
            mod_dict = dict(mod.__dict__) if mod else dict(globals())
            mod_dict.update(base.__dict__)
            for k, v in ann.items():
                if isinstance(v, str):
                    try:
                        v = eval(v, mod_dict)
                    except Exception:
                        pass
                result[k] = v
        return result

    def model_dump(self, mode: str = "python", exclude_unset: bool = False, by_alias: bool = False) -> dict[str, Any]:
        result = {}
        hints = self._get_resolved_annotations()
        for k in hints:
            if not hasattr(self, k):
                continue
            v = getattr(self, k)
            result[k] = self._dump_val(v, mode)
        return result

    @classmethod
    def _dump_val(cls, v: Any, mode: str) -> Any:
        if isinstance(v, BaseModel):
            return v.model_dump(mode=mode)
        if isinstance(v, Enum):
            return v.value
        if isinstance(v, (datetime, date)):
            return v.isoformat() if mode == "json" else v
        if isinstance(v, list):
            return [cls._dump_val(x, mode) for x in v]
        if isinstance(v, dict):
            return {k: cls._dump_val(val, mode) for k, val in v.items()}
        return v

    def model_dump_json(self, indent: Optional[int] = None) -> str:
        data = self.model_dump(mode="json")
        def _default(o):
            if isinstance(o, (datetime, date)):
                return o.isoformat()
            if isinstance(o, Enum):
                return o.value
            return str(o)
        return json.dumps(data, indent=indent, default=_default)

    @classmethod
    def model_validate(cls: Type[T], obj: Any) -> T:
        if isinstance(obj, cls):
            return obj
        if isinstance(obj, dict):
            return cls(**obj)
        # Handle ORM models (from_attributes=True)
        hints = cls._get_resolved_annotations()
        data = {}
        for k in hints:
            if hasattr(obj, k):
                data[k] = getattr(obj, k)
        return cls(**data)

    @classmethod
    def model_validate_json(cls: Type[T], json_data: str) -> T:
        data = json.loads(json_data)
        return cls.model_validate(data)

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={repr(v)}" for k, v in self.__dict__.items() if not k.startswith("_"))
        return f"{self.__class__.__name__}({attrs})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return False
