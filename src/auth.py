import os
from datetime import datetime, timedelta, timezone

import jwt
from argon2.exceptions import VerifyMismatchError
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from src.services.users import get_user_credentials, password_hasher

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def authenticate_user(email: str, password: str):
    credenciais = get_user_credentials(email)
    if credenciais is None:
        return None

    _, senha_hash, tipo = credenciais
    try:
        password_hasher.verify(senha_hash, password)
    except VerifyMismatchError:
        return None

    return {"email": email, "tipo": tipo}


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        tipo = payload.get("tipo")
        if email is None:
            raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception

    return {"email": email, "tipo": tipo}


def require_roles(*roles: str):
    permitidos = {r.lower() for r in roles}

    def checker(current_user: dict = Depends(get_current_user)):
        tipo = (current_user.get("tipo") or "").lower()
        if tipo not in permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para acessar este recurso",
            )
        return current_user

    return checker


def require_self_or_roles(*roles: str):
    """Libera se o usuário logado tiver um dos `roles`, ou se `email` (da rota) for o próprio email logado."""
    permitidos = {r.lower() for r in roles}

    def checker(email: str, current_user: dict = Depends(get_current_user)):
        tipo = (current_user.get("tipo") or "").lower()
        if tipo in permitidos:
            return current_user
        if current_user.get("email") != email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você só pode alterar o próprio perfil",
            )
        return current_user

    return checker
