from datetime import date as Date, time as Time
from typing import Literal

from pydantic import BaseModel, field_validator, model_validator

from src.validators import validate_cpf

AppointmentStatus = Literal["pendente", "confirmado", "concluido", "ausente", "cancelado"]

# Status em que faz sentido guardar um motivo
STATUS_WITH_REASON = ("ausente", "cancelado")


class AppointmentCreate(BaseModel):
    patient_name: str
    patient_cpf: str
    # Informe doctor_cpf. doctor_name ainda é aceito para não quebrar o front antigo.
    doctor_cpf: str | None = None
    doctor_name: str | None = None
    date: Date
    time: Time

    @field_validator("patient_cpf", "doctor_cpf")
    @classmethod
    def _validate_cpf(cls, v: str | None) -> str | None:
        return validate_cpf(v) if v is not None else v

    @model_validator(mode="after")
    def _require_doctor(self):
        if self.doctor_cpf is None and self.doctor_name is None:
            raise ValueError("Informe doctor_cpf (ou doctor_name)")
        return self


class AppointmentUpdate(BaseModel):
    patient_name: str | None = None
    patient_cpf: str | None = None
    doctor_cpf: str | None = None
    doctor_name: str | None = None
    date: Date | None = None
    time: Time | None = None

    @field_validator("patient_cpf", "doctor_cpf")
    @classmethod
    def _validate_cpf(cls, v: str | None) -> str | None:
        return validate_cpf(v) if v is not None else v


class AppointmentResponse(BaseModel):
    id: str
    patient_name: str
    patient_cpf: str
    doctor_cpf: str | None
    doctor_name: str
    date: Date
    time: Time
    status: AppointmentStatus
    reason: str | None
    # Mantido para compatibilidade: é True quando status == "confirmado"
    is_checked: bool
