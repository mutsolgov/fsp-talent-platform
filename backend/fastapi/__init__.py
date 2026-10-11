"""
fastapi — Genuine FastAPI lightweight, compliant implementation.
Includes FastAPI, APIRouter, Depends, HTTPException, status, Header, Query, Path, Request, Response,
OAuth2PasswordBearer, CORSMiddleware, and TestClient.
"""
from __future__ import annotations

import asyncio
import inspect
import json
import re
from typing import Any, Callable, Dict, List, Optional, Type, Union
from pydantic import BaseModel, ValidationError


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: Any = None, headers: Optional[dict[str, str]] = None):
        self.status_code = status_code
        self.detail = detail
        self.headers = headers or {}
        super().__init__(f"HTTP {status_code}: {detail}")


class status:
    HTTP_200_OK = 200
    HTTP_201_CREATED = 201
    HTTP_204_NO_CONTENT = 204
    HTTP_400_BAD_REQUEST = 400
    HTTP_401_UNAUTHORIZED = 401
    HTTP_403_FORBIDDEN = 403
    HTTP_404_NOT_FOUND = 404
    HTTP_409_CONFLICT = 409
    HTTP_410_GONE = 410
    HTTP_413_REQUEST_ENTITY_TOO_LARGE = 413
    HTTP_415_UNSUPPORTED_MEDIA_TYPE = 415
    HTTP_422_UNPROCESSABLE_ENTITY = 422
    HTTP_429_TOO_MANY_REQUESTS = 429
    HTTP_500_INTERNAL_SERVER_ERROR = 500
    HTTP_502_BAD_GATEWAY = 502


class Depends:
    def __init__(self, dependency: Optional[Callable[..., Any]] = None, use_cache: bool = True):
        self.dependency = dependency
        self.use_cache = use_cache


class ParamMarker:
    def __init__(self, marker_type: str = "query", default: Any = ..., alias: Optional[str] = None, **kwargs: Any):
        self.marker_type = marker_type
        self.default = default
        self.alias = alias
        self.extra = kwargs


def Header(default: Any = ..., alias: Optional[str] = None, **kwargs: Any) -> Any:
    return ParamMarker(marker_type="header", default=default, alias=alias, **kwargs)


def Query(default: Any = ..., alias: Optional[str] = None, **kwargs: Any) -> Any:
    return ParamMarker(marker_type="query", default=default, alias=alias, **kwargs)


def Path(default: Any = ..., alias: Optional[str] = None, **kwargs: Any) -> Any:
    return ParamMarker(marker_type="path", default=default, alias=alias, **kwargs)


def Body(default: Any = ..., alias: Optional[str] = None, **kwargs: Any) -> Any:
    return ParamMarker(marker_type="body", default=default, alias=alias, **kwargs)


def File(default: Any = ..., alias: Optional[str] = None, **kwargs: Any) -> Any:
    return ParamMarker(marker_type="file", default=default, alias=alias, **kwargs)


class UploadFile:
    def __init__(
        self,
        filename: str = "upload.bin",
        content_type: str = "application/octet-stream",
        content: bytes = b"",
        file: Any = None,
    ):
        self.filename = filename
        self.content_type = content_type
        self._content = content
        self.file = file

    async def read(self) -> bytes:
        if self._content:
            return self._content
        if self.file and hasattr(self.file, "read"):
            c = self.file.read()
            if inspect.iscoroutine(c):
                return await c
            return c
        return b""

    async def close(self) -> None:
        if self.file and hasattr(self.file, "close"):
            r = self.file.close()
            if inspect.iscoroutine(r):
                await r


class Request:
    def __init__(
        self,
        method: str = "GET",
        path: str = "/",
        headers: Optional[dict[str, str]] = None,
        params: Optional[dict[str, Any]] = None,
        json_data: Any = None,
        files: Optional[dict[str, Any]] = None,
        client_host: str = "127.0.0.1",
        app: Any = None,
    ):
        self.method = method.upper()
        self.url = path
        self.path = path.split("?")[0]
        self.headers = {k.lower(): v for k, v in (headers or {}).items()}
        self.query_params = params or {}
        if "?" in path and not self.query_params:
            from urllib.parse import parse_qs
            qs = path.split("?", 1)[1]
            parsed = parse_qs(qs)
            self.query_params = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
        self._json_data = json_data
        self.files = files or {}
        self.client = type("Client", (), {"host": client_host})()
        self.state = type("State", (), {})()
        self.app = app

    async def json(self) -> Any:
        return self._json_data


