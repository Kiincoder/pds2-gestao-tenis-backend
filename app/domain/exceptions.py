class DuplicateEmailError(Exception):
    """O endereço de e-mail já está cadastrado."""


class AuthenticationError(Exception):
    """Credenciais ou sessão inválidas."""


class InvalidCredentialsError(AuthenticationError):
    """Falha de login sem indicar se a conta existe."""


class ForbiddenError(Exception):
    """A conta autenticada não tem permissão para a operação."""


class MemberNotFoundError(Exception):
    """O membro solicitado não existe."""


class DuplicateMemberEmailError(Exception):
    """O e-mail já pertence a outro membro."""


class UserNotFoundError(Exception):
    """A conta de acesso solicitada não existe."""
