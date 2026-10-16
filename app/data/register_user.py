from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RegisterUserData:
    name: str
    email: str
    password: str = field(repr=False)
