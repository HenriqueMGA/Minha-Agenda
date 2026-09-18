from fastapi import HTTPException
from psycopg2.errors import UniqueViolation

from src.db.db_conection import get_connection
from src.models.medicos import DoctorResponse


def create_doctors_table():
    with get_connection() as conexao:
        cursor = conexao.cursor()
        cursor.execute(
            """
                CREATE SCHEMA IF NOT EXISTS minhaagenda;

                CREATE TABLE IF NOT EXISTS minhaagenda.doctors (
                    cpf VARCHAR(11) PRIMARY KEY,
                    nome VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    tel VARCHAR(20) NOT NULL,
                    doctor_specialty VARCHAR(100) NOT NULL
                );
            """
        )
        cursor.close()


def list_doctors():
    with get_connection() as conexao:
        cursor = conexao.cursor()
        cursor.execute('SELECT cpf, nome, email, tel, doctor_specialty FROM minhaagenda.doctors')
        dados = cursor.fetchall()
        cursor.close()
        return [
            DoctorResponse(cpf=row[0], name=row[1], email=row[2], tel=row[3], doctor_specialty=row[4])
            for row in dados
        ]


def search_doctor(name: str | None = None, email: str | None = None, cpf: str | None = None):
    filtros = []
    params = {}

    if name is not None:
        filtros.append("nome = %(name)s")
        params["name"] = name
    if email is not None:
        filtros.append("email = %(email)s")
        params["email"] = email
    if cpf is not None:
        filtros.append("cpf = %(cpf)s")
        params["cpf"] = cpf

    where = " AND ".join(filtros) if filtros else "TRUE"

    with get_connection() as conexao:
        cursor = conexao.cursor()
        cursor.execute(f"SELECT cpf, nome, email, tel, doctor_specialty FROM minhaagenda.doctors WHERE {where}", params)
        dados = cursor.fetchall()
        cursor.close()
        return [
            DoctorResponse(cpf=row[0], name=row[1], email=row[2], tel=row[3], doctor_specialty=row[4])
            for row in dados
        ]


def create_doctor(body):

    doctor = search_doctor(cpf=body.cpf)
    if doctor:
        raise HTTPException(status_code=409, detail="CPF já está em uso")

    params = {
        "name": body.name,
        "cpf": body.cpf,
        "tel": body.tel,
        "email": body.email,
        "doctor_specialty": body.doctor_specialty,
    }

    try:
        with get_connection() as conexao:
            cursor = conexao.cursor()
            cursor.execute(
                """
                    INSERT INTO minhaagenda.doctors (nome, cpf, tel, email, doctor_specialty)
                    VALUES (%(name)s, %(cpf)s, %(tel)s, %(email)s, %(doctor_specialty)s)
                    RETURNING cpf
                """,
                params,
            )
            new_cpf = cursor.fetchone()[0]
            cursor.close()
    except UniqueViolation:
        raise HTTPException(status_code=409, detail="CPF já está em uso")

    return {"cpf": new_cpf}


def del_doctor(cpf: str):

    doctor = search_doctor(cpf=cpf)
    if not doctor:
        raise HTTPException(status_code=404, detail="Médico não encontrado")

    with get_connection() as conexao:
        cursor = conexao.cursor()
        cursor.execute(
            "DELETE FROM minhaagenda.doctors WHERE cpf = %(cpf)s RETURNING cpf",
            {"cpf": cpf},
        )
        row = cursor.fetchone()
        cursor.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Médico não encontrado")

    return {"cpf": row[0]}


def modify_doctor(cpf: str, body):

    doctor = search_doctor(cpf=cpf)
    if not doctor:
        raise HTTPException(status_code=404, detail="Médico não encontrado")

    campos = []
    params = {"current_cpf": cpf}

    if body.name is not None:
        campos.append("nome = %(name)s")
        params["name"] = body.name
    if body.email is not None:
        campos.append("email = %(email)s")
        params["email"] = body.email
    if body.tel is not None:
        campos.append("tel = %(tel)s")
        params["tel"] = body.tel
    if body.doctor_specialty is not None:
        campos.append("doctor_specialty = %(doctor_specialty)s")
        params["doctor_specialty"] = body.doctor_specialty
    if body.cpf is not None and body.cpf != cpf:
        if search_doctor(cpf=body.cpf):
            raise HTTPException(status_code=409, detail="CPF já está em uso")
        campos.append("cpf = %(new_cpf)s")
        params["new_cpf"] = body.cpf

    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    set_clause = ", ".join(campos)

    try:
        with get_connection() as conexao:
            cursor = conexao.cursor()
            cursor.execute(
                f"UPDATE minhaagenda.doctors SET {set_clause} WHERE cpf = %(current_cpf)s RETURNING cpf",
                params,
            )
            row = cursor.fetchone()
            cursor.close()
    except UniqueViolation:
        raise HTTPException(status_code=409, detail="CPF já está em uso")

    if row is None:
        raise HTTPException(status_code=404, detail="Médico não encontrado")

    return {"cpf": row[0]}
