from argon2 import PasswordHasher
from fastapi import HTTPException
from psycopg2.errors import UniqueViolation

from src.db.db_conection import get_connection
from src.models.users import UserResponse

password_hasher = PasswordHasher()


def create_users_table():
    with get_connection() as conexao:
        cursor = conexao.cursor()
        cursor.execute(
            """
                CREATE SCHEMA IF NOT EXISTS minhaagenda;

                CREATE TABLE IF NOT EXISTS minhaagenda.users (
                    email VARCHAR(255) PRIMARY KEY,
                    nome VARCHAR(255) NOT NULL,
                    username VARCHAR(50) NOT NULL,
                    senha VARCHAR(255) NOT NULL,
                    tipo VARCHAR(20) NOT NULL
                );
            """
        )
        cursor.close()


def get_user_credentials(email: str):
    """Uso interno da autenticação: retorna (email, senha_hash, tipo) ou None. Nunca exponha via rota."""
    with get_connection() as conexao:
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT email, senha, tipo FROM minhaagenda.users WHERE email = %(email)s",
            {"email": email},
        )
        row = cursor.fetchone()
        cursor.close()
        return row


def list_users():
    with get_connection() as conexao:
        cursor = conexao.cursor()
        cursor.execute('SELECT email, username FROM minhaagenda.users')
        dados = cursor.fetchall()
        cursor.close()
        return [UserResponse(email=row[0], username=row[1]) for row in dados]


def search_user(name: str | None = None, email: str | None = None, username: str | None = None, type: str | None = None):
    filtros = []
    params = {}

    if name is not None:
        filtros.append("nome = %(name)s")
        params["name"] = name
    if email is not None:
        filtros.append("email = %(email)s")
        params["email"] = email
    if username is not None:
        filtros.append("username = %(username)s")
        params["username"] = username
    if type is not None:
        filtros.append("tipo = %(type)s")
        params["type"] = type
    

    where = " AND ".join(filtros) if filtros else "TRUE"

    with get_connection() as conexao:
        cursor = conexao.cursor()
        cursor.execute(f"SELECT email, username FROM minhaagenda.users WHERE {where}", params)
        dados = cursor.fetchall()
        cursor.close()
        return [UserResponse(email=row[0], username=row[1]) for row in dados]


def create_user(body):

    user = search_user(email=body.email)
    if user:
        raise HTTPException(status_code=409, detail="Email já está em uso")

    params = {
        "name": body.name,
        "username": body.username,
        "password": password_hasher.hash(body.password),
        "email": body.email,
        "type": body.type,
    }

    try:
        with get_connection() as conexao:
            cursor = conexao.cursor()
            cursor.execute(
                """
                    INSERT INTO minhaagenda.users (nome, username, senha, email, tipo)
                    VALUES (%(name)s, %(username)s, %(password)s, %(email)s, %(type)s)
                    RETURNING email
                """,
                params,
            )
            new_email = cursor.fetchone()[0]
            cursor.close()
    except UniqueViolation:
        raise HTTPException(status_code=409, detail="Email já está em uso")

    return {"email": new_email}


def del_user(email: str):

    user = search_user(email=email)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    with get_connection() as conexao:
        cursor = conexao.cursor()
        cursor.execute(
            "DELETE FROM minhaagenda.users WHERE email = %(email)s RETURNING email",
            {"email": email},
        )
        row = cursor.fetchone()
        cursor.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    return {"email": row[0]}


def modify_user(email: str, body):

    user = search_user(email=email)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    campos = []
    params = {"current_email": email}

    if body.name is not None:
        campos.append("nome = %(name)s")
        params["name"] = body.name
    if body.username is not None:
        campos.append("username = %(username)s")
        params["username"] = body.username
    if body.password is not None:
        campos.append("senha = %(password)s")
        params["password"] = password_hasher.hash(body.password)
    if body.type is not None:
        campos.append("tipo = %(type)s")
        params["type"] = body.type
    if body.email is not None and body.email != email:
        if search_user(email=body.email):
            raise HTTPException(status_code=409, detail="Email já está em uso")
        campos.append("email = %(new_email)s")
        params["new_email"] = body.email

    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    set_clause = ", ".join(campos)

    try:
        with get_connection() as conexao:
            cursor = conexao.cursor()
            cursor.execute(
                f"UPDATE minhaagenda.users SET {set_clause} WHERE email = %(current_email)s RETURNING email",
                params,
            )
            row = cursor.fetchone()
            cursor.close()
    except UniqueViolation:
        raise HTTPException(status_code=409, detail="Email já está em uso")

    if row is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    return {"email": row[0]}
