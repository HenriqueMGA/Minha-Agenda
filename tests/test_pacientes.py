from src.services.pacientes import del_patient


def test_list_patients_requires_login(client):
    r = client.get("/patients/list")
    assert r.status_code == 401


def test_list_patients_allowed_for_any_role(client, regular_user):
    r = client.get("/patients/list", headers=regular_user["headers"])
    assert r.status_code == 200


def test_create_patient_requires_login(client, valid_cpf):
    r = client.post("/patients/create", json={
        "name": "P", "cpf": valid_cpf(), "email": "p@example.com",
        "tel": "11999998888", "dt_nasc": "1990-01-01",
    })
    assert r.status_code == 401


def test_create_patient_allowed_for_any_logged_in_user(client, regular_user, valid_cpf):
    cpf = valid_cpf()
    r = client.post("/patients/create", headers=regular_user["headers"], json={
        "name": "Paciente Teste", "cpf": cpf, "email": "paciente@example.com",
        "tel": "11999998888", "dt_nasc": "1990-01-01",
    })
    assert r.status_code == 200
    assert r.json()["cpf"] == cpf
    del_patient(cpf)


def test_create_patient_invalid_cpf(client, regular_user):
    r = client.post("/patients/create", headers=regular_user["headers"], json={
        "name": "P", "cpf": "11111111111", "email": "p@example.com",
        "tel": "119", "dt_nasc": "1990-01-01",
    })
    assert r.status_code == 422


def test_create_patient_duplicate_cpf(client, regular_user, valid_cpf):
    cpf = valid_cpf()
    body = {"name": "P1", "cpf": cpf, "email": "p1@example.com", "tel": "119", "dt_nasc": "1990-01-01"}
    r1 = client.post("/patients/create", headers=regular_user["headers"], json=body)
    assert r1.status_code == 200

    body2 = {**body, "name": "P2", "email": "p2@example.com"}
    r2 = client.post("/patients/create", headers=regular_user["headers"], json=body2)
    assert r2.status_code == 409

    del_patient(cpf)


def test_update_patient(client, regular_user, valid_cpf):
    cpf = valid_cpf()
    client.post("/patients/create", headers=regular_user["headers"], json={
        "name": "P", "cpf": cpf, "email": "p@example.com", "tel": "119", "dt_nasc": "1990-01-01",
    })

    r = client.put("/patients/update", headers=regular_user["headers"],
                    params={"cpf": cpf}, json={"tel": "11988887777"})
    assert r.status_code == 200
    assert r.json()["cpf"] == cpf

    r = client.get("/patients/search", headers=regular_user["headers"], params={"cpf": cpf})
    assert r.json()[0]["tel"] == "11988887777"

    del_patient(cpf)


def test_delete_patient(client, regular_user, valid_cpf):
    cpf = valid_cpf()
    client.post("/patients/create", headers=regular_user["headers"], json={
        "name": "P", "cpf": cpf, "email": "p@example.com", "tel": "119", "dt_nasc": "1990-01-01",
    })

    r = client.delete("/patients/delete", headers=regular_user["headers"], params={"cpf": cpf})
    assert r.status_code == 200


def test_delete_nonexistent_patient(client, regular_user, valid_cpf):
    r = client.delete("/patients/delete", headers=regular_user["headers"], params={"cpf": valid_cpf()})
    assert r.status_code == 404
