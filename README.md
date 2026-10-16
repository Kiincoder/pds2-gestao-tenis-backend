# Clube de Tênis — API

## Executar com Docker Compose

Requer Docker Desktop/Engine com Compose v2 e acesso à internet para baixar imagens e pacotes. Na raiz do projeto, em PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up --build -d app
```

O Compose inicia o PostgreSQL, executa `alembic upgrade head` no serviço `migrate` e, após a migration terminar, inicia a API.

- API: `http://localhost:8000/api/v1`.
- Swagger UI: `http://localhost:8000/docs`.
- ReDoc: `http://localhost:8000/redoc`.
- Contrato OpenAPI: `http://localhost:8000/openapi.json`.
- Saúde: `http://localhost:8000/up` — verifica se a aplicação responde, sem consultar o banco.

O PostgreSQL fica disponível em `localhost:5432`, com as credenciais do `.env`. Dentro do Docker, a API usa o host `db`. O volume `postgres_data` preserva os dados ao parar os containers. As credenciais de exemplo destinam-se a desenvolvimento local.

```powershell
docker compose logs -f app migrate
docker compose stop
```

O Dockerfile inclui as dependências de desenvolvimento para executar os testes. As versões permitidas estão em `pyproject.toml`; esta entrega ainda não inclui um lock das dependências resolvidas.

## Executar com Python local

Requer Python 3.13+ e PostgreSQL acessível nas credenciais configuradas no `.env`. O Python 3.14 também é aceito, desde que as versões resolvidas das dependências ofereçam suporte.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --no-proxy-headers
```

Para usar somente o PostgreSQL pelo Docker: `docker compose up -d db`. A aplicação monta a URL de conexão a partir das variáveis `DB_*`, incluindo o escape correto de caracteres especiais na senha.

## Organização

```text
app/
  controllers/    Rotas, entrada HTTP e respostas
  schemas/        Validação Pydantic e contratos públicos
  data/           Dados tipados do caso de uso
  handlers/       Caso de uso de cadastro
  repositories/   Contrato de persistência e implementação SQLAlchemy
  domain/         Entidades e exceções sem dependência de framework
  db/             Modelo SQLAlchemy e base declarativa
  core/           Configuração e limite de requisições
  dependencies.py Injeção de sessões, repository e hasher
  main.py         Aplicação, ciclo de vida e tratamento de erros
migrations/       Histórico Alembic
tests/
  unit/           Handler e limite de requisições
  api/            Contrato HTTP e validação, com handler substituído
  integration/    Cadastro e restrições no PostgreSQL real
```

Fluxo: controller → handler → contrato repository → SQLAlchemy → PostgreSQL. O handler recebe o hasher por injeção; o repository recebe apenas o hash da senha. As rotas de cadastro são síncronas e executadas pelo FastAPI no pool de threads, compatível com o driver SQLAlchemy síncrono.

As migrations são explícitas: não há criação automática de tabelas durante a inicialização da API. Para criar uma próxima migration:

```powershell
alembic revision --autogenerate -m "descricao"
alembic upgrade head
```

## Referências

- [FastAPI — dependências](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [SQLAlchemy — PostgreSQL e psycopg](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg)
- [Alembic — migrations](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [pwdlib — hash de senhas](https://frankie567.github.io/pwdlib/)