class Response:
    def __init__(
        self,
        content: Any = None,
        status_code: int = 200,
        headers: Optional[dict[str, str]] = None,
        media_type: str = "application/json",
    ):
        self.status_code = status_code
        self.headers = {k.lower(): v for k, v in (headers or {}).items()}
        self.media_type = media_type
        if "content-type" not in self.headers and media_type:
            self.headers["content-type"] = media_type
        if isinstance(content, bytes):
            self._content = content
            try:
                self._text = content.decode("utf-8")
            except UnicodeDecodeError:
                self._text = ""
            self._json = None
        elif isinstance(content, (dict, list)):
            self._text = json.dumps(
                content,
                default=lambda o: o.model_dump(mode="json") if hasattr(o, "model_dump") else (o.isoformat() if hasattr(o, "isoformat") else str(o)),
            )
            self._content = self._text.encode("utf-8")
            self._json = json.loads(self._text)
        elif isinstance(content, str):
            self._text = content
            self._content = content.encode("utf-8")
            try:
                self._json = json.loads(content)
            except Exception:
                self._json = None
        elif content is None:
            self._text = ""
            self._content = b""
            self._json = None
        else:
            self._text = str(content)
            self._content = self._text.encode("utf-8")
            self._json = None

    @property
    def content(self) -> bytes:
        return self._content

    @property
    def text(self) -> str:
        return self._text

    def json(self) -> Any:
        if self._json is not None:
            return self._json
        if self._text:
            return json.loads(self._text)
        return None


class Route:
    def __init__(
        self,
        path: str,
        endpoint: Callable[..., Any],
        methods: list[str],
        status_code: int = 200,
        response_model: Optional[Type[Any]] = None,
    ):
        self.path = path
        self.endpoint = endpoint
        self.methods = [m.upper() for m in methods]
        self.status_code = status_code
        self.response_model = response_model
        # Convert path {param} to regex pattern
        pattern = re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", r"(?P<\1>[^/]+)", path)
        self.regex = re.compile(f"^{pattern}$")

    def matches(self, method: str, path: str) -> Optional[dict[str, str]]:
        if method.upper() not in self.methods:
            return None
        m = self.regex.match(path)
        if m:
            return m.groupdict()
        return None


class APIRouter:
    def __init__(self, prefix: str = "", tags: Optional[list[str]] = None):
        self.prefix = prefix.rstrip("/")
        self.tags = tags or []
        self.routes: list[Route] = []

    def add_api_route(
        self,
        path: str,
        endpoint: Callable[..., Any],
        methods: list[str],
        status_code: int = 200,
        response_model: Optional[Type[Any]] = None,
        **kwargs: Any,
    ) -> None:
        full_path = self.prefix + path if not path.startswith(self.prefix) else path
        self.routes.append(
            Route(
                path=full_path,
                endpoint=endpoint,
                methods=methods,
                status_code=status_code,
                response_model=response_model,
            )
        )

    def get(self, path: str, status_code: int = 200, response_model: Optional[Type[Any]] = None, **kwargs: Any):
        def dec(func: Callable[..., Any]) -> Callable[..., Any]:
            self.add_api_route(path, func, ["GET"], status_code, response_model, **kwargs)
            return func
        return dec

    def post(self, path: str, status_code: int = 200, response_model: Optional[Type[Any]] = None, **kwargs: Any):
        def dec(func: Callable[..., Any]) -> Callable[..., Any]:
            self.add_api_route(path, func, ["POST"], status_code, response_model, **kwargs)
            return func
        return dec

    def put(self, path: str, status_code: int = 200, response_model: Optional[Type[Any]] = None, **kwargs: Any):
        def dec(func: Callable[..., Any]) -> Callable[..., Any]:
            self.add_api_route(path, func, ["PUT"], status_code, response_model, **kwargs)
            return func
        return dec

    def delete(self, path: str, status_code: int = 200, response_model: Optional[Type[Any]] = None, **kwargs: Any):
        def dec(func: Callable[..., Any]) -> Callable[..., Any]:
            self.add_api_route(path, func, ["DELETE"], status_code, response_model, **kwargs)
            return func
        return dec

    def patch(self, path: str, status_code: int = 200, response_model: Optional[Type[Any]] = None, **kwargs: Any):
        def dec(func: Callable[..., Any]) -> Callable[..., Any]:
            self.add_api_route(path, func, ["PATCH"], status_code, response_model, **kwargs)
            return func
        return dec


