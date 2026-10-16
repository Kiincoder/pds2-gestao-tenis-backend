from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status

from app.data.members import CreateMemberData, UpdateMemberData
from app.dependencies import (
    get_create_member_handler,
    get_delete_member_handler,
    get_list_members_handler,
    get_member_handler,
    get_update_member_handler,
    require_administrator,
)
from app.domain.entities import MemberStatus
from app.handlers.members import (
    CreateMemberHandler,
    DeleteMemberHandler,
    GetMemberHandler,
    ListMembersHandler,
    UpdateMemberHandler,
)
from app.schemas.auth import AuthenticationErrorResponse, ValidationErrorResponse
from app.schemas.members import (
    CreateMemberRequest,
    MemberEnvelope,
    MemberErrorResponse,
    MemberListResponse,
    MemberResponse,
    PaginationMeta,
    UpdateMemberRequest,
)

router = APIRouter(
    prefix="/api/v1/members",
    tags=["US03 — Membros"],
    dependencies=[Depends(require_administrator)],
    responses={
        401: {
            "model": AuthenticationErrorResponse,
            "description": "Sessão ausente, inválida, expirada ou revogada",
            "headers": {"WWW-Authenticate": {"schema": {"type": "string"}, "example": "Bearer"}},
        },
        403: {"model": MemberErrorResponse, "description": "Conta sem permissão de administrador"},
        422: {"model": ValidationErrorResponse, "description": "Dados inválidos"},
    },
)
not_found = {"model": MemberErrorResponse, "description": "Membro não encontrado"}
conflict = {
    "model": ValidationErrorResponse,
    "description": "E-mail já cadastrado para outro membro",
}
MemberId = Annotated[int, Path(ge=1, le=9223372036854775807)]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=MemberEnvelope,
    summary="Cadastrar membro",
    description="Cria o cadastro do clube. Não cria conta de acesso nem altera permissões.",
    responses={409: conflict},
)
def create_member(
    payload: CreateMemberRequest,
    handler: Annotated[CreateMemberHandler, Depends(get_create_member_handler)],
) -> MemberEnvelope:
    member = handler.handle(
        CreateMemberData(payload.name, str(payload.email), payload.phone, payload.status)
    )
    return MemberEnvelope(data=MemberResponse.model_validate(member))


@router.get("", response_model=MemberListResponse, summary="Listar membros com paginação e filtros")
def list_members(
    handler: Annotated[ListMembersHandler, Depends(get_list_members_handler)],
    page: Annotated[int, Query(ge=1, le=2147483647)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[MemberStatus | None, Query(alias="status")] = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
) -> MemberListResponse:
    result = handler.handle(
        page=page, page_size=page_size, status=status_filter, search=q.strip() if q else None
    )
    return MemberListResponse(
        data=[MemberResponse.model_validate(member) for member in result.items],
        meta=PaginationMeta(
            page=result.page,
            page_size=result.page_size,
            total=result.total,
            total_pages=(result.total + result.page_size - 1) // result.page_size,
        ),
    )


@router.get(
    "/{member_id}",
    response_model=MemberEnvelope,
    summary="Consultar membro",
    responses={404: not_found},
)
def get_member(
    member_id: MemberId,
    handler: Annotated[GetMemberHandler, Depends(get_member_handler)],
) -> MemberEnvelope:
    return MemberEnvelope(data=MemberResponse.model_validate(handler.handle(member_id)))


@router.patch(
    "/{member_id}",
    response_model=MemberEnvelope,
    summary="Editar dados ou ativar/inativar membro",
    description="Atualiza somente os campos informados. Envie phone: null para remover o telefone.",
    responses={404: not_found, 409: conflict},
)
def update_member(
    member_id: MemberId,
    payload: UpdateMemberRequest,
    handler: Annotated[UpdateMemberHandler, Depends(get_update_member_handler)],
) -> MemberEnvelope:
    member = handler.handle(
        member_id,
        UpdateMemberData(
            name=payload.name,
            email=str(payload.email) if payload.email is not None else None,
            phone=payload.phone,
            update_phone="phone" in payload.model_fields_set,
            status=payload.status,
        ),
    )
    return MemberEnvelope(data=MemberResponse.model_validate(member))


@router.delete(
    "/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Excluir membro",
    description="Exclui definitivamente o cadastro do membro. Não exclui contas de acesso.",
    responses={404: not_found},
)
def delete_member(
    member_id: MemberId,
    handler: Annotated[DeleteMemberHandler, Depends(get_delete_member_handler)],
) -> Response:
    handler.handle(member_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
