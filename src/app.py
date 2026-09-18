from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.db.db_conection import close_pool
from src.routes import agenda, auth, medicos, pacientes, users
from src.services.agenda import create_appointments_table
from src.services.medicos import create_doctors_table
from src.services.pacientes import create_patients_table
from src.services.users import create_users_table


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_users_table()
    create_patients_table()
    create_doctors_table()
    create_appointments_table()
    yield
    close_pool()


app = FastAPI(
    title="API MinhaAgenda",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(pacientes.router)
app.include_router(medicos.router)
app.include_router(agenda.router)