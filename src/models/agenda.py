from datetime import date as Date, time as Time

from pydantic import BaseModel, field_validator

from src.validators import validate_cpf


class AppointmentCreate(BaseModel):
    patient_name: str
    patient_cpf: str
    doctor_name: str
    date: Date
    time: Time

    @field_validator("patient_cpf")
    @classmethod
    def _validate_cpf(cls, v: str) -> str:
        return validate_cpf(v)


class AppointmentUpdate(BaseModel):
    patient_name: str | None = None
    patient_cpf: str | None = None
    doctor_name: str | None = None
    date: Date | None = None
    time: Time | None = None

    @field_validator("patient_cpf")
    @classmethod
    def _validate_cpf(cls, v: str | None) -> str | None:
        return validate_cpf(v) if v is not None else v


class AppointmentResponse(BaseModel):
    id: int
    patient_name: str
    patient_cpf: str
    doctor_name: str
    date: Date
    time: Time
