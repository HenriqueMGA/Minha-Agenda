from fastapi import APIRouter, Depends

from src.auth import get_current_user
from src.models.pacientes import PatientCreate, PatientResponse, PatientUpdate
from src.services.pacientes import create_patient, del_patient, list_patients, modify_patient, search_patient


router = APIRouter(prefix="/patients", tags=["patients"])

@router.get("/list", response_model=list[PatientResponse])
def get_patients():

    result = list_patients()
    return result

@router.get("/search", response_model=list[PatientResponse])
def get_patient(name: str | None = None, email: str | None = None, cpf: str | None = None):

    result = search_patient(name=name, email=email, cpf=cpf)
    return result

@router.post("/create", dependencies=[Depends(get_current_user)])
def post_patient(body: PatientCreate):

    result = create_patient(body)
    return result

@router.delete("/delete", dependencies=[Depends(get_current_user)])
def delete_patient(cpf: str):

    result = del_patient(cpf)
    return result

@router.put("/update", dependencies=[Depends(get_current_user)])
def update_patient(cpf: str, body: PatientUpdate):

    result = modify_patient(cpf, body)
    return result
