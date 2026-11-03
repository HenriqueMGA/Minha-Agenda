from src.services.users import del_user


def test_create_user_requires_login(client, unique_email, unique_username):
    r = client.post("/users/create", json={
        "name": "X", "username": unique_username(), "password": "x",
        "email": unique_email(), "type": "user",
    })
    assert r.status_code == 401


def test_create_user_forbidden_for_regular_user(client, regular_user, unique_email, unique_username):
    r = client.post("/users/create", headers=regular_user["headers"], json={
        "name": "X", "username": unique_username(), "password": "x",
        "email": unique_email(), "type": "user",
    })
    assert r.status_code == 403


def test_create_user_allowed_for_admin(client, admin, unique_email, unique_username):
    email = unique_email()
    r = client.post("/users/create", headers=admin["headers"], json={
        "name": "Novo", "username": unique_username(), "password": "senha123",
        "email": email, "type": "user",
    })
    assert r.status_code == 200
    assert r.json()["email"] == email
    del_user(email)


def test_create_user_duplicate_email(client, admin, regular_user, unique_username):
    r = client.post("/users/create", headers=admin["headers"], json={
        "name": "Dup", "username": unique_username(), "password": "x",
        "email": regular_user["email"], "type": "user",
    })
    assert r.status_code == 409


def test_list_users_requires_login(client):
    r = client.get("/users/list")
    assert r.status_code == 401


def test_list_users_allowed_for_any_role(client, regular_user):
    r = client.get("/users/list", headers=regular_user["headers"])
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_search_user_by_email(client, regular_user):
    r = client.get("/users/search", headers=regular_user["headers"], params={"email": regular_user["email"]})
    assert r.status_code == 200
    results = r.json()
    assert len(results) == 1
    assert results[0]["email"] == regular_user["email"]
    assert "senha" not in results[0]


def test_update_own_profile(client, regular_user):
    r = client.put("/users/update", headers=regular_user["headers"],
                    params={"email": regular_user["email"]}, json={"name": "Nome Editado"})
    assert r.status_code == 200


def test_update_own_profile_cannot_change_type(client, regular_user):
    r = client.put("/users/update", headers=regular_user["headers"],
                    params={"email": regular_user["email"]}, json={"type": "admin"})
    assert r.status_code == 403


def test_update_other_profile_forbidden_for_regular_user(client, regular_user, admin):
    r = client.put("/users/update", headers=regular_user["headers"],
                    params={"email": admin["email"]}, json={"name": "Hack"})
    assert r.status_code == 403


def test_update_other_profile_allowed_for_admin(client, admin, regular_user):
    r = client.put("/users/update", headers=admin["headers"],
                    params={"email": regular_user["email"]}, json={"type": "dev"})
    assert r.status_code == 200


def test_update_nonexistent_user(client, admin, unique_email):
    r = client.put("/users/update", headers=admin["headers"],
                    params={"email": unique_email()}, json={"name": "X"})
    assert r.status_code == 404


def test_delete_own_profile(client, make_user):
    u = make_user("user")
    r = client.delete("/users/delete", headers=u["headers"], params={"email": u["email"]})
    assert r.status_code == 200


def test_delete_other_profile_forbidden_for_regular_user(client, regular_user, admin):
    r = client.delete("/users/delete", headers=regular_user["headers"], params={"email": admin["email"]})
    assert r.status_code == 403


def test_delete_nonexistent_user(client, admin, unique_email):
    r = client.delete("/users/delete", headers=admin["headers"], params={"email": unique_email()})
    assert r.status_code == 404
