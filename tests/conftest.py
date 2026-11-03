import random
import uuid

import pytest
from fastapi.testclient import TestClient

from src.app import app
from src.models.users import UserCreate
from src.services.users import create_user, del_user


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def unique_email():
    def _make(prefix="test"):
        return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"
    return _make


@pytest.fixture
def unique_username():
    def _make(prefix="test"):
        return f"{prefix}{uuid.uuid4().hex[:10]}"
    return _make


def _check_digit(digits: str) -> int:
    peso = len(digits) + 1
    soma = sum(int(d) * (peso - i) for i, d in enumerate(digits))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


@pytest.fixture
def valid_cpf():
    """Gera um CPF novo e com dígito verificador válido a cada chamada."""
    def _make():
        base = "".join(str(random.randint(0, 9)) for _ in range(9))
        while len(set(base)) == 1:
            base = "".join(str(random.randint(0, 9)) for _ in range(9))
        d1 = _check_digit(base)
        d2 = _check_digit(base + str(d1))
        return f"{base}{d1}{d2}"
    return _make


@pytest.fixture
def make_user(client, unique_email, unique_username):
    """Factory: cria um usuário (direto pela camada de serviço, contornando a
    exigência de admin/dev na rota) e devolve dados de login + token real."""
    created = []

    def _make(type_="user", password="senha123"):
        email = unique_email()
        create_user(UserCreate(
            name="Usuario Teste",
            username=unique_username(),
            password=password,
            email=email,
            type=type_,
        ))
        created.append(email)

        r = client.post("/auth/token", data={"username": email, "password": password})
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]

        return {
            "email": email,
            "password": password,
            "token": token,
            "headers": {"Authorization": f"Bearer {token}"},
        }

    yield _make

    for email in created:
        try:
            del_user(email)
        except Exception:
            pass


@pytest.fixture
def admin(make_user):
    return make_user("admin")


@pytest.fixture
def dev(make_user):
    return make_user("dev")


@pytest.fixture
def regular_user(make_user):
    return make_user("user")