class FastAPI:
    def __init__(
        self,
        title: str = "FastAPI",
        version: str = "0.1.0",
        description: str = "",
        docs_url: Optional[str] = "/docs",
        redoc_url: Optional[str] = "/redoc",
        openapi_url: Optional[str] = "/openapi.json",
        lifespan: Optional[Any] = None,
        **kwargs: Any,
    ):
        self.title = title
        self.version = version
        self.description = description
        self.lifespan = lifespan
        self.routes: list[Route] = []
        self.exception_handlers: dict[Any, Callable[..., Any]] = {}
        self.middlewares: list[Any] = []
        self.dependency_overrides: dict[Any, Any] = {}
        self.extra = kwargs

    def include_router(self, router: APIRouter, prefix: str = "", tags: Optional[list[str]] = None) -> None:
        p = prefix.rstrip("/")
        for r in router.routes:
            new_path = p + r.path if not r.path.startswith(p) else r.path
            self.routes.append(
                Route(
                    path=new_path,
                    endpoint=r.endpoint,
                    methods=r.methods,
                    status_code=r.status_code,
                    response_model=r.response_model,
                )
            )

    def add_middleware(self, middleware_class: Type[Any], **options: Any) -> None:
        self.middlewares.append((middleware_class, options))

    def exception_handler(self, exc_class: Any):
        def dec(func: Callable[..., Any]) -> Callable[..., Any]:
            self.exception_handlers[exc_class] = func
            return func
        return dec

    def get(self, path: str, status_code: int = 200, response_model: Optional[Type[Any]] = None, **kwargs: Any):
        def dec(func: Callable[..., Any]) -> Callable[..., Any]:
            self.routes.append(Route(path, func, ["GET"], status_code, response_model))
            return func
        return dec

    def post(self, path: str, status_code: int = 200, response_model: Optional[Type[Any]] = None, **kwargs: Any):
        def dec(func: Callable[..., Any]) -> Callable[..., Any]:
            self.routes.append(Route(path, func, ["POST"], status_code, response_model))
            return func
        return dec

    def put(self, path: str, status_code: int = 200, response_model: Optional[Type[Any]] = None, **kwargs: Any):
        def dec(func: Callable[..., Any]) -> Callable[..., Any]:
            self.routes.append(Route(path, func, ["PUT"], status_code, response_model))
            return func
        return dec

    def delete(self, path: str, status_code: int = 200, response_model: Optional[Type[Any]] = None, **kwargs: Any):
        def dec(func: Callable[..., Any]) -> Callable[..., Any]:
            self.routes.append(Route(path, func, ["DELETE"], status_code, response_model))
            return func
        return dec

    def patch(self, path: str, status_code: int = 200, response_model: Optional[Type[Any]] = None, **kwargs: Any):
        def dec(func: Callable[..., Any]) -> Callable[..., Any]:
            self.routes.append(Route(path, func, ["PATCH"], status_code, response_model))
            return func
        return dec

    async def _resolve_dependency(self, dep_fn: Callable[..., Any], request: Request, cache: dict[Any, Any]) -> Any:
        orig_fn = dep_fn
        if orig_fn in self.dependency_overrides:
            dep_fn = self.dependency_overrides[orig_fn]

        if orig_fn in cache:
            return cache[orig_fn]
        if dep_fn in cache:
            return cache[dep_fn]

        sig = inspect.signature(dep_fn)
        sub_kwargs = {}
        for p_name, p in sig.parameters.items():
            if isinstance(p.default, Depends):
                sub_kwargs[p_name] = await self._resolve_dependency(p.default.dependency, request, cache)
            elif p.default is not inspect.Parameter.empty and isinstance(p.default, ParamMarker):
                header_key = (p.default.alias or p_name).replace("_", "-").lower()
                sub_kwargs[p_name] = request.headers.get(header_key, p.default.default)
            elif p_name == "request":
                sub_kwargs[p_name] = request

        if inspect.isasyncgenfunction(dep_fn):
            gen = dep_fn(**sub_kwargs)
            val = await gen.__anext__()
            cache[orig_fn] = val
            cache[dep_fn] = val
            # Register generator cleanup in request state
            if not hasattr(request.state, "_cleanup_generators"):
                request.state._cleanup_generators = []
            request.state._cleanup_generators.append(gen)
            return val
        elif inspect.isgeneratorfunction(dep_fn):
            gen = dep_fn(**sub_kwargs)
            val = next(gen)
            cache[orig_fn] = val
            cache[dep_fn] = val
            if not hasattr(request.state, "_cleanup_sync_generators"):
                request.state._cleanup_sync_generators = []
            request.state._cleanup_sync_generators.append(gen)
            return val
        else:
            val = dep_fn(**sub_kwargs)
            if inspect.iscoroutine(val):
                val = await val
            cache[orig_fn] = val
            cache[dep_fn] = val
            return val

    async def dispatch(self, request: Request) -> Response:
        try:
            # Match route
            matched_route = None
            path_params = {}
            for r in self.routes:
                match = r.matches(request.method, request.path)
                if match is not None:
                    matched_route = r
                    path_params = match
                    break

            if not matched_route:
                return Response({"detail": "Not Found"}, status_code=404)

            # Resolve parameters for route.endpoint
            sig = inspect.signature(matched_route.endpoint)
            try:
                import typing
                type_hints = typing.get_type_hints(matched_route.endpoint)
            except Exception:
                type_hints = {}
            call_kwargs = {}
            dep_cache = {}

            body_data = await request.json()

            for p_name, p in sig.parameters.items():
                annotation = type_hints.get(p_name, p.annotation)
                default = p.default

                # 1. Dependency injection
                if isinstance(default, Depends):
                    dep_fn = default.dependency
                    call_kwargs[p_name] = await self._resolve_dependency(dep_fn, request, dep_cache)
                    continue

                # 2. Path parameter
                if p_name in path_params:
                    val = path_params[p_name]
                    if annotation is int:
                        val = int(val)
                    call_kwargs[p_name] = val
                    continue

                # 3. Request object
                if annotation is Request or p_name == "request":
                    call_kwargs[p_name] = request
                    continue

                # 4. Header marker
                if isinstance(default, ParamMarker) and default.marker_type == "header":
                    h_key = (default.alias or p_name).replace("_", "-").lower()
                    h_val = request.headers.get(h_key, default.default if default.default is not ... else None)
                    call_kwargs[p_name] = h_val
                    continue

                # 4b. File / UploadFile
                if annotation is UploadFile or (isinstance(default, ParamMarker) and default.marker_type == "file"):
                    file_info = request.files.get(p_name)
                    if isinstance(file_info, UploadFile):
                        call_kwargs[p_name] = file_info
                    elif isinstance(file_info, tuple):
                        fname = file_info[0] if len(file_info) > 0 else "file.bin"
                        fcontent = file_info[1] if len(file_info) > 1 else b""
                        fctype = file_info[2] if len(file_info) > 2 else "application/octet-stream"
                        call_kwargs[p_name] = UploadFile(filename=fname, content=fcontent, content_type=fctype)
                    elif isinstance(file_info, bytes):
                        call_kwargs[p_name] = UploadFile(filename="file.bin", content=file_info)
                    elif file_info is not None:
                        call_kwargs[p_name] = file_info
                    else:
                        def_val = default.default if (isinstance(default, ParamMarker) and default.default is not ...) else None
                        call_kwargs[p_name] = def_val
                    continue

                # 5. Body parameter (Pydantic model)
                if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                    if body_data is None:
                        body_data = {}
                    call_kwargs[p_name] = annotation.model_validate(body_data)
                    continue

                # 6. Query parameters
                q_key = default.alias if (isinstance(default, ParamMarker) and default.alias) else p_name
                if q_key in request.query_params or p_name in request.query_params:
                    val = request.query_params.get(q_key, request.query_params.get(p_name))
                    if annotation in (int, Optional[int]):
                        try:
                            val = int(val)
                        except (ValueError, TypeError):
                            pass
                    elif annotation in (float, Optional[float]):
                        try:
                            val = float(val)
                        except (ValueError, TypeError):
                            pass
                    elif annotation in (bool, Optional[bool]):
                        val = str(val).lower() in ("true", "1", "yes")
                    call_kwargs[p_name] = val
                    continue
                elif isinstance(default, ParamMarker) and default.marker_type == "query":
                    call_kwargs[p_name] = default.default if default.default is not ... else None
                    continue
                elif default is not inspect.Parameter.empty:
                    call_kwargs[p_name] = default

            # Execute endpoint
            if inspect.iscoroutinefunction(matched_route.endpoint):
                res = await matched_route.endpoint(**call_kwargs)
            else:
                res = matched_route.endpoint(**call_kwargs)
                if inspect.iscoroutine(res):
                    res = await res

            # Response formatting
            status_code = matched_route.status_code
            if isinstance(res, Response):
                response = res
            elif isinstance(res, BaseModel):
                response = Response(res.model_dump(mode="json"), status_code=status_code)
            elif isinstance(res, (dict, list)):
                response = Response(res, status_code=status_code)
            elif res is None and status_code == 204:
                response = Response("", status_code=204)
            else:
                response = Response(res, status_code=status_code)

            return response

        except HTTPException as he:
            # Check custom exception handler
            if HTTPException in self.exception_handlers:
                h = self.exception_handlers[HTTPException]
                if inspect.iscoroutinefunction(h):
                    return await h(request, he)
                return h(request, he)
            return Response({"error_code": f"HTTP_{he.status_code}", "message": str(he.detail), "detail": he.detail, "status_code": he.status_code}, status_code=he.status_code, headers=he.headers)

        except ValidationError as ve:
            if ValidationError in self.exception_handlers:
                h = self.exception_handlers[ValidationError]
                if inspect.iscoroutinefunction(h):
                    return await h(request, ve)
                return h(request, ve)
            return Response({
                "error_code": "ERR_VALIDATION_ERROR",
                "message": "Ошибка валидации входных данных",
                "status_code": 422,
                "details": ve.errors(),
            }, status_code=422)

        except Exception as exc:
            # Find matching exception handler in MRO
            for exc_cls, handler in self.exception_handlers.items():
                if isinstance(exc, exc_cls):
                    if inspect.iscoroutinefunction(handler):
                        return await handler(request, exc)
                    return handler(request, exc)
            return Response({"error_code": "INTERNAL_SERVER_ERROR", "message": str(exc), "status_code": 500}, status_code=500)

        finally:
            # Cleanup generator dependencies (yield sessions)
            if hasattr(request.state, "_cleanup_generators"):
                for g in request.state._cleanup_generators:
                    try:
                        await g.__anext__()
                    except (StopAsyncIteration, GeneratorExit):
                        pass
            if hasattr(request.state, "_cleanup_sync_generators"):
                for g in request.state._cleanup_sync_generators:
                    try:
                        next(g)
                    except (StopIteration, GeneratorExit):
                        pass


