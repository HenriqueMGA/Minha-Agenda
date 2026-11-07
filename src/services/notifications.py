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
REMINDER_INSTRUCTION = "Caso não possa comparecer, avise respondendo esta mensagem."

CONFIRMATION_SUBJECT = "Confirme sua consulta"
REMINDER_SUBJECT = "Lembrete da sua consulta"


def _message(id: int, appointment, patient, sender_name: str, sender_email: str, with_link: bool) -> dict:
    """Escolhe o modelo pelo status: pendente pede confirmação, confirmado recebe lembrete.

    Sem link, o paciente responde a mensagem e o recepcionista marca a confirmação no sistema.
    O lembrete nunca leva o link, porque a consulta já está confirmada.
    """
    quando = f"no dia {appointment.date.strftime('%d/%m/%Y')} às {appointment.time.strftime('%H:%M')}"
    assinatura = f"Atendimento: {sender_name} ({sender_email})"

    if appointment.status == "pendente":
        link = _confirmation_link(id) if with_link else None
        action = f"Confirme sua presença: {link}" if link else REPLY_INSTRUCTION
        text = (
            f"Olá, {patient.name}! Você tem uma consulta marcada com {appointment.doctor_name} {quando}. "
            f"{action}\n{assinatura}"
        )
        return {"template": "confirmacao", "subject": CONFIRMATION_SUBJECT, "text": text, "link": link}

    if appointment.status == "confirmado":
        text = (
            f"Olá, {patient.name}! Lembrete: sua consulta com {appointment.doctor_name} é {quando}. "
            f"{REMINDER_INSTRUCTION}\n{assinatura}"
        )
        return {"template": "lembrete", "subject": REMINDER_SUBJECT, "text": text, "link": None}

    raise HTTPException(
        status_code=409,
        detail=f"Não há mensagem para enviar: a consulta está com status \"{appointment.status}\"",
    )


def appointment_confirmation_whatsapp_link(id: int, sender_email: str, with_link: bool = False):
    """Monta um link wa.me com a mensagem pronta; quem envia é o atendente, pelo próprio WhatsApp."""
    appointment, patient = _get_appointment_and_patient(id)
    message = _message(id, appointment, patient, _sender_username(sender_email), sender_email, with_link)
    to_phone = _to_whatsapp_number(patient.tel).lstrip("+")

    return {
        "channel": "whatsapp",
        "template": message["template"],
        "to": to_phone,
        "url": f"https://wa.me/{to_phone}?text={quote(message['text'])}",
    }


def appointment_confirmation_email_link(id: int, sender_email: str, with_link: bool = False):
    """Monta um link mailto: com assunto e corpo prontos; abre o cliente de email do atendente."""
    appointment, patient = _get_appointment_and_patient(id)
    message = _message(id, appointment, patient, _sender_username(sender_email), sender_email, with_link)
    query = urlencode({"subject": message["subject"], "body": message["text"]}, quote_via=quote)

    return {
        "channel": "email",
        "template": message["template"],
        "to": patient.email,
        "url": f"mailto:{patient.email}?{query}",
    }
