from datetime import date, time

from fastapi import APIRouter, Depends

from src.auth import get_current_user
from src.models.agenda import AppointmentCreate, AppointmentResponse, AppointmentUpdate
from src.services.agenda import create_appointment, del_appointment, list_appointments, modify_appointment, search_appointment


router = APIRouter(prefix="/appointments", tags=["appointments"])

@router.get("/list", response_model=list[AppointmentResponse])
def get_appointments():

    result = list_appointments()
    return result

@router.get("/search", response_model=list[AppointmentResponse])
def get_appointment(patient_cpf: str | None = None, doctor_name: str | None = None, date: date | None = None, time: time | None = None):

    result = search_appointment(patient_cpf=patient_cpf, doctor_name=doctor_name, date=date, time=time)
    return result

@router.post("/create", response_model=AppointmentResponse, dependencies=[Depends(get_current_user)])
def post_appointment(body: AppointmentCreate):

    result = create_appointment(body)
    return result

@router.delete("/delete", response_model=AppointmentResponse, dependencies=[Depends(get_current_user)])
def delete_appointment(id: int):

    result = del_appointment(id)
    return result

@router.put("/update", response_model=AppointmentResponse, dependencies=[Depends(get_current_user)])
def update_appointment(id: int, body: AppointmentUpdate):

    result = modify_appointment(id, body)
    return result
