# Sistema de Autenticação - Conversa Estágios

## Visão Geral

O sistema de autenticação implementado usa **Magic Links** com **JWT Bearer Tokens** para usuários com email `@usp.br`.

## Fluxo de Autenticação

### 1. Solicitar Magic Link

**Endpoint:** `POST /api/v1/auth/request-magic-link`

```json
{
  "email": "joao.silva@usp.br"
}
```

**Resposta:**
```json
{
  "message": "Magic link enviado para seu email",
  "email": "joao.silva@usp.br",
  "expires_in_minutes": 15
}
```

### 2. Verificar Token Magic

**Endpoint:** `POST /api/v1/auth/verify-token`

```json
{
  "token": "abc123def456ghi789"
}
```

**Resposta:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 86400,
  "user": {
    "id": 1,
    "email": "joao.silva@usp.br",
    "full_name": "João Silva",
    "is_active": true,
    "created_at": "2025-01-01T00:00:00Z"
  }
}
```

### 3. Usar JWT Token

Para acessar rotas protegidas, inclua o token no header:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 4. Obter Informações do Usuário

**Endpoint:** `GET /api/v1/auth/me`

**Headers:** `Authorization: Bearer <token>`

**Resposta:**
```json
{
  "id": 1,
  "email": "joao.silva@usp.br",
  "full_name": "João Silva",
  "is_active": true,
  "created_at": "2025-01-01T00:00:00Z",
  "last_login": "2025-01-01T12:00:00Z"
}
```

### 5. Renovar Token

**Endpoint:** `POST /api/v1/auth/refresh`

**Headers:** `Authorization: Bearer <token>`

## Configuração de Email

Para o envio de magic links, configure as seguintes variáveis de ambiente:

```env
# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
FROM_EMAIL=noreply@example.com
FROM_NAME=Conversa Estágios

# Frontend URL (para os links mágicos)
FRONTEND_URL=http://localhost:5173
```

## Segurança

### Restrições
- Apenas emails `@usp.br` são aceitos
- Magic tokens expiram em 15 minutos
- Magic tokens são de uso único
- JWT tokens expiram em 24 horas (configurável)

### Validações
- Constraint no banco: email deve terminar com `@usp.br`
- Magic tokens são hasheados antes do armazenamento
- JWT tokens assinados com chave secreta
- Tokens expirados são automaticamente rejeitados

## Rotas de Chat

### Chat Sem Autenticação
```bash
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "Quais são as linguagens mais usadas?"}'
```

### Chat Com Autenticação
```bash
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <seu-jwt-token>" \
  -d '{"message": "Quais são as linguagens mais usadas?"}'
```

## Banco de Dados

### Tabelas Criadas

**`users`**
- `id` (Primary Key)
- `email` (Unique, must end with @usp.br)
- `full_name` 
- `is_active`
- `created_at`, `updated_at`, `last_login`

**`magic_tokens`**
- `id` (Primary Key)
- `user_id` (Foreign Key → users.id)
- `token` (Hashed, Unique)
- `expires_at`
- `used_at`
- `created_at`
- `ip_address`, `user_agent`

### Migração

Para criar as tabelas, execute:
```bash
python backend/add_auth_tables.py
```

## Testando o Sistema

### Script de Teste
```bash
python backend/test_auth_setup.py    # Testa imports e configuração
python backend/test_auth_flow.py     # Testa fluxo completo
```

### Servidor de Desenvolvimento
```bash
cd /Users/m/dev/conversa-v2
source env/bin/activate
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Documentação Interativa
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Próximos Passos

Para integração com o frontend:

1. **Frontend fará requests para:**
   - `POST /api/v1/auth/request-magic-link` - Solicitar magic link
   - `POST /api/v1/auth/verify-token` - Verificar token do email
   - `GET /api/v1/auth/me` - Obter dados do usuário
   - `POST /api/v1/chat/` - Chat (com/sem auth)

2. **Frontend precisará implementar:**
   - Formulário de login (email)
   - Página de verificação de token (do magic link)
   - Armazenamento seguro do JWT (localStorage/sessionStorage)
   - Interceptor para adicionar Authorization header
   - Renovação automática de tokens

3. **URL do Magic Link:**
   - `{FRONTEND_URL}/auth/verify?token={magic_token}`
   - Ex: `http://localhost:5173/auth/verify?token=abc123...`