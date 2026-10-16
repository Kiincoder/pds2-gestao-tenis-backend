import argparse

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.exceptions import UserNotFoundError
from app.handlers.administrator import PromoteAdministratorHandler
from app.repositories.sqlalchemy_users import SqlAlchemyUserRepository


def main() -> int:
    parser = argparse.ArgumentParser(description="Comandos administrativos do clube de tênis.")
    commands = parser.add_subparsers(dest="command", required=True)
    promote = commands.add_parser(
        "promote-admin", help="Promover uma conta existente a administrador"
    )
    promote.add_argument("email")
    args = parser.parse_args()

    engine = create_engine(Settings().database_url)
    try:
        with Session(engine, expire_on_commit=False) as session:
            handler = PromoteAdministratorHandler(SqlAlchemyUserRepository(session))
            try:
                user = handler.handle(args.email)
            except UserNotFoundError:
                parser.exit(
                    1, "Conta não encontrada. Crie a conta pela US01 antes de promovê-la.\n"
                )
            print(f"Conta promovida a administrador: {user.email}")
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
