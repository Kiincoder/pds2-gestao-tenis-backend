from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.controllers.auth import router
from app.core.config import Settings
from app.core.rate_limit import RegistrationRateLimiter
from app.domain.exceptions import DuplicateEmailError


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
        version="0.1.0",
        description="US01 — criação de conta. US02 e US03 serão entregues em sequência.",
        lifespan=lifespan,
    )
    limiter = RegistrationRateLimiter(
        settings.registration_rate_limit, settings.registration_rate_window_seconds
    )

    @application.middleware("http")
    async def limit_registration(request: Request, call_next):
        if request.method == "POST" and request.url.path.rstrip("/") == "/api/v1/auth/register":
            retry_after = limiter.check(request.client.host if request.client else "unknown")
            if retry_after is not None:
                return JSONResponse(
                    status_code=429,
                    content={"message": "Muitas tentativas. Tente novamente em instantes."},
                    headers={"Retry-After": str(retry_after)},
                )
        return await call_next(request)

    @application.exception_handler(DuplicateEmailError)
    async def duplicate_email(request: Request, error: DuplicateEmailError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "message": "Este e-mail já está cadastrado.",
                "errors": {"email": ["Este e-mail já está cadastrado."]},
            },
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
    return application


app = create_app()
