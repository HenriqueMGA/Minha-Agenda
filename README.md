# API MinhaAgenda

API em FastAPI para agendamento de consultas: usuários do sistema, pacientes, médicos e agendamentos, com confirmação de presença por WhatsApp ou email.

- **Produção (Vercel):** <https://minha-agenda-flax-tau.vercel.app>
- **Front em produção:** <https://minha-agenda-frontend-eight.vercel.app>
- **Local:** <http://localhost:8000>
- **Documentação interativa (Swagger):** `/docs` — dá para testar todas as rotas pelo navegador.

## Sumário

- [Como rodar](#como-rodar)
- [Autenticação](#autenticação)
- [Erros](#erros)
- [Auth — `/auth`](#auth--auth)
- [Usuários — `/users`](#usuários--users)
- [Pacientes — `/patients`](#pacientes--patients)
- [Médicos — `/doctors`](#médicos--doctors)
- [Agendamentos — `/appointments`](#agendamentos--appointments)
- [Fluxo de confirmação de consulta](#fluxo-de-confirmação-de-consulta)

---

## Como rodar

```bash
poetry install
poetry run poe run      # sobe em http://localhost:8000
poetry run pytest       # roda os testes
```

Variáveis de ambiente (arquivo `.env` na raiz):

| Variável | Para que serve |
|---|---|
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Conexão com o PostgreSQL |
| `SECRET_KEY` | Chave usada para assinar os tokens JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Validade do token de login (padrão: `60`) |
| `APP_BASE_URL` | Endereço público da API, usado para montar o link de confirmação enviado ao paciente. Em produção: `https://minha-agenda-flax-tau.vercel.app` (sem `/` no final) |
| `PORT` | Porta do servidor quando roda com `poe run` (padrão: `8000`) |

Na Vercel, o `.env` não é enviado: cadastre essas variáveis em **Settings → Environment Variables** do projeto da API e faça um **Redeploy**. Se o `APP_BASE_URL` estiver faltando ou apontando para outro endereço, o link de confirmação que vai para o paciente sai errado.

As tabelas são criadas automaticamente quando a API sobe, e as colunas novas são adicionadas às tabelas que já existiam, sem apagar dados.

**CORS:** a API aceita o front em produção, `localhost`/`127.0.0.1` em qualquer porta (Vite, Live Server etc.) e páginas abertas direto do arquivo (`file://`). Outro domínio precisa ser adicionado em `allow_origins` no `src/app.py`.

---

## Autenticação

Quase todas as rotas exigem login. O fluxo é:

1. Faça login em `POST /auth/token` e pegue o `access_token`.
2. Envie o token no cabeçalho de todas as outras requisições:

```text
Authorization: Bearer <access_token>
```

Algumas rotas exigem também um **tipo de usuário** específico (`admin` ou `dev`). Usuários comuns são do tipo `user`.

Na tabela de cada rota, a coluna **Acesso** indica:

| Valor | Significado |
|---|---|
| 🌐 Público | Não precisa de login |
| 🔒 Logado | Qualquer usuário logado |
| 🔑 admin/dev | Só usuários do tipo `admin` ou `dev` |
| 👤 Próprio ou admin/dev | O próprio usuário (mesmo email) ou um `admin`/`dev` |

---

## Erros

Todos os erros voltam no formato:

```json
{ "detail": "Mensagem explicando o erro" }
```

| Código | Quando acontece |
|---|---|
| `400` | Atualização enviada sem nenhum campo |
| `401` | Sem token, token inválido/expirado, ou email/senha errados no login |
| `403` | Logado, mas sem permissão para a rota |
| `404` | Registro não encontrado |
| `409` | Conflito: email/CPF já cadastrado, ou médico já tem consulta nesse dia e horário |
| `422` | Dados inválidos: CPF inválido, data em formato errado, id que não é número, campo obrigatório faltando |

**CPF:** sempre 11 dígitos, só números, sem pontos ou traço (ex.: `12345678909`). O dígito verificador é validado.

**Datas e horários:** data no formato `AAAA-MM-DD` (ex.: `2026-11-10`) e horário `HH:MM:SS` (ex.: `14:00:00`).

---

## Auth — `/auth`

### `POST /auth/token` — Login

| | |
|---|---|
| **URL** | `/auth/token` |
| **Acesso** | 🌐 Público |
| **Formato do corpo** | `application/x-www-form-urlencoded` (formulário, **não** JSON) |

**Entrada (formulário):**

| Campo | Tipo | Descrição |
|---|---|---|
| `username` | texto | **O email** do usuário (o nome do campo é `username` por padrão do OAuth2) |
| `password` | texto | Senha |

**Saída `200`:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Erros:** `401` email ou senha incorretos.

Exemplo em JavaScript:

```js
const r = await fetch(`${API}/auth/token`, {
  method: "POST",
  headers: { "Content-Type": "application/x-www-form-urlencoded" },
  body: new URLSearchParams({ username: email, password: senha }),
});
const { access_token } = await r.json();
```

---

## Usuários — `/users`

Usuários são as pessoas que usam o sistema (recepcionistas, administradores).

### `GET /users/list` — Listar usuários

| | |
|---|---|
| **URL** | `/users/list` |
| **Acesso** | 🔒 Logado |
| **Entrada** | — |

**Saída `200`:**

```json
[
  { "email": "recepcao@clinica.com", "username": "recepcao" }
]
```

### `GET /users/search` — Buscar usuários

| | |
|---|---|
| **URL** | `/users/search?email=recepcao@clinica.com` |
| **Acesso** | 🔒 Logado |

**Entrada (query string, todos opcionais — combinados com "E"):**

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `name` | texto | Nome completo (busca exata) |
| `email` | texto | Email (busca exata) |
| `username` | texto | Nome de usuário (busca exata) |
| `type` | texto | Tipo: `user`, `admin` ou `dev` |

**Saída `200`:** lista no mesmo formato de `/users/list` (vazia se nada for encontrado).

### `POST /users/create` — Criar usuário

| | |
|---|---|
| **URL** | `/users/create` |
| **Acesso** | 🔑 admin/dev |

**Entrada (JSON):**

```json
{
  "name": "Ana Souza",
  "username": "ana",
  "password": "senha123",
  "email": "ana@clinica.com",
  "type": "user"
}
```

Todos os campos são obrigatórios. `type` pode ser `user`, `admin` ou `dev`.

**Saída `200`:**

```json
{ "email": "ana@clinica.com" }
```

**Erros:** `403` sem permissão · `409` email já está em uso.

### `PUT /users/update` — Atualizar usuário

| | |
|---|---|
| **URL** | `/users/update?email=ana@clinica.com` |
| **Acesso** | 👤 Próprio ou admin/dev |

**Entrada:**

- Query string: `email` — email do usuário a ser alterado.
- Corpo (JSON), envie só os campos que quer mudar:

```json
{
  "name": "Ana Souza Lima",
  "username": "analima",
  "password": "novaSenha",
  "email": "ana.lima@clinica.com",
  "type": "admin"
}
```

Um usuário comum **não pode** alterar o próprio `type`.

**Saída `200`:**

```json
{ "email": "ana.lima@clinica.com" }
```

**Erros:** `400` nenhum campo enviado · `403` tentando alterar outro usuário ou o próprio tipo · `404` usuário não encontrado · `409` novo email já está em uso.

### `DELETE /users/delete` — Excluir usuário

| | |
|---|---|
| **URL** | `/users/delete?email=ana@clinica.com` |
| **Acesso** | 👤 Próprio ou admin/dev |

**Entrada (query string):** `email` — email do usuário a excluir.

**Saída `200`:**

```json
{ "email": "ana@clinica.com" }
```

**Erros:** `403` tentando excluir outro usuário · `404` usuário não encontrado.

---

## Pacientes — `/patients`

O telefone e o email cadastrados aqui são usados para montar as mensagens de confirmação de consulta.

### `GET /patients/list` — Listar pacientes

| | |
|---|---|
| **URL** | `/patients/list` |
| **Acesso** | 🔒 Logado |
| **Entrada** | — |

**Saída `200`:**

```json
[
  {
    "id": "00001",
    "cpf": "12345678909",
    "name": "Maria Silva",
    "email": "maria@example.com",
    "tel": "(11) 98888-7777",
    "dt_nasc": "1990-01-01"
  }
]
```

`id` é gerado pela API, sempre com pelo menos 5 dígitos. As rotas de atualizar e excluir continuam usando o `cpf`.

### `GET /patients/search` — Buscar pacientes

| | |
|---|---|
| **URL** | `/patients/search?cpf=12345678909` |
| **Acesso** | 🔒 Logado |

**Entrada (query string, todos opcionais — combinados com "E"):**

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `name` | texto | Nome (busca exata) |
| `email` | texto | Email (busca exata) |
| `cpf` | texto | CPF |

**Saída `200`:** lista no mesmo formato de `/patients/list`.

### `POST /patients/create` — Cadastrar paciente

| | |
|---|---|
| **URL** | `/patients/create` |
| **Acesso** | 🔒 Logado |

**Entrada (JSON), todos obrigatórios:**

```json
{
  "name": "Maria Silva",
  "cpf": "12345678909",
  "email": "maria@example.com",
  "tel": "(11) 98888-7777",
  "dt_nasc": "1990-01-01"
}
```

`tel` pode ter espaços, parênteses e traço; para o WhatsApp só os dígitos são usados (DDD + número, o `+55` é acrescentado automaticamente).

**Saída `200`:**

```json
{ "cpf": "12345678909" }
```

**Erros:** `409` CPF já está em uso · `422` CPF inválido.

### `PUT /patients/update` — Atualizar paciente

| | |
|---|---|
| **URL** | `/patients/update?cpf=12345678909` |
| **Acesso** | 🔒 Logado |

**Entrada:**

- Query string: `cpf` — CPF atual do paciente.
- Corpo (JSON), só os campos que mudam: `name`, `email`, `tel`, `dt_nasc`, `cpf`.

```json
{ "tel": "(11) 97777-6666" }
```

**Saída `200`:**

```json
{ "cpf": "12345678909" }
```

**Erros:** `400` nenhum campo enviado · `404` paciente não encontrado · `409` novo CPF já está em uso · `422` CPF inválido.

### `DELETE /patients/delete` — Excluir paciente

| | |
|---|---|
| **URL** | `/patients/delete?cpf=12345678909` |
| **Acesso** | 🔒 Logado |

**Entrada (query string):** `cpf`.

**Saída `200`:**

```json
{ "cpf": "12345678909" }
```

**Erros:** `404` paciente não encontrado.

---

## Médicos — `/doctors`

### `GET /doctors/list` — Listar médicos

| | |
|---|---|
| **URL** | `/doctors/list` |
| **Acesso** | 🔒 Logado |
| **Entrada** | — |

**Saída `200`:**

```json
[
  {
    "id": "00001",
    "cpf": "98765432100",
    "name": "Dr. João Souza",
    "email": "joao@clinica.com",
    "tel": "(11) 3333-4444",
    "doctor_specialty": "Cardiologia",
    "registration": "CRM-SP 123456",
    "status": "ativo"
  }
]
```

| Campo | Descrição |
|---|---|
| `id` | Gerado pela API, sempre com pelo menos 5 dígitos. As rotas de atualizar e excluir continuam usando o `cpf` |
| `registration` | Registro no conselho (CRM, CRO...). Pode ser `null` |
| `status` | `ativo`, `ferias` ou `inativo` |

### `GET /doctors/search` — Buscar médicos

| | |
|---|---|
| **URL** | `/doctors/search?name=Dr. João Souza` |
| **Acesso** | 🔒 Logado |

**Entrada (query string, todos opcionais — combinados com "E"):**

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `name` | texto | Nome (busca exata) |
| `email` | texto | Email (busca exata) |
| `cpf` | texto | CPF |
| `status` | texto | `ativo`, `ferias` ou `inativo` |

**Saída `200`:** lista no mesmo formato de `/doctors/list`.

### `POST /doctors/create` — Cadastrar médico

| | |
|---|---|
| **URL** | `/doctors/create` |
| **Acesso** | 🔑 admin/dev |

**Entrada (JSON):**

```json
{
  "name": "Dr. João Souza",
  "cpf": "98765432100",
  "email": "joao@clinica.com",
  "tel": "(11) 3333-4444",
  "doctor_specialty": "Cardiologia",
  "registration": "CRM-SP 123456",
  "status": "ativo"
}
```

`registration` e `status` são opcionais (o padrão de `status` é `ativo`); os outros campos são obrigatórios.

**Saída `200`:**

```json
{ "cpf": "98765432100" }
```

**Erros:** `403` sem permissão · `409` CPF já está em uso · `422` CPF ou status inválido.

### `PUT /doctors/update` — Atualizar médico

| | |
|---|---|
| **URL** | `/doctors/update?cpf=98765432100` |
| **Acesso** | 🔑 admin/dev |

**Entrada:**

- Query string: `cpf` — CPF atual do médico.
- Corpo (JSON), só os campos que mudam: `name`, `email`, `tel`, `doctor_specialty`, `cpf`, `registration`, `status`.

```json
{ "status": "ferias" }
```

Os agendamentos ficam ligados ao médico pelo CPF. Por isso, renomear o médico já muda o nome mostrado nos agendamentos dele, e trocar o CPF leva os agendamentos junto.

**Saída `200`:**

```json
{ "cpf": "98765432100" }
```

**Erros:** `400` nenhum campo enviado · `403` sem permissão · `404` médico não encontrado · `409` novo CPF já está em uso · `422` CPF ou status inválido.

### `DELETE /doctors/delete` — Excluir médico

| | |
|---|---|
| **URL** | `/doctors/delete?cpf=98765432100` |
| **Acesso** | 🔑 admin/dev |

**Entrada (query string):** `cpf`.

**Saída `200`:**

```json
{ "cpf": "98765432100" }
```

**Erros:** `403` sem permissão · `404` médico não encontrado.

---

## Agendamentos — `/appointments`

Todas as rotas de agendamento devolvem o agendamento no formato abaixo (as rotas de busca devolvem uma lista dele):

```json
{
  "id": "00073",
  "patient_name": "Maria Silva",
  "patient_cpf": "12345678909",
  "doctor_cpf": "98765432100",
  "doctor_name": "Dr. João Souza",
  "date": "2026-11-10",
  "time": "14:00:00",
  "status": "pendente",
  "reason": null,
  "is_checked": false
}
```

| Campo | Descrição |
|---|---|
| `id` | Número do agendamento, sempre com pelo menos 5 dígitos (`"00073"`). Nas rotas que recebem `id`, tanto `73` quanto `00073` funcionam |
| `doctor_cpf` | CPF do médico. É ele que liga o agendamento ao cadastro do médico |
| `doctor_name` | Nome atual do médico, vindo do cadastro (acompanha uma renomeação) |
| `status` | `pendente`, `confirmado`, `concluido`, `ausente` ou `cancelado` |
| `reason` | Motivo da ausência ou do cancelamento. É `null` nos outros status |
| `is_checked` | Mantido para compatibilidade: `true` quando `status` é `confirmado` |

Consultas com status `cancelado` liberam o horário: dá para marcar outra consulta com o mesmo médico, na mesma data e hora.

### `GET /appointments/list` — Listar agendamentos

| | |
|---|---|
| **URL** | `/appointments/list` |
| **Acesso** | 🔒 Logado |
| **Entrada** | — |

**Saída `200`:** lista de agendamentos.

### `GET /appointments/search` — Buscar agendamentos

| | |
|---|---|
| **URL** | `/appointments/search?doctor_cpf=98765432100&date=2026-11-10` |
| **Acesso** | 🔒 Logado |

**Entrada (query string, todos opcionais — combinados com "E"):**

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `patient_cpf` | texto | CPF do paciente |
| `doctor_cpf` | texto | CPF do médico |
| `doctor_name` | texto | Nome atual do médico (busca exata) |
| `status` | texto | `pendente`, `confirmado`, `concluido`, `ausente` ou `cancelado` |
| `date` | data | `AAAA-MM-DD` |
| `time` | horário | `HH:MM:SS` |

**Saída `200`:** lista de agendamentos.

### `POST /appointments/create` — Criar agendamento

| | |
|---|---|
| **URL** | `/appointments/create` |
| **Acesso** | 🔒 Logado |

**Entrada (JSON), todos obrigatórios:**

```json
{
  "patient_name": "Maria Silva",
  "patient_cpf": "12345678909",
  "doctor_cpf": "98765432100",
  "date": "2026-11-10",
  "time": "14:00:00"
}
```

O médico precisa estar cadastrado em `/doctors`. No lugar de `doctor_cpf` ainda dá para mandar `doctor_name` (o front antigo faz isso): a API procura o médico pelo nome e guarda o CPF dele.

Para conseguir enviar a mensagem de confirmação depois, o paciente com esse CPF precisa estar cadastrado em `/patients`.

**Saída `200`:** o agendamento criado, com `status: "pendente"`.

**Erros:** `404` médico não encontrado · `409` o médico já tem consulta nessa data e horário, ou há mais de um médico com o nome enviado · `422` CPF inválido ou médico não informado.

### `PUT /appointments/update` — Atualizar agendamento

| | |
|---|---|
| **URL** | `/appointments/update?id=00073` |
| **Acesso** | 🔒 Logado |

**Entrada:**

- Query string: `id`.
- Corpo (JSON), só os campos que mudam: `patient_name`, `patient_cpf`, `doctor_cpf` (ou `doctor_name`), `date`, `time`. Para mudar o status, use `PUT /appointments/status` (mais abaixo).

```json
{ "time": "15:30:00" }
```

**Saída `200`:** o agendamento atualizado.

**Erros:** `400` nenhum campo enviado · `404` agendamento ou médico não encontrado · `409` o médico já tem consulta no novo horário · `422` id ou CPF inválido.

### `DELETE /appointments/delete` — Excluir agendamento

| | |
|---|---|
| **URL** | `/appointments/delete?id=00073` |
| **Acesso** | 🔒 Logado |

**Entrada (query string):** `id`.

**Saída `200`:** o agendamento excluído.

**Erros:** `404` agendamento não encontrado · `422` id inválido.

### `GET /appointments/notify/whatsapp-link` — Mensagem pronta para WhatsApp

Não envia nada: devolve um link `wa.me` que abre o WhatsApp (app ou Web) na conversa com o paciente, com a mensagem já escrita. O recepcionista só aperta **Enviar**.

| | |
|---|---|
| **URL** | `/appointments/notify/whatsapp-link?id=00073` |
| **Acesso** | 🔒 Logado |

**Entrada (query string):**

| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `id` | texto | — | Id do agendamento |
| `with_link` | `true`/`false` | `false` | Se `true`, a mensagem de confirmação leva o link para o próprio paciente confirmar (veja o [fluxo](#fluxo-de-confirmação-de-consulta)). Não tem efeito no lembrete |

A mensagem depende do status da consulta (veja os [modelos](#modelos-de-mensagem)).

**Saída `200`:**

```json
{
  "channel": "whatsapp",
  "template": "confirmacao",
  "to": "5511988887777",
  "url": "https://wa.me/5511988887777?text=Ol%C3%A1%2C%20Maria%20Silva%21..."
}
```

`template` diz qual modelo foi usado: `confirmacao` ou `lembrete`.

**Erros:** `404` agendamento não encontrado, ou paciente com esse CPF não cadastrado · `409` consulta concluída, ausente ou cancelada (não há mensagem para enviar) · `422` id inválido.

### `GET /appointments/notify/email-link` — Mensagem pronta para email

Não envia nada: devolve um link `mailto:` que abre o programa de email do computador com destinatário, assunto e texto preenchidos.

| | |
|---|---|
| **URL** | `/appointments/notify/email-link?id=00073` |
| **Acesso** | 🔒 Logado |

**Entrada (query string):** igual à de `/notify/whatsapp-link` (`id` e `with_link`).

**Saída `200`:**

```json
{
  "channel": "email",
  "template": "confirmacao",
  "to": "maria@example.com",
  "url": "mailto:maria@example.com?subject=Confirme%20sua%20consulta&body=Ol%C3%A1%2C%20Maria..."
}
```

**Erros:** `404` agendamento não encontrado, ou paciente não cadastrado · `409` consulta concluída, ausente ou cancelada · `422` id inválido.

#### Modelos de mensagem

O texto é igual nos dois canais; o que muda é o status da consulta:

| Status | Modelo (`template`) | Assunto do email |
|---|---|---|
| `pendente` | `confirmacao` — pede a confirmação | "Confirme sua consulta" |
| `confirmado` | `lembrete` — lembra a data e o horário | "Lembrete da sua consulta" |
| `concluido`, `ausente`, `cancelado` | nenhum: a rota responde `409` | — |

Confirmação, com `with_link=false` (padrão):

```text
Olá, Maria Silva! Você tem uma consulta marcada com Dr. João Souza no dia 10/11/2026 às 14:00. Responda SIM para confirmar sua presença ou NÃO caso não possa comparecer.
Atendimento: recepcao (recepcao@clinica.com)
```

Confirmação, com `with_link=true`:

```text
Olá, Maria Silva! Você tem uma consulta marcada com Dr. João Souza no dia 10/11/2026 às 14:00. Confirme sua presença: https://minha-agenda-flax-tau.vercel.app/appointments/confirm?id=73&token=...
Atendimento: recepcao (recepcao@clinica.com)
```

Lembrete (o `with_link` é ignorado, porque a consulta já está confirmada):

```text
Olá, Maria Silva! Lembrete: sua consulta com Dr. João Souza é no dia 10/11/2026 às 14:00. Caso não possa comparecer, avise respondendo esta mensagem.
Atendimento: recepcao (recepcao@clinica.com)
```

A linha "Atendimento" usa o usuário logado que gerou a mensagem.

Exemplo de uso no front (as rotas exigem o token, por isso não dá para usar um `<a href>` direto):

```js
async function abrirMensagem(id, canal, withLink = false) { // canal: "whatsapp" ou "email"
  const r = await fetch(
    `${API}/appointments/notify/${canal}-link?id=${id}&with_link=${withLink}`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  if (!r.ok) return alert((await r.json()).detail);
  const { url } = await r.json();
  window.open(url, "_blank");
}
```

### `PUT /appointments/check` — Recepcionista marca a confirmação

Usada quando o paciente responde a mensagem: o recepcionista marca (ou desmarca) a presença no sistema.

| | |
|---|---|
| **URL** | `/appointments/check?id=00073&is_checked=true` |
| **Acesso** | 🔒 Logado |

**Entrada (query string):**

| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `id` | texto | — | Id do agendamento |
| `is_checked` | `true`/`false` | `true` | `true` = status `confirmado`; `false` = volta para `pendente` |

**Saída `200`:** o agendamento com o status atualizado.

**Erros:** `404` agendamento não encontrado · `409` o horário já foi ocupado por outra consulta (ao reativar uma cancelada) · `422` id inválido.

### `PUT /appointments/status` — Mudar o status da consulta

Para concluir a consulta, marcar o paciente como ausente, cancelar, ou voltar para pendente/confirmado.

| | |
|---|---|
| **URL** | `/appointments/status?id=00073&status=cancelado&reason=Paciente viajou` |
| **Acesso** | 🔒 Logado |

**Entrada (query string):**

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `id` | texto | Id do agendamento |
| `status` | texto | `pendente`, `confirmado`, `concluido`, `ausente` ou `cancelado` |
| `reason` | texto (opcional) | Motivo. Só é guardado para `ausente` e `cancelado`; nos outros status o motivo é apagado |

**Saída `200`:** o agendamento com o status atualizado.

**Erros:** `404` agendamento não encontrado · `409` o horário já foi ocupado por outra consulta (ao reativar uma cancelada) · `422` id ou status inválido.

### `GET /appointments/confirm` — Página de confirmação do paciente

É a rota do link enviado quando `with_link=true`. O paciente abre no navegador (celular ou computador), sem precisar de login, e vê uma **página** (HTML, não JSON) com o médico, a data e o horário da consulta e um botão **Confirmar presença**.

**Abrir o link não confirma nada.** Quem confirma é o botão, que chama `POST /appointments/confirm`. Assim a prévia de link que o WhatsApp e os programas de email geram sozinhos não confirma a consulta no lugar do paciente.

| | |
|---|---|
| **URL** | `/appointments/confirm?id=73&token=Xy9...` |
| **Acesso** | 🌐 Público (protegido pelo `token`) |

**Entrada (query string):**

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `id` | texto | Id do agendamento |
| `token` | texto | Token secreto do agendamento, já incluído no link gerado pela API |

**O que a página mostra:**

| Situação | Página | Status HTTP |
|---|---|---|
| Consulta pendente | Dados da consulta + botão **Confirmar presença** | `200` |
| Já confirmada | "Presença confirmada", sem botão | `200` |
| Cancelada, concluída, ausente ou com a data já passada | "Não é possível confirmar", com o motivo | `409` |
| id ou token errado | "Link inválido", sem nenhum dado da consulta | `404` |

### `POST /appointments/confirm` — Botão "Confirmar presença"

Recebe o formulário da página acima (`application/x-www-form-urlencoded`, campos `id` e `token`) e confirma a consulta. Devolve a página "Presença confirmada", ou as mesmas páginas de erro do `GET`.

**Segurança do link:**

- A página não mostra o CPF nem o sobrenome do paciente, só o primeiro nome.
- O token é comparado em tempo constante e só vale para consultas pendentes ou confirmadas até o dia da consulta (horário de Brasília).
- As páginas vão com `Cache-Control: no-store`, `Referrer-Policy: no-referrer` (o token não vaza para outros sites), `X-Robots-Tag: noindex` e uma `Content-Security-Policy` que bloqueia scripts e impede a página de ser aberta dentro de outro site.

---

## Fluxo de confirmação de consulta

Há duas formas de confirmar; nenhuma tem custo de envio, porque a mensagem sai do WhatsApp/email do próprio recepcionista.

**1. Paciente responde, recepcionista confirma (padrão)**

1. Recepcionista chama `GET /appointments/notify/whatsapp-link?id=...` (ou `email-link`) e abre a `url` devolvida.
2. Aperta **Enviar** no WhatsApp/email.
3. O paciente responde "SIM" ou "NÃO".
4. Recepcionista chama `PUT /appointments/check?id=...` se a resposta foi "SIM", ou `PUT /appointments/status?id=...&status=cancelado&reason=...` se foi "NÃO".

**2. Paciente confirma sozinho pelo link**

1. Recepcionista chama `GET /appointments/notify/whatsapp-link?id=...&with_link=true` e envia a mensagem.
2. O paciente clica no link, que abre a página `GET /appointments/confirm?id=...&token=...` com os dados da consulta.
3. O paciente aperta **Confirmar presença**, e o agendamento fica com `status: "confirmado"` sem ação do recepcionista.

Depois da consulta, o recepcionista usa `PUT /appointments/status` com `concluido` ou `ausente`.

> O link aponta para `APP_BASE_URL`, então ele precisa estar configurado na Vercel com o endereço da API (`https://minha-agenda-flax-tau.vercel.app`).
