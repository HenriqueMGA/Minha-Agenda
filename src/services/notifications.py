import os
from urllib.parse import quote, urlencode

from dotenv import load_dotenv
from fastapi import HTTPException

from src.services.agenda import get_confirmation_token, search_appointment
from src.services.pacientes import search_patient
from src.services.users import search_user

load_dotenv()

APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")


def _get_appointment_and_patient(id: int):
    appointments = search_appointment(id=id)
    if not appointments:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    appointment = appointments[0]

    patients = search_patient(cpf=appointment.patient_cpf)
    if not patients:
        raise HTTPException(status_code=404, detail="Paciente do agendamento não encontrado no cadastro")
    patient = patients[0]

    return appointment, patient


def _confirmation_link(id: int) -> str:
    token = get_confirmation_token(id)
    return f"{APP_BASE_URL}/appointments/confirm?id={id}&token={token}"


def _to_whatsapp_number(tel: str) -> str:
    digits = "".join(c for c in tel if c.isdigit())
    # DDD + número tem 10 ou 11 dígitos; só olhar o "55" do começo confundiria com o DDD 55 (RS).
    if len(digits) <= 11:
        digits = "55" + digits
    return f"+{digits}"


def _sender_username(sender_email: str) -> str:
    encontrados = search_user(email=sender_email)
    return encontrados[0].username if encontrados else sender_email


REPLY_INSTRUCTION = "Responda SIM para confirmar sua presença ou NÃO caso não possa comparecer."


def _confirmation_text(appointment, patient, link: str | None, sender_name: str, sender_email: str) -> str:
    """Sem link, o paciente responde a mensagem e o recepcionista marca a confirmação no sistema."""
    action = f"Confirme sua presença: {link}" if link else REPLY_INSTRUCTION
    return (
        f"Olá, {patient.name}! Você tem uma consulta marcada com {appointment.doctor_name} "
        f"no dia {appointment.date.strftime('%d/%m/%Y')} às {appointment.time.strftime('%H:%M')}. "
        f"{action}\n"
        f"Atendimento: {sender_name} ({sender_email})"
    )


def appointment_confirmation_whatsapp_link(id: int, sender_email: str, with_link: bool = False):
    """Monta um link wa.me com a mensagem pronta; quem envia é o atendente, pelo próprio WhatsApp."""
    appointment, patient = _get_appointment_and_patient(id)
    link = _confirmation_link(id) if with_link else None
    message = _confirmation_text(appointment, patient, link, _sender_username(sender_email), sender_email)
    to_phone = _to_whatsapp_number(patient.tel).lstrip("+")

    return {"channel": "whatsapp", "to": to_phone, "url": f"https://wa.me/{to_phone}?text={quote(message)}"}


def appointment_confirmation_email_link(id: int, sender_email: str, with_link: bool = False):
    """Monta um link mailto: com assunto e corpo prontos; abre o cliente de email do atendente."""
    appointment, patient = _get_appointment_and_patient(id)
    link = _confirmation_link(id) if with_link else None
    body = _confirmation_text(appointment, patient, link, _sender_username(sender_email), sender_email)
    query = urlencode({"subject": "Confirme sua consulta", "body": body}, quote_via=quote)

    return {"channel": "email", "to": patient.email, "url": f"mailto:{patient.email}?{query}"}