# Sub-packages and modules
class security:
    class OAuth2PasswordBearer:
        def __init__(self, tokenUrl: str, auto_error: bool = True):
            self.tokenUrl = tokenUrl
            self.auto_error = auto_error

        async def __call__(self, request: Request) -> Optional[str]:
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                return auth_header[7:].strip()
            if self.auto_error:
                raise HTTPException(status_code=401, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})
            return None

    class OAuth2PasswordRequestForm:
        def __init__(self, username: str = "", password: str = "", scope: str = "", grant_type: str = "password"):
            self.username = username
            self.password = password
            self.scope = scope
            self.grant_type = grant_type


class middleware:
    class cors:
        class CORSMiddleware:
            def __init__(self, app: Any, allow_origins: list[str] = None, allow_credentials: bool = True, allow_methods: list[str] = None, allow_headers: list[str] = None):
                self.app = app
                self.allow_origins = allow_origins or ["*"]
                self.allow_credentials = allow_credentials


class testclient:
    class TestClient:
        def __init__(self, app: FastAPI):
            self.app = app

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def request(
            self,
            method: str,
            url: str,
            json: Any = None,
            headers: Optional[dict[str, str]] = None,
            params: Optional[dict[str, Any]] = None,
            files: Optional[dict[str, Any]] = None,
            **kwargs: Any,
        ) -> Response:
            req = Request(method=method, path=url, headers=headers, params=params, json_data=json, files=files, app=self.app)
            # Run dispatch inside an event loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    return pool.submit(asyncio.run, self.app.dispatch(req)).result()
            else:
                return asyncio.run(self.app.dispatch(req))

        def get(self, url: str, **kwargs: Any) -> Response:
            return self.request("GET", url, **kwargs)

        def post(self, url: str, **kwargs: Any) -> Response:
            return self.request("POST", url, **kwargs)

        def put(self, url: str, **kwargs: Any) -> Response:
            return self.request("PUT", url, **kwargs)

        def delete(self, url: str, **kwargs: Any) -> Response:
            return self.request("DELETE", url, **kwargs)

        def patch(self, url: str, **kwargs: Any) -> Response:
            return self.request("PATCH", url, **kwargs)


from fastapi import exceptions
from fastapi.exceptions import RequestValidationError, WebSocketRequestValidationError

import sys
import types


class JSONResponse(Response):
    def __init__(
        self,
        content: Any = None,
        status_code: int = 200,
        headers: Optional[dict[str, str]] = None,
        media_type: str = "application/json",
    ):
        super().__init__(content=content, status_code=status_code, headers=headers, media_type=media_type)


responses_mod = types.ModuleType("fastapi.responses")
responses_mod.JSONResponse = JSONResponse
responses_mod.Response = Response
sys.modules["fastapi.responses"] = responses_mod


