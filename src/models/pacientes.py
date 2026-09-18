from datetime import date

from pydantic import BaseModel, field_validator

from src.validators import validate_cpf


class PatientCreate(BaseModel):
    name: str
    cpf: str
    email: str
    tel: str
    dt_nasc: date

    @field_validator("cpf")
    @classmethod
    def _validate_cpf(cls, v: str) -> str:
        return validate_cpf(v)


class PatientUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    tel: str | None = None
    dt_nasc: date | None = None
    cpf: str | None = None

    @field_validator("cpf")
    @classmethod
    def _validate_cpf(cls, v: str | None) -> str | None:
        return validate_cpf(v) if v is not None else v


class PatientResponse(BaseModel):
    cpf: str
    name: str
    email: str
    tel: str
    dt_nasc: date
