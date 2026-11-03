from datetime import date, time

from fastapi import APIRouter, Depends, HTTPException

from src.auth import get_current_user
from src.models.agenda import AppointmentCreate, AppointmentResponse, AppointmentUpdate
from src.services.agenda import (
    confirm_appointment,
    create_appointment,
    del_appointment,
    list_appointments,
    modify_appointment,
    search_appointment,
    set_appointment_checked,
)
from src.services.notifications import (
    appointment_confirmation_email_link,
    appointment_confirmation_whatsapp_link,
)


def _parse_id(id: str) -> int:
    try:
        return int(id)
    except ValueError:
        raise HTTPException(status_code=422, detail="id inválido")


router = APIRouter(prefix="/appointments", tags=["appointments"])

@router.get("/list", response_model=list[AppointmentResponse], dependencies=[Depends(get_current_user)])
def get_appointments():

    result = list_appointments()
    return result

@router.get("/search", response_model=list[AppointmentResponse], dependencies=[Depends(get_current_user)])
def get_appointment(patient_cpf: str | None = None, doctor_name: str | None = None, date: date | None = None, time: time | None = None):

    result = search_appointment(patient_cpf=patient_cpf, doctor_name=doctor_name, date=date, time=time)
    return result

@router.post("/create", response_model=AppointmentResponse, dependencies=[Depends(get_current_user)])
def post_appointment(body: AppointmentCreate):

    result = create_appointment(body)
    return result

@router.delete("/delete", response_model=AppointmentResponse, dependencies=[Depends(get_current_user)])
def delete_appointment(id: str):

    result = del_appointment(_parse_id(id))
    return result

@router.put("/update", response_model=AppointmentResponse, dependencies=[Depends(get_current_user)])
def update_appointment(id: str, body: AppointmentUpdate):

    result = modify_appointment(_parse_id(id), body)
    return result

@router.get("/confirm", response_model=AppointmentResponse)
def confirm(id: str, token: str):
    """Rota pública: o paciente chega aqui pelo link do email/WhatsApp, sem login."""

    result = confirm_appointment(_parse_id(id), token)
    return result

@router.put("/check", response_model=AppointmentResponse, dependencies=[Depends(get_current_user)])
def check_appointment(id: str, is_checked: bool = True):
    """O recepcionista marca (ou desmarca) a confirmação depois que o paciente responde à mensagem."""

    result = set_appointment_checked(_parse_id(id), is_checked)
    return result

# with_link=true inclui o link de /confirm, para o próprio paciente confirmar sem depender do recepcionista.

@router.get("/notify/whatsapp-link")
def notify_whatsapp_link(id: str, with_link: bool = False, current_user: dict = Depends(get_current_user)):
    """Devolve um link wa.me com a mensagem pronta; o front abre e o atendente só aperta enviar."""

    result = appointment_confirmation_whatsapp_link(_parse_id(id), current_user["email"], with_link)
    return result

@router.get("/notify/email-link")
def notify_email_link(id: str, with_link: bool = False, current_user: dict = Depends(get_current_user)):
    """Devolve um link mailto: com assunto e corpo prontos."""

    result = appointment_confirmation_email_link(_parse_id(id), current_user["email"], with_link)
    return result
