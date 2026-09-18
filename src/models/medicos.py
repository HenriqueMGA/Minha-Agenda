from pydantic import BaseModel, field_validator

from src.validators import validate_cpf


class DoctorCreate(BaseModel):
    name: str
    cpf: str
    email: str
    tel: str
    doctor_specialty: str

    @field_validator("cpf")
    @classmethod
    def _validate_cpf(cls, v: str) -> str:
        return validate_cpf(v)


class DoctorUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    tel: str | None = None
    doctor_specialty: str | None = None
    cpf: str | None = None

    @field_validator("cpf")
    @classmethod
    def _validate_cpf(cls, v: str | None) -> str | None:
        return validate_cpf(v) if v is not None else v


class DoctorResponse(BaseModel):
    cpf: str
    name: str
    email: str
    tel: str
    doctor_specialty: str
