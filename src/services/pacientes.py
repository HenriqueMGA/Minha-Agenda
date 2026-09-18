from fastapi import HTTPException
from psycopg2.errors import UniqueViolation

from src.db.db_conection import get_connection
from src.models.pacientes import PatientResponse


def create_patients_table():
    with get_connection() as conexao:
        cursor = conexao.cursor()
        cursor.execute(
            """
                CREATE SCHEMA IF NOT EXISTS minhaagenda;

                CREATE TABLE IF NOT EXISTS minhaagenda.patients (
                    cpf VARCHAR(11) PRIMARY KEY,
                    nome VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    tel VARCHAR(20) NOT NULL,
                    dt_nasc DATE NOT NULL
                );
            """
        )
        cursor.close()


def list_patients():
    with get_connection() as conexao:
        cursor = conexao.cursor()
        cursor.execute('SELECT cpf, nome, email, tel, dt_nasc FROM minhaagenda.patients')
        dados = cursor.fetchall()
        cursor.close()
        return [
            PatientResponse(cpf=row[0], name=row[1], email=row[2], tel=row[3], dt_nasc=row[4])
            for row in dados
        ]


def search_patient(name: str | None = None, email: str | None = None, cpf: str | None = None):
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
        cursor.execute(f"SELECT cpf, nome, email, tel, dt_nasc FROM minhaagenda.patients WHERE {where}", params)
        dados = cursor.fetchall()
        cursor.close()
        return [
            PatientResponse(cpf=row[0], name=row[1], email=row[2], tel=row[3], dt_nasc=row[4])
            for row in dados
        ]


def create_patient(body):

    patient = search_patient(cpf=body.cpf)
    if patient:
        raise HTTPException(status_code=409, detail="CPF já está em uso")

    params = {
        "name": body.name,
        "cpf": body.cpf,
        "tel": body.tel,
        "email": body.email,
        "dt_nasc": body.dt_nasc,
    }

    try:
        with get_connection() as conexao:
            cursor = conexao.cursor()
            cursor.execute(
                """
                    INSERT INTO minhaagenda.patients (nome, cpf, tel, email, dt_nasc)
                    VALUES (%(name)s, %(cpf)s, %(tel)s, %(email)s, %(dt_nasc)s)
                    RETURNING cpf
                """,
                params,
            )
            new_cpf = cursor.fetchone()[0]
            cursor.close()
    except UniqueViolation:
        raise HTTPException(status_code=409, detail="CPF já está em uso")

    return {"cpf": new_cpf}


def del_patient(cpf: str):

    patient = search_patient(cpf=cpf)
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")

    with get_connection() as conexao:
        cursor = conexao.cursor()
        cursor.execute(
            "DELETE FROM minhaagenda.patients WHERE cpf = %(cpf)s RETURNING cpf",
            {"cpf": cpf},
        )
        row = cursor.fetchone()
        cursor.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")

    return {"cpf": row[0]}


def modify_patient(cpf: str, body):

    patient = search_patient(cpf=cpf)
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")

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
    if body.dt_nasc is not None:
        campos.append("dt_nasc = %(dt_nasc)s")
        params["dt_nasc"] = body.dt_nasc
    if body.cpf is not None and body.cpf != cpf:
        if search_patient(cpf=body.cpf):
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
                f"UPDATE minhaagenda.patients SET {set_clause} WHERE cpf = %(current_cpf)s RETURNING cpf",
                params,
            )
            row = cursor.fetchone()
            cursor.close()
    except UniqueViolation:
        raise HTTPException(status_code=409, detail="CPF já está em uso")

    if row is None:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")

    return {"cpf": row[0]}
