# Clube de Tênis — Backend

API em PHP 8.3+ / Laravel 13 e PostgreSQL 17. O ambiente Docker usa PHP 8.4.

## Entregas e commits

As histórias estão na imagem `image.png`. Para permitir um commit independente por história, esta primeira entrega contém **somente a US01**, junto com a infraestrutura necessária:

| História | Requisito | Situação |
| --- | --- | --- |
| US01 | Criar conta para acessar o sistema do clube | Implementada; execução dos testes pendente no ambiente local |
| US02 | Login e logout com segurança | Próxima entrega, após o commit da US01 |
| US03 | Administrador cadastra e gerencia membros | Após o commit da US02 |

A imagem não especifica campos nem critérios detalhados. Para a US01, foram adotados nome, e-mail, senha e confirmação. A criação de conta não faz login automático. Campos de membros e permissões administrativas ficam para a US03.

## Executar com Docker Compose

Requer Docker Engine/Desktop com Compose v2 e acesso à internet para baixar imagens e dependências. Os comandos abaixo funcionam em PowerShell, na raiz do projeto:

```powershell
Copy-Item .env.example .env
docker compose build app
docker compose run --rm app composer install
docker compose run --rm app php artisan key:generate
docker compose run --rm app php artisan migrate
docker compose up -d app
```

API: `http://localhost:8000/api/v1`. Swagger: `http://localhost:8000/docs`. OpenAPI: `http://localhost:8000/openapi.json`. Saúde da aplicação: `http://localhost:8000/up` (não verifica conectividade com o banco).

`composer install` gera o `composer.lock` no primeiro uso. Inclua esse arquivo no commit para fixar as versões. Ele ainda não foi gerado neste ambiente, que não dispõe de PHP/Composer/Docker e bloqueia downloads por shell.

O serviço `app` sobrescreve apenas o endereço de conexão para usar o host `db` dentro do Docker. O PostgreSQL fica acessível no host em `localhost:5432`; banco, usuário e senha vêm do `.env`. Os valores de exemplo são para desenvolvimento local. O volume `postgres_data` preserva os dados ao parar os containers.

```powershell
docker compose logs -f app
docker compose stop
```

O servidor Artisan e o Dockerfile fornecidos destinam-se a desenvolvimento. Para produção, use servidor apropriado, `APP_DEBUG=false`, credenciais próprias e HTTPS.

## Executar com PHP e Composer locais

Requer PHP 8.3+, Composer 2, PostgreSQL e as extensões exigidas pelo Laravel e PHPUnit, incluindo `pdo_pgsql`, `mbstring`, DOM e XML. O ambiente Docker padroniza a execução em PHP 8.4. Configure o banco e as credenciais no `.env`:

```powershell
Copy-Item .env.example .env
composer install
php artisan key:generate
php artisan migrate
php artisan serve
```

## US01 — Criar conta

`POST /api/v1/auth/register` — público; envie `Content-Type: application/json`.

```json
{
  "name": "Maria Silva",
  "email": "maria@example.com",
  "password": "SenhaSegura123",
  "password_confirmation": "SenhaSegura123"
}
```

Resposta `201`:

```json
{
  "data": {
    "id": 1,
    "name": "Maria Silva",
    "email": "maria@example.com",
    "created_at": "2026-10-15T21:00:00.000000Z"
  }
}
```

- Nome obrigatório, com até 120 caracteres.
- E-mail válido, com até 254 caracteres, convertido para minúsculas e sem espaços nas extremidades.
- Senha com pelo menos 12 caracteres, letras maiúsculas/minúsculas e número; até 72 bytes em UTF-8, limite do bcrypt. A senha e sua confirmação não são aparadas.
- E-mail duplicado, dados inválidos e tentativa de enviar `role`/`is_admin`: `422` com `message` e `errors`.
- Máximo de 5 tentativas/minuto por IP, incluindo cadastros inválidos: `429` com `Retry-After`.
- Senha persistida somente como hash; senha e token de lembrança nunca aparecem na resposta.
- PostgreSQL impõe unicidade e normalização do e-mail. A violação de unicidade por cadastros simultâneos é convertida em erro de validação.

As regras de validação exibem mensagens em português. A API responde erros em JSON mesmo sem o cabeçalho `Accept`.

## Organização

```text
app/
  Data/                    Dados tipados que entram no caso de uso
  Handlers/Auth/           Caso de uso de cadastro
  Http/Controllers/Auth/   Entrada HTTP e resposta
  Http/Requests/Auth/      Autorização e validação da entrada
  Http/Resources/          Campos públicos da resposta
  Models/                 Modelos Eloquent e casts
  Repositories/Contracts/ Contratos de persistência
  Repositories/Eloquent/  Implementações de persistência
  Providers/              Injeção de dependências e limites de requisição
```

Fluxo: Request → Controller → Handler → contrato Repository → Eloquent → PostgreSQL. Os repositories são específicos ao domínio; não há um repository genérico que apenas replique todas as operações do Eloquent. As regras simples de unicidade na validação usam a regra nativa do Laravel, e o banco assegura a integridade final.

## Testes e estilo

Os testes de integração usam **PostgreSQL real**, em um serviço separado do banco de desenvolvimento. O banco de testes não publica porta nem compartilha o volume de desenvolvimento.

```powershell
docker compose --profile test run --rm test
docker compose run --rm app composer lint
```

Para formatar: `docker compose run --rm app vendor/bin/pint`.

A suíte cobre cadastro, hash e ocultação da senha, normalização e duplicação do e-mail, entradas inválidas, tentativa de privilégios administrativos, limite de requisições, erros JSON e disponibilidade do Swagger. Um teste do handler simula a violação de unicidade na disputa entre requisições; ele não reproduz concorrência real.

Para testes fora do Docker, crie um banco **separado** chamado `clube_tenis_test`, configure `.env.testing` com credenciais próprias e rode `composer test`. O `phpunit.xml` força o nome do banco de testes para evitar utilizar o banco de desenvolvimento. Evite executar a suíte com configuração previamente cacheada (`php artisan config:clear`).

## Documentação Swagger

O contrato OpenAPI 3.0 está versionado em `public/openapi.json`. O Swagger UI em `/docs` permite testar o cadastro no mesmo servidor. Os arquivos visuais são carregados do CDN com versão fixa; essa interface precisa de internet. O contrato JSON fica disponível localmente e pode ser importado no Postman/Insomnia.

## Registrar a US01 no Git

Esta pasta não continha repositório Git, e nenhum commit foi criado automaticamente. Se ainda não houver repositório, inicialize-o:

```powershell
git init
```

Após instalar as dependências e validar a entrega:

```powershell
git add .
git commit -m "feat(US01): criar contas com Laravel e PostgreSQL"
```

Não avance para a US02 antes desse commit se desejar preservar uma história por commit.

## Referências

- [Estrutura oficial do Laravel 13](https://github.com/laravel/laravel/tree/13.x)
- [Validação de requisições](https://laravel.com/docs/13.x/validation)
- [Tratamento de erros JSON](https://laravel.com/docs/13.x/errors)
