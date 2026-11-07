import secrets
from datetime import date, datetime, time, timedelta, timezone

from fastapi import HTTPException
from psycopg2.errors import UniqueViolation

from src.db.db_conection import get_connection
from src.models.agenda import STATUS_WITH_REASON, AppointmentResponse
from src.services.medicos import search_doctor

# O nome do médico vem do cadastro (pelo CPF), então acompanha uma renomeação.
# a.doctor_name fica só como reserva, caso o médico tenha sido excluído.
_SELECT = """
    SELECT a.id, a.patient_name, a.patient_cpf, a.doctor_cpf, COALESCE(d.nome, a.doctor_name),
           a.appointment_date, a.appointment_time, a.status, a.reason
    FROM minhaagenda.appointments a
    LEFT JOIN minhaagenda.doctors d ON d.cpf = a.doctor_cpf
"""

_CONFLICT_DETAIL = "Já existe uma consulta marcada para esse profissional nessa data e horário"

# O Brasil não tem mais horário de verão, então o fuso é fixo
_BRASILIA = timezone(timedelta(hours=-3))


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
                    doctor_cpf VARCHAR(11),
                    doctor_name VARCHAR(255) NOT NULL,
                    appointment_date DATE NOT NULL,
                    appointment_time TIME NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'pendente',
                    reason TEXT,
                    is_checked BOOLEAN NOT NULL DEFAULT FALSE,
                    confirmation_token VARCHAR(64) NOT NULL
                );

                -- Migração de tabelas criadas antes desses campos existirem
                ALTER TABLE minhaagenda.appointments ADD COLUMN IF NOT EXISTS doctor_cpf VARCHAR(11);
                ALTER TABLE minhaagenda.appointments ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'pendente';
                ALTER TABLE minhaagenda.appointments ADD COLUMN IF NOT EXISTS reason TEXT;

                UPDATE minhaagenda.appointments SET status = 'confirmado'
                WHERE is_checked AND status = 'pendente';

                UPDATE minhaagenda.appointments a SET doctor_cpf = d.cpf
                FROM minhaagenda.doctors d
                WHERE a.doctor_cpf IS NULL AND d.nome = a.doctor_name;

                -- Um horário por médico, sem contar consultas canceladas
                ALTER TABLE minhaagenda.appointments
                    DROP CONSTRAINT IF EXISTS appointments_doctor_name_appointment_date_appointment_time_key;
                CREATE UNIQUE INDEX IF NOT EXISTS appointments_doctor_slot_key
                    ON minhaagenda.appointments (doctor_cpf, appointment_date, appointment_time)
                    WHERE status <> 'cancelado';
            """
        )
        cursor.close()


def _to_response(row):
    return AppointmentResponse(
        id=str(row[0]).zfill(5),
        patient_name=row[1],
        patient_cpf=row[2],
        doctor_cpf=row[3],
        doctor_name=row[4],
        date=row[5],
        time=row[6],
        status=row[7],
        reason=row[8],
        is_checked=row[7] == "confirmado",
    )


def _get_appointment(id: int):
    encontrados = search_appointment(id=id)
    if not encontrados:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    return encontrados[0]


def _resolve_doctor(doctor_cpf: str | None, doctor_name: str | None):
    if doctor_cpf is not None:
        encontrados = search_doctor(cpf=doctor_cpf)
    else:
        encontrados = search_doctor(name=doctor_name)

    if not encontrados:
        raise HTTPException(status_code=404, detail="Médico não encontrado")
    if len(encontrados) > 1:
        raise HTTPException(status_code=409, detail="Há mais de um médico com esse nome; informe doctor_cpf")
    return encontrados[0]


def _has_conflict(doctor_cpf: str, date: date, time: time, ignore_id: int | None = None) -> bool:
    ocupados = search_appointment(doctor_cpf=doctor_cpf, date=date, time=time)
    return any(a.status != "cancelado" and int(a.id) != ignore_id for a in ocupados)


def get_confirmation_token(id: int) -> str | None:
    """Uso interno: nunca exponha via rota pública além do fluxo de confirmação."""
    with get_connection() as conexao:
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT confirmation_token FROM minhaagenda.appointments WHERE id = %(id)s",
            {"id": id},
        )
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row else None


def list_appointments():
    with get_connection() as conexao:
        cursor = conexao.cursor()
        cursor.execute(f"{_SELECT} ORDER BY a.appointment_date, a.appointment_time")
        dados = cursor.fetchall()
        cursor.close()
        return [_to_response(row) for row in dados]


def search_appointment(
    id: int | None = None,
    patient_cpf: str | None = None,
    doctor_cpf: str | None = None,
    doctor_name: str | None = None,
    date: date | None = None,
    time: time | None = None,
    status: str | None = None,
):
    filtros = []
    params = {}

    if id is not None:
        filtros.append("a.id = %(id)s")
        params["id"] = id
    if patient_cpf is not None:
        filtros.append("a.patient_cpf = %(patient_cpf)s")
        params["patient_cpf"] = patient_cpf
    if doctor_cpf is not None:
        filtros.append("a.doctor_cpf = %(doctor_cpf)s")
        params["doctor_cpf"] = doctor_cpf
    if doctor_name is not None:
        filtros.append("COALESCE(d.nome, a.doctor_name) = %(doctor_name)s")
        params["doctor_name"] = doctor_name
    if date is not None:
        filtros.append("a.appointment_date = %(date)s")
        params["date"] = date
    if time is not None:
        filtros.append("a.appointment_time = %(time)s")
        params["time"] = time
    if status is not None:
        filtros.append("a.status = %(status)s")
        params["status"] = status

    where = " AND ".join(filtros) if filtros else "TRUE"

    with get_connection() as conexao:
        cursor = conexao.cursor()
        cursor.execute(
            f"{_SELECT} WHERE {where} ORDER BY a.appointment_date, a.appointment_time",
            params,
        )
        dados = cursor.fetchall()
        cursor.close()
        return [_to_response(row) for row in dados]


def create_appointment(body):

    doctor = _resolve_doctor(body.doctor_cpf, body.doctor_name)

    if _has_conflict(doctor.cpf, body.date, body.time):
        raise HTTPException(status_code=409, detail=_CONFLICT_DETAIL)

    params = {
        "patient_name": body.patient_name,
        "patient_cpf": body.patient_cpf,
        "doctor_cpf": doctor.cpf,
        "doctor_name": doctor.name,
        "date": body.date,
        "time": body.time,
        "confirmation_token": secrets.token_urlsafe(32),
    }

    try:
        with get_connection() as conexao:
            cursor = conexao.cursor()
            cursor.execute(
                """
                    INSERT INTO minhaagenda.appointments
                        (patient_name, patient_cpf, doctor_cpf, doctor_name, appointment_date, appointment_time, confirmation_token)
                    VALUES
                        (%(patient_name)s, %(patient_cpf)s, %(doctor_cpf)s, %(doctor_name)s, %(date)s, %(time)s, %(confirmation_token)s)
                    RETURNING id
                """,
                params,
            )
            new_id = cursor.fetchone()[0]
            cursor.close()
    except UniqueViolation:
        raise HTTPException(status_code=409, detail=_CONFLICT_DETAIL)

    return _get_appointment(new_id)


def del_appointment(id: int):

    appointment = _get_appointment(id)

    with get_connection() as conexao:
        cursor = conexao.cursor()
        cursor.execute(
            "DELETE FROM minhaagenda.appointments WHERE id = %(id)s RETURNING id",
            {"id": id},
        )
        row = cursor.fetchone()
        cursor.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    return appointment


def modify_appointment(id: int, body):

    atual = _get_appointment(id)

    campos = []
    params = {"id": id}

    if body.patient_name is not None:
        campos.append("patient_name = %(patient_name)s")
        params["patient_name"] = body.patient_name
    if body.patient_cpf is not None:
        campos.append("patient_cpf = %(patient_cpf)s")
        params["patient_cpf"] = body.patient_cpf
    novo_doctor_cpf = atual.doctor_cpf
    if body.doctor_cpf is not None or body.doctor_name is not None:
        doctor = _resolve_doctor(body.doctor_cpf, body.doctor_name)
        novo_doctor_cpf = doctor.cpf
        campos.append("doctor_cpf = %(doctor_cpf)s")
        campos.append("doctor_name = %(doctor_name)s")
        params["doctor_cpf"] = doctor.cpf
        params["doctor_name"] = doctor.name
    if body.date is not None:
        campos.append("appointment_date = %(date)s")
        params["date"] = body.date
    if body.time is not None:
        campos.append("appointment_time = %(time)s")
        params["time"] = body.time

    if not campos:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    mudou_horario = "doctor_cpf" in params or body.date is not None or body.time is not None
    if mudou_horario and atual.status != "cancelado":
        novo_date = body.date if body.date is not None else atual.date
        novo_time = body.time if body.time is not None else atual.time
        if _has_conflict(novo_doctor_cpf, novo_date, novo_time, ignore_id=id):
            raise HTTPException(status_code=409, detail=_CONFLICT_DETAIL)

    set_clause = ", ".join(campos)

    try:
        with get_connection() as conexao:
            cursor = conexao.cursor()
            cursor.execute(
                f"UPDATE minhaagenda.appointments SET {set_clause} WHERE id = %(id)s RETURNING id",
                params,
            )
            row = cursor.fetchone()
            cursor.close()
    except UniqueViolation:
        raise HTTPException(status_code=409, detail=_CONFLICT_DETAIL)

    if row is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    return _get_appointment(id)


def _today() -> date:
    """Data de hoje no horário de Brasília (o servidor roda em UTC)."""
    return datetime.now(_BRASILIA).date()


def get_appointment_by_token(id: int, token: str):
    """Devolve o agendamento só se o token do link bater; senão, None."""
    stored = get_confirmation_token(id)
    if stored is None or not secrets.compare_digest(stored.encode(), token.encode()):
        return None
    return _get_appointment(id)


def can_be_confirmed(appointment) -> bool:
    """O link só vale para consultas pendentes ou confirmadas que ainda não passaram."""
    return appointment.status in ("pendente", "confirmado") and appointment.date >= _today()


def confirm_appointment(id: int, token: str):
    """Confirmação feita pelo paciente; não reabre consultas encerradas, canceladas ou que já passaram."""

    appointment = get_appointment_by_token(id, token)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Link de confirmação inválido")
    if not can_be_confirmed(appointment):
        raise HTTPException(status_code=409, detail="Esta consulta não pode mais ser confirmada")

    with get_connection() as conexao:
        cursor = conexao.cursor()
        cursor.execute(
            "UPDATE minhaagenda.appointments SET status = 'confirmado', is_checked = TRUE, reason = NULL "
            "WHERE id = %(id)s AND status IN ('pendente', 'confirmado') "
            "RETURNING id",
            {"id": id},
        )
        row = cursor.fetchone()
        cursor.close()

    if row is None:
        raise HTTPException(status_code=409, detail="Esta consulta não pode mais ser confirmada")

    return _get_appointment(id)


def set_appointment_status(id: int, status: str, reason: str | None = None):
    """O motivo só é guardado para ausência e cancelamento; nos outros status ele é limpo."""

    _get_appointment(id)

    params = {
        "id": id,
        "status": status,
        "is_checked": status == "confirmado",
        "reason": reason if status in STATUS_WITH_REASON else None,
    }

    try:
        with get_connection() as conexao:
            cursor = conexao.cursor()
            cursor.execute(
                "UPDATE minhaagenda.appointments "
                "SET status = %(status)s, is_checked = %(is_checked)s, reason = %(reason)s "
                "WHERE id = %(id)s RETURNING id",
                params,
            )
            row = cursor.fetchone()
            cursor.close()
    except UniqueViolation:
        # Reativar uma consulta cancelada cujo horário já foi ocupado por outra
        raise HTTPException(status_code=409, detail=_CONFLICT_DETAIL)

    if row is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    return _get_appointment(id)


def set_appointment_checked(id: int, is_checked: bool):
    """Usado pelo recepcionista quando o paciente responde à mensagem."""

    return set_appointment_status(id, "confirmado" if is_checked else "pendente")
