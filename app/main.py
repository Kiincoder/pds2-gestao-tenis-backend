from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.controllers.auth import router
from app.controllers.members import router as members_router
from app.controllers.sessions import router as sessions_router
from app.core.config import Settings
from app.core.rate_limit import RegistrationRateLimiter
from app.domain.exceptions import (
    AuthenticationError,
    DuplicateEmailError,
    DuplicateMemberEmailError,
    ForbiddenError,
    InvalidCredentialsError,
    MemberNotFoundError,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        application.state.session_factory = sessionmaker(engine, expire_on_commit=False)
        try:
            yield
        finally:
            engine.dispose()

    application = FastAPI(
        title="Clube de Tênis API",
        version="0.3.0",
        description="US01 — cadastro. US02 — login/logout. US03 — membros gerenciados por admin.",
        lifespan=lifespan,
    )
    application.state.settings = settings
    limiter = RegistrationRateLimiter(
        settings.registration_rate_limit, settings.registration_rate_window_seconds
    )
    login_limiter = RegistrationRateLimiter(
        settings.login_rate_limit, settings.login_rate_window_seconds
    )

    @application.middleware("http")
    async def limit_authentication(request: Request, call_next):
        path = request.url.path.rstrip("/")
        selected_limiter = {
            "/api/v1/auth/register": limiter,
            "/api/v1/auth/login": login_limiter,
        }.get(path)
        response = None
        if request.method == "POST" and selected_limiter is not None:
            client_ip = request.client.host if request.client else "unknown"
            retry_after = selected_limiter.check(client_ip)
            if retry_after is not None:
                response = JSONResponse(
                    status_code=429,
                    content={"message": "Muitas tentativas. Tente novamente em instantes."},
                    headers={"Retry-After": str(retry_after)},
                )
        if response is None:
            response = await call_next(request)
        if path in {"/api/v1/auth/login", "/api/v1/auth/logout", "/api/v1/auth/me"} or (
            path == "/api/v1/members" or path.startswith("/api/v1/members/")
        ):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
        return response

    @application.exception_handler(AuthenticationError)
    async def unauthorized(request: Request, error: AuthenticationError) -> JSONResponse:
        message = (
            "E-mail ou senha inválidos."
            if isinstance(error, InvalidCredentialsError)
            else "Autenticação necessária ou sessão inválida."
        )
        return JSONResponse(
            status_code=401,
            content={"message": message},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @application.exception_handler(DuplicateEmailError)
    async def duplicate_email(request: Request, error: DuplicateEmailError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "message": "Este e-mail já está cadastrado.",
                "errors": {"email": ["Este e-mail já está cadastrado."]},
            },
        )

    @application.exception_handler(ForbiddenError)
    async def forbidden(request: Request, error: ForbiddenError) -> JSONResponse:
        return JSONResponse(
            status_code=403, content={"message": "Acesso restrito a administradores."}
        )

    @application.exception_handler(MemberNotFoundError)
    async def member_not_found(request: Request, error: MemberNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"message": "Membro não encontrado."})

    @application.exception_handler(DuplicateMemberEmailError)
    async def duplicate_member(request: Request, error: DuplicateMemberEmailError) -> JSONResponse:
        message = "Este e-mail já está cadastrado para outro membro."
        return JSONResponse(
            status_code=409, content={"message": message, "errors": {"email": [message]}}
        )

    @application.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: RequestValidationError) -> JSONResponse:
        errors: dict[str, list[str]] = {}
        for item in error.errors():
            field = ".".join(str(part) for part in item["loc"] if part != "body") or "body"
            message = item["msg"]
            if item["type"] == "missing":
                message = "Campo obrigatório."
            elif item["type"] == "extra_forbidden":
                message = "Este campo não pode ser informado."
            elif item["type"] == "value_error" and isinstance(
                item.get("ctx", {}).get("error"), ValueError
            ):
                message = str(item["ctx"]["error"])
            errors.setdefault(field, []).append(message)
        return JSONResponse(
            status_code=422,
            content={"message": "Os dados informados são inválidos.", "errors": errors},
        )

    @application.get("/", include_in_schema=False)
    def index() -> RedirectResponse:
        return RedirectResponse("/docs")

    @application.get("/up", tags=["Saúde"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    application.include_router(router)
    application.include_router(sessions_router)
    application.include_router(members_router)
    return application


app = create_app()
