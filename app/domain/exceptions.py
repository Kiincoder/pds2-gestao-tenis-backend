class DuplicateEmailError(Exception):
    """O endereço de e-mail já está cadastrado."""


class AuthenticationError(Exception):
    """Credenciais ou sessão inválidas."""


class InvalidCredentialsError(AuthenticationError):
    """Falha de login sem indicar se a conta existe."""
