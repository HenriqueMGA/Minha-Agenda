def test_login_success(client, regular_user):
    r = client.post("/auth/token", data={
        "username": regular_user["email"],
        "password": regular_user["password"],
    })
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password(client, regular_user):
    r = client.post("/auth/token", data={
        "username": regular_user["email"],
        "password": "senha_errada",
    })
    assert r.status_code == 401


def test_login_nonexistent_user(client, unique_email):
    r = client.post("/auth/token", data={
        "username": unique_email(),
        "password": "qualquer",
    })
    assert r.status_code == 401


def test_protected_route_without_token(client):
    r = client.get("/users/list")
    assert r.status_code == 401


def test_protected_route_with_garbage_token(client):
    r = client.get("/users/list", headers={"Authorization": "Bearer token.invalido.aqui"})
    assert r.status_code == 401
