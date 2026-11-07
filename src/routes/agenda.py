from datetime import date, time

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse

from src.auth import get_current_user
from src.models.agenda import AppointmentCreate, AppointmentResponse, AppointmentStatus, AppointmentUpdate
from src.pages.confirmation import closed_page, confirm_form_page, confirmed_page, invalid_link_page
from src.services.agenda import (
    can_be_confirmed,
    confirm_appointment,
    create_appointment,
    del_appointment,
    get_appointment_by_token,
    list_appointments,
    modify_appointment,
    search_appointment,
    set_appointment_checked,
    set_appointment_status,
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


def _parse_link_id(id: str) -> int | None:
    """Nas páginas do paciente, id inválido vira a página de link inválido em vez de erro 422."""
    if not (id.isascii() and id.isdigit()) or len(id) > 9:
        return None
    return int(id) or None


router = APIRouter(prefix="/appointments", tags=["appointments"])

@router.get("/list", response_model=list[AppointmentResponse], dependencies=[Depends(get_current_user)])
def get_appointments():

    result = list_appointments()
    return result

@router.get("/search", response_model=list[AppointmentResponse], dependencies=[Depends(get_current_user)])
def get_appointment(
    patient_cpf: str | None = None,
    doctor_cpf: str | None = None,
    doctor_name: str | None = None,
    date: date | None = None,
    time: time | None = None,
    status: AppointmentStatus | None = None,
):

    result = search_appointment(
        patient_cpf=patient_cpf, doctor_cpf=doctor_cpf, doctor_name=doctor_name, date=date, time=time, status=status
    )
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

@router.get("/confirm", response_class=HTMLResponse)
def confirm_page(id: str, token: str):
    """Rota pública: página que o paciente abre pelo link do email/WhatsApp, sem login.
    Só mostra a consulta; quem confirma é o botão da página (POST /confirm)."""

    appointment_id = _parse_link_id(id)
    appointment = get_appointment_by_token(appointment_id, token) if appointment_id else None
    if appointment is None:
        return invalid_link_page()
    if not can_be_confirmed(appointment):
        return closed_page(appointment)
    if appointment.status == "confirmado":
        return confirmed_page(appointment)

    return confirm_form_page(appointment, appointment_id, token)

@router.post("/confirm", response_class=HTMLResponse)
def confirm(id: str = Form(...), token: str = Form(...)):
    """Rota pública: recebe o botão "Confirmar presença" da página acima."""

    appointment_id = _parse_link_id(id)
    if appointment_id is None:
        return invalid_link_page()

    try:
        appointment = confirm_appointment(appointment_id, token)
    except HTTPException as e:
        if e.status_code == 409:
            return closed_page(get_appointment_by_token(appointment_id, token))
        return invalid_link_page()

    return confirmed_page(appointment)

@router.put("/check", response_model=AppointmentResponse, dependencies=[Depends(get_current_user)])
def check_appointment(id: str, is_checked: bool = True):
    """O recepcionista marca (ou desmarca) a confirmação depois que o paciente responde à mensagem."""

    result = set_appointment_checked(_parse_id(id), is_checked)
    return result

@router.put("/status", response_model=AppointmentResponse, dependencies=[Depends(get_current_user)])
def update_appointment_status(id: str, status: AppointmentStatus, reason: str | None = None):
    """Muda o status da consulta. O motivo (reason) só é guardado para "ausente" e "cancelado"."""

    result = set_appointment_status(_parse_id(id), status, reason)
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
