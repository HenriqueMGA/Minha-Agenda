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
        "https://minha-agenda-frontend-eight.vercel.app",
        # Páginas abertas direto do arquivo (file://) enviam Origin "null"
        "null",
    ],
    # Qualquer porta em localhost/127.0.0.1 (Vite, Live Server, etc.)
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(pacientes.router)
app.include_router(medicos.router)
app.include_router(agenda.router)
