from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class LoginUserData:
    email: str
    password: str = field(repr=False)
