from datetime import date, time

from fastapi import HTTPException
from psycopg2.errors import UniqueViolation

from src.db.db_conection import get_connection
from src.models.agenda import AppointmentResponse


def create_appointments_table():
    with get_connection() as conexao:
        cursor = conexao.cursor()
        cursor.execute(
            """
                CREATE SCHEMA IF NOT EXISTS minhaagenda;

                CREATE TABLE IF NOT EXISTS minhaagenda.appointments (
                    id SERIAL PRIMARY KEY,
                    patient_name VARCHAR(255) NOT NULL,
                    patient_cpf VARCHAR(11) NOT NULL,
                    doctor_name VARCHAR(255) NOT NULL,
                    appointment_date DATE NOT NULL,
                    appointment_time TIME NOT NULL,
                    UNIQUE (doctor_name, appointment_date, appointment_time)
                );
            """
        )
        cursor.close()


def _to_response(row):
    return AppointmentResponse(
        id=row[0],
        patient_name=row[1],
        patient_cpf=row[2],
        doctor_name=row[3],
        date=row[4],
        time=row[5],
    )


def list_appointments():
    with get_connection() as conexao:
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT id, patient_name, patient_cpf, doctor_name, appointment_date, appointment_time "
            "FROM minhaagenda.appointments"
        )
        dados = cursor.fetchall()
        cursor.close()
        return [_to_response(row) for row in dados]


def search_appointment(
    id: int | None = None,
    patient_cpf: str | None = None,
    doctor_name: str | None = None,
    date: date | None = None,
    time: time | None = None,
):
    filtros = []
    params = {}

    if id is not None:
        filtros.append("id = %(id)s")
        params["id"] = id
    if patient_cpf is not None:
        filtros.append("patient_cpf = %(patient_cpf)s")
        params["patient_cpf"] = patient_cpf
    if doctor_name is not None:
        filtros.append("doctor_name = %(doctor_name)s")
        params["doctor_name"] = doctor_name
    if date is not None:
        filtros.append("appointment_date = %(date)s")
        params["date"] = date
    if time is not None:
        filtros.append("appointment_time = %(time)s")
        params["time"] = time

    where = " AND ".join(filtros) if filtros else "TRUE"

    with get_connection() as conexao:
        cursor = conexao.cursor()
        cursor.execute(
            f"SELECT id, patient_name, patient_cpf, doctor_name, appointment_date, appointment_time "
            f"FROM minhaagenda.appointments WHERE {where}",
            params,
        )
        dados = cursor.fetchall()
        cursor.close()
        return [_to_response(row) for row in dados]


def create_appointment(body):

    conflito = search_appointment(doctor_name=body.doctor_name, date=body.date, time=body.time)
    if conflito:
        raise HTTPException(
            status_code=409,
            detail="Já existe uma consulta marcada para esse profissional nessa data e horário",
        )

    params = {
        "patient_name": body.patient_name,
        "patient_cpf": body.patient_cpf,
        "doctor_name": body.doctor_name,
        "date": body.date,
        "time": body.time,
    }

    try:
        with get_connection() as conexao:
            cursor = conexao.cursor()
            cursor.execute(
                """
                    INSERT INTO minhaagenda.appointments (patient_name, patient_cpf, doctor_name, appointment_date, appointment_time)
                    VALUES (%(patient_name)s, %(patient_cpf)s, %(doctor_name)s, %(date)s, %(time)s)
                    RETURNING id, patient_name, patient_cpf, doctor_name, appointment_date, appointment_time
                """,
                params,
            )
            row = cursor.fetchone()
            cursor.close()
    except UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="Já existe uma consulta marcada para esse profissional nessa data e horário",
        )

    return _to_response(row)


def del_appointment(id: int):

    appointment = search_appointment(id=id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    with get_connection() as conexao:
        cursor = conexao.cursor()
        cursor.execute(
            "DELETE FROM minhaagenda.appointments WHERE id = %(id)s "
            "RETURNING id, patient_name, patient_cpf, doctor_name, appointment_date, appointment_time",
            {"id": id},
        )
        row = cursor.fetchone()
        cursor.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    return _to_response(row)


def modify_appointment(id: int, body):

    existentes = search_appointment(id=id)
    if not existentes:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    atual = existentes[0]

    campos = []
    params = {"id": id}

    if body.patient_name is not None:
        campos.append("patient_name = %(patient_name)s")
        params["patient_name"] = body.patient_name
    if body.patient_cpf is not None:
        campos.append("patient_cpf = %(patient_cpf)s")
        params["patient_cpf"] = body.patient_cpf
    if body.doctor_name is not None:
        campos.append("doctor_name = %(doctor_name)s")
        params["doctor_name"] = body.doctor_name
    if body.date is not None:
        campos.append("appointment_date = %(date)s")
        params["date"] = body.date
    if body.time is not None:
        campos.append("appointment_time = %(time)s")
        params["time"] = body.time

    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    if body.doctor_name is not None or body.date is not None or body.time is not None:
        novo_doctor = body.doctor_name if body.doctor_name is not None else atual.doctor_name
        novo_date = body.date if body.date is not None else atual.date
        novo_time = body.time if body.time is not None else atual.time

        conflito = [
            c for c in search_appointment(doctor_name=novo_doctor, date=novo_date, time=novo_time)
            if c.id != id
        ]
        if conflito:
            raise HTTPException(
                status_code=409,
                detail="Já existe uma consulta marcada para esse profissional nessa data e horário",
            )

    set_clause = ", ".join(campos)

    try:
        with get_connection() as conexao:
            cursor = conexao.cursor()
            cursor.execute(
                f"UPDATE minhaagenda.appointments SET {set_clause} WHERE id = %(id)s "
                f"RETURNING id, patient_name, patient_cpf, doctor_name, appointment_date, appointment_time",
                params,
            )
            row = cursor.fetchone()
            cursor.close()
    except UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="Já existe uma consulta marcada para esse profissional nessa data e horário",
        )

    if row is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    return _to_response(row)
