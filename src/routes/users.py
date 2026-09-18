
from fastapi import APIRouter, Depends, HTTPException
from src.auth import require_roles, require_self_or_roles
from src.models.users import UserCreate, UserResponse, UserUpdate
from src.services.users import create_user, del_user, list_users, modify_user, search_user


router = APIRouter(prefix="/users", tags=["users"])

@router.get("/list", response_model=list[UserResponse])
def get_users():

    result = list_users()
    return result

@router.get("/search", response_model=list[UserResponse])
def get_user(name: str | None = None, email: str | None = None, username: str | None = None, type: str | None = None):

    result = search_user(name=name, email=email, username=username, type=type)
    return result

@router.post("/create", dependencies=[Depends(require_roles("admin", "dev"))])
def post_user(body: UserCreate):

    result = create_user(body)
    return result

@router.delete("/delete")
def delete_user(email: str, current_user: dict = Depends(require_self_or_roles("admin", "dev"))):

    result = del_user(email)
    return result

@router.put("/update")
def update_user(email: str, body: UserUpdate, current_user: dict = Depends(require_self_or_roles("admin", "dev"))):

    tipo_atual = (current_user.get("tipo") or "").lower()
    if tipo_atual not in {"admin", "dev"} and body.type is not None:
        raise HTTPException(status_code=403, detail="Você não pode alterar seu próprio tipo de usuário")

    result = modify_user(email, body)
    return result