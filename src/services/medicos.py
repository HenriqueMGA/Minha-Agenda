from fastapi import HTTPException
from psycopg2.errors import UniqueViolation

from src.db.db_conection import get_connection
from src.models.medicos import DoctorResponse

_COLUMNS = "id, cpf, nome, email, tel, doctor_specialty, registration, status"


def create_doctors_table():
    with get_connection() as conexao:
        cursor = conexao.cursor()
        cursor.execute(
            """
                CREATE SCHEMA IF NOT EXISTS minhaagenda;

                CREATE TABLE IF NOT EXISTS minhaagenda.doctors (
                    id SERIAL UNIQUE,
                    cpf VARCHAR(11) PRIMARY KEY,
                    nome VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    tel VARCHAR(20) NOT NULL,
                    doctor_specialty VARCHAR(100) NOT NULL,
                    registration VARCHAR(30),
                    status VARCHAR(20) NOT NULL DEFAULT 'ativo'
                );

                -- Migração de tabelas criadas antes desses campos existirem
                ALTER TABLE minhaagenda.doctors ADD COLUMN IF NOT EXISTS id SERIAL UNIQUE;
                ALTER TABLE minhaagenda.doctors ADD COLUMN IF NOT EXISTS registration VARCHAR(30);
                ALTER TABLE minhaagenda.doctors ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'ativo';
            """
        )
        cursor.close()


def _to_response(row):
    return DoctorResponse(
        id=str(row[0]).zfill(5),
        cpf=row[1],
        name=row[2],
        email=row[3],
        tel=row[4],
        doctor_specialty=row[5],
        registration=row[6],
        status=row[7],
    )


def list_doctors():
    with get_connection() as conexao:
        cursor = conexao.cursor()
        cursor.execute(f"SELECT {_COLUMNS} FROM minhaagenda.doctors ORDER BY id")
        dados = cursor.fetchall()
        cursor.close()
        return [_to_response(row) for row in dados]


def search_doctor(name: str | None = None, email: str | None = None, cpf: str | None = None, status: str | None = None):
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
    if status is not None:
        filtros.append("status = %(status)s")
        params["status"] = status

    where = " AND ".join(filtros) if filtros else "TRUE"

    with get_connection() as conexao:
        cursor = conexao.cursor()
        cursor.execute(f"SELECT {_COLUMNS} FROM minhaagenda.doctors WHERE {where} ORDER BY id", params)
        dados = cursor.fetchall()
        cursor.close()
        return [_to_response(row) for row in dados]


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
        "registration": body.registration,
        "status": body.status,
    }

    try:
        with get_connection() as conexao:
            cursor = conexao.cursor()
            cursor.execute(
                """
                    INSERT INTO minhaagenda.doctors (nome, cpf, tel, email, doctor_specialty, registration, status)
                    VALUES (%(name)s, %(cpf)s, %(tel)s, %(email)s, %(doctor_specialty)s, %(registration)s, %(status)s)
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
    if body.registration is not None:
        campos.append("registration = %(registration)s")
        params["registration"] = body.registration
    if body.status is not None:
        campos.append("status = %(status)s")
        params["status"] = body.status
    cpf_mudou = body.cpf is not None and body.cpf != cpf
    if cpf_mudou:
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
            # Os agendamentos guardam o CPF do médico, então acompanham a troca
            if row is not None and cpf_mudou:
                cursor.execute(
                    "UPDATE minhaagenda.appointments SET doctor_cpf = %(new_cpf)s WHERE doctor_cpf = %(current_cpf)s",
                    params,
                )
            cursor.close()
    except UniqueViolation:
        raise HTTPException(status_code=409, detail="CPF já está em uso")

    if row is None:
        raise HTTPException(status_code=404, detail="Médico não encontrado")

    return {"cpf": row[0]}
