from fastapi import APIRouter, Depends

from src.auth import require_roles
from src.models.medicos import DoctorCreate, DoctorResponse, DoctorUpdate
from src.services.medicos import create_doctor, del_doctor, list_doctors, modify_doctor, search_doctor


router = APIRouter(prefix="/doctors", tags=["doctors"])

@router.get("/list", response_model=list[DoctorResponse])
def get_doctors():

    result = list_doctors()
    return result

@router.get("/search", response_model=list[DoctorResponse])
def get_doctor(name: str | None = None, email: str | None = None, cpf: str | None = None):

    result = search_doctor(name=name, email=email, cpf=cpf)
    return result

@router.post("/create", dependencies=[Depends(require_roles("admin", "dev"))])
def post_doctor(body: DoctorCreate):

    result = create_doctor(body)
    return result

@router.delete("/delete", dependencies=[Depends(require_roles("admin", "dev"))])
def delete_doctor(cpf: str):

    result = del_doctor(cpf)
    return result

@router.put("/update", dependencies=[Depends(require_roles("admin", "dev"))])
def update_doctor(cpf: str, body: DoctorUpdate):

    result = modify_doctor(cpf, body)
    return result
