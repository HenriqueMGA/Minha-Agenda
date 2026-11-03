from src.services.medicos import del_doctor


def test_list_doctors_requires_login(client):
    r = client.get("/doctors/list")
    assert r.status_code == 401


def test_list_doctors_allowed_for_any_role(client, regular_user):
    r = client.get("/doctors/list", headers=regular_user["headers"])
    assert r.status_code == 200


def test_create_doctor_requires_login(client, valid_cpf):
    r = client.post("/doctors/create", json={
        "name": "Dr", "cpf": valid_cpf(), "email": "d@example.com",
        "tel": "119", "doctor_specialty": "Clinico",
    })
    assert r.status_code == 401


def test_create_doctor_forbidden_for_regular_user(client, regular_user, valid_cpf):
    r = client.post("/doctors/create", headers=regular_user["headers"], json={
        "name": "Dr", "cpf": valid_cpf(), "email": "d@example.com",
        "tel": "119", "doctor_specialty": "Clinico",
    })
    assert r.status_code == 403


def test_create_doctor_allowed_for_admin(client, admin, valid_cpf):
    cpf = valid_cpf()
    r = client.post("/doctors/create", headers=admin["headers"], json={
        "name": "Dr Teste", "cpf": cpf, "email": "dr@example.com",
        "tel": "119", "doctor_specialty": "Clinico",
    })
    assert r.status_code == 200
    assert r.json()["cpf"] == cpf
    del_doctor(cpf)


def test_create_doctor_invalid_cpf(client, admin):
    r = client.post("/doctors/create", headers=admin["headers"], json={
        "name": "Dr", "cpf": "123", "email": "d@example.com",
        "tel": "119", "doctor_specialty": "X",
    })
    assert r.status_code == 422


def test_create_doctor_duplicate_cpf(client, admin, valid_cpf):
    cpf = valid_cpf()
    body = {"name": "D1", "cpf": cpf, "email": "d1@example.com", "tel": "119", "doctor_specialty": "X"}
    r1 = client.post("/doctors/create", headers=admin["headers"], json=body)
    assert r1.status_code == 200

    r2 = client.post("/doctors/create", headers=admin["headers"], json={**body, "email": "d2@example.com"})
    assert r2.status_code == 409

    del_doctor(cpf)


def test_update_doctor(client, admin, valid_cpf):
    cpf = valid_cpf()
    client.post("/doctors/create", headers=admin["headers"], json={
        "name": "D", "cpf": cpf, "email": "d@example.com", "tel": "119", "doctor_specialty": "X",
    })

    r = client.put("/doctors/update", headers=admin["headers"], params={"cpf": cpf}, json={"doctor_specialty": "Y"})
    assert r.status_code == 200
    assert r.json()["cpf"] == cpf

    r = client.get("/doctors/search", headers=admin["headers"], params={"cpf": cpf})
    assert r.json()[0]["doctor_specialty"] == "Y"

    del_doctor(cpf)


def test_update_doctor_forbidden_for_regular_user(client, regular_user, admin, valid_cpf):
    cpf = valid_cpf()
    client.post("/doctors/create", headers=admin["headers"], json={
        "name": "D", "cpf": cpf, "email": "d@example.com", "tel": "119", "doctor_specialty": "X",
    })

    r = client.put("/doctors/update", headers=regular_user["headers"], params={"cpf": cpf}, json={"doctor_specialty": "Z"})
    assert r.status_code == 403

    del_doctor(cpf)


def test_delete_doctor(client, admin, valid_cpf):
    cpf = valid_cpf()
    client.post("/doctors/create", headers=admin["headers"], json={
        "name": "D", "cpf": cpf, "email": "d@example.com", "tel": "119", "doctor_specialty": "X",
    })

    r = client.delete("/doctors/delete", headers=admin["headers"], params={"cpf": cpf})
    assert r.status_code == 200


def test_delete_doctor_forbidden_for_regular_user(client, regular_user, admin, valid_cpf):
    cpf = valid_cpf()
    client.post("/doctors/create", headers=admin["headers"], json={
        "name": "D", "cpf": cpf, "email": "d@example.com", "tel": "119", "doctor_specialty": "X",
    })

    r = client.delete("/doctors/delete", headers=regular_user["headers"], params={"cpf": cpf})
    assert r.status_code == 403

    del_doctor(cpf)


def test_delete_nonexistent_doctor(client, admin, valid_cpf):
    r = client.delete("/doctors/delete", headers=admin["headers"], params={"cpf": valid_cpf()})
    assert r.status_code == 404
