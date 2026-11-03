from urllib.parse import parse_qs, unquote, urlsplit

from src.services.agenda import del_appointment, get_confirmation_token
from src.services.notifications import _to_whatsapp_number
from src.services.pacientes import del_patient


def _create_appointment_with_patient(client, headers, cpf, doctor_name, date):
    """As mensagens usam o nome, email e telefone do cadastro do paciente, então ele precisa existir."""
    client.post("/patients/create", headers=headers, json={
        "name": "Maria Teste", "cpf": cpf, "email": "maria@example.com",
        "tel": "(11) 98888-7777", "dt_nasc": "1990-01-01",
    })
    r = client.post("/appointments/create", headers=headers, json={
        "patient_name": "Maria Teste", "patient_cpf": cpf, "doctor_name": doctor_name,
        "date": date, "time": "14:00:00",
    })
    return r.json()["id"]


def test_list_appointments_requires_login(client):
    r = client.get("/appointments/list")
    assert r.status_code == 401


def test_list_appointments_allowed_for_any_role(client, regular_user):
    r = client.get("/appointments/list", headers=regular_user["headers"])
    assert r.status_code == 200


def test_create_appointment_requires_login(client, valid_cpf):
    r = client.post("/appointments/create", json={
        "patient_name": "P", "patient_cpf": valid_cpf(), "doctor_name": "Dr X",
        "date": "2027-01-10", "time": "09:00:00",
    })
    assert r.status_code == 401


def test_create_appointment_allowed_for_any_logged_in_user(client, regular_user, valid_cpf):
    r = client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "P", "patient_cpf": valid_cpf(), "doctor_name": "Dr Agenda Teste 1",
        "date": "2027-01-10", "time": "09:00:00",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["id"].isdigit()
    assert len(body["id"]) >= 5

    del_appointment(int(body["id"]))


def test_create_appointment_invalid_cpf(client, regular_user):
    r = client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "P", "patient_cpf": "000", "doctor_name": "Dr X",
        "date": "2027-01-10", "time": "09:00:00",
    })
    assert r.status_code == 422


def test_create_appointment_conflict_same_doctor_datetime(client, regular_user, valid_cpf):
    body = {
        "patient_name": "P1", "patient_cpf": valid_cpf(), "doctor_name": "Dr Agenda Teste 2",
        "date": "2027-02-01", "time": "10:00:00",
    }
    r1 = client.post("/appointments/create", headers=regular_user["headers"], json=body)
    assert r1.status_code == 200
    id1 = r1.json()["id"]

    body2 = {**body, "patient_cpf": valid_cpf(), "patient_name": "P2"}
    r2 = client.post("/appointments/create", headers=regular_user["headers"], json=body2)
    assert r2.status_code == 409

    del_appointment(int(id1))


def test_update_appointment(client, regular_user, valid_cpf):
    r1 = client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "P", "patient_cpf": valid_cpf(), "doctor_name": "Dr Agenda Teste 3",
        "date": "2027-03-01", "time": "08:00:00",
    })
    appt_id = r1.json()["id"]

    r = client.put("/appointments/update", headers=regular_user["headers"],
                    params={"id": appt_id}, json={"time": "09:30:00"})
    assert r.status_code == 200
    assert r.json()["time"] == "09:30:00"

    del_appointment(int(appt_id))


def test_update_appointment_conflict(client, regular_user, valid_cpf):
    client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "P1", "patient_cpf": valid_cpf(), "doctor_name": "Dr Agenda Teste 4",
        "date": "2027-03-05", "time": "08:00:00",
    })
    r2 = client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "P2", "patient_cpf": valid_cpf(), "doctor_name": "Dr Agenda Teste 4",
        "date": "2027-03-05", "time": "09:00:00",
    })
    id2 = r2.json()["id"]

    r = client.put("/appointments/update", headers=regular_user["headers"],
                    params={"id": id2}, json={"time": "08:00:00"})
    assert r.status_code == 409

    del_appointment(int(id2))
    from src.services.agenda import search_appointment
    for a in search_appointment(doctor_name="Dr Agenda Teste 4"):
        del_appointment(int(a.id))


def test_update_appointment_invalid_id_format(client, regular_user):
    r = client.put("/appointments/update", headers=regular_user["headers"],
                    params={"id": "abc"}, json={"time": "09:00:00"})
    assert r.status_code == 422


def test_delete_appointment(client, regular_user, valid_cpf):
    r1 = client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "P", "patient_cpf": valid_cpf(), "doctor_name": "Dr Agenda Teste 5",
        "date": "2027-04-01", "time": "08:00:00",
    })
    appt_id = r1.json()["id"]

    r = client.delete("/appointments/delete", headers=regular_user["headers"], params={"id": appt_id})
    assert r.status_code == 200


def test_delete_nonexistent_appointment(client, regular_user):
    r = client.delete("/appointments/delete", headers=regular_user["headers"], params={"id": "999999"})
    assert r.status_code == 404


def test_appointment_is_checked_defaults_false(client, regular_user, valid_cpf):
    r = client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "P", "patient_cpf": valid_cpf(), "doctor_name": "Dr Agenda Teste 6",
        "date": "2027-05-10", "time": "08:00:00",
    })
    assert r.json()["is_checked"] is False
    del_appointment(int(r.json()["id"]))


def test_confirm_appointment_with_correct_token(client, regular_user, valid_cpf):
    r1 = client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "P", "patient_cpf": valid_cpf(), "doctor_name": "Dr Agenda Teste 7",
        "date": "2027-05-11", "time": "08:00:00",
    })
    appt_id = r1.json()["id"]
    token = get_confirmation_token(int(appt_id))

    r = client.get("/appointments/confirm", params={"id": appt_id, "token": token})
    assert r.status_code == 200
    assert r.json()["is_checked"] is True

    del_appointment(int(appt_id))


def test_confirm_appointment_without_login_required(client, regular_user, valid_cpf):
    """A confirmação é pública -- o paciente clica no link sem precisar de conta."""
    r1 = client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "P", "patient_cpf": valid_cpf(), "doctor_name": "Dr Agenda Teste 8",
        "date": "2027-05-12", "time": "08:00:00",
    })
    appt_id = r1.json()["id"]
    token = get_confirmation_token(int(appt_id))

    r = client.get("/appointments/confirm", params={"id": appt_id, "token": token})
    assert r.status_code == 200

    del_appointment(int(appt_id))


def test_confirm_appointment_wrong_token(client, regular_user, valid_cpf):
    r1 = client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "P", "patient_cpf": valid_cpf(), "doctor_name": "Dr Agenda Teste 9",
        "date": "2027-05-13", "time": "08:00:00",
    })
    appt_id = r1.json()["id"]

    r = client.get("/appointments/confirm", params={"id": appt_id, "token": "token-completamente-errado"})
    assert r.status_code == 404

    del_appointment(int(appt_id))


def test_check_appointment_by_receptionist(client, regular_user, valid_cpf):
    r1 = client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "P", "patient_cpf": valid_cpf(), "doctor_name": "Dr Agenda Teste 10",
        "date": "2027-05-14", "time": "08:00:00",
    })
    appt_id = r1.json()["id"]

    r = client.put("/appointments/check", headers=regular_user["headers"], params={"id": appt_id})
    assert r.status_code == 200
    assert r.json()["is_checked"] is True

    r = client.put("/appointments/check", headers=regular_user["headers"], params={"id": appt_id, "is_checked": False})
    assert r.status_code == 200
    assert r.json()["is_checked"] is False

    del_appointment(int(appt_id))


def test_check_appointment_requires_login(client):
    r = client.put("/appointments/check", params={"id": "00001"})
    assert r.status_code == 401


def test_check_nonexistent_appointment(client, regular_user):
    r = client.put("/appointments/check", headers=regular_user["headers"], params={"id": "999999"})
    assert r.status_code == 404


def test_check_appointment_invalid_id_format(client, regular_user):
    r = client.put("/appointments/check", headers=regular_user["headers"], params={"id": "abc"})
    assert r.status_code == 422


def test_confirm_appointment_invalid_id_format(client):
    r = client.get("/appointments/confirm", params={"id": "abc", "token": "x"})
    assert r.status_code == 422


def test_whatsapp_link_asks_patient_to_reply_by_default(client, regular_user, valid_cpf):
    cpf = valid_cpf()
    appt_id = _create_appointment_with_patient(client, regular_user["headers"], cpf, "Dr Agenda Teste 11", "2027-06-01")

    r = client.get("/appointments/notify/whatsapp-link", headers=regular_user["headers"], params={"id": appt_id})
    assert r.status_code == 200
    body = r.json()
    assert body["channel"] == "whatsapp"
    assert body["to"] == "5511988887777"
    assert body["url"].startswith("https://wa.me/5511988887777?text=")

    text = unquote(body["url"].split("?text=", 1)[1])
    assert "Maria Teste" in text
    assert "Dr Agenda Teste 11" in text
    assert "01/06/2027 às 14:00" in text
    assert "Responda SIM" in text
    assert "/appointments/confirm" not in text
    assert regular_user["email"] in text

    del_appointment(int(appt_id))
    del_patient(cpf)


def test_whatsapp_link_with_link_lets_patient_confirm(client, regular_user, valid_cpf):
    cpf = valid_cpf()
    appt_id = _create_appointment_with_patient(client, regular_user["headers"], cpf, "Dr Agenda Teste 12", "2027-06-02")
    token = get_confirmation_token(int(appt_id))

    r = client.get("/appointments/notify/whatsapp-link", headers=regular_user["headers"],
                   params={"id": appt_id, "with_link": True})
    assert r.status_code == 200
    text = unquote(r.json()["url"].split("?text=", 1)[1])
    assert "Responda SIM" not in text
    assert f"/appointments/confirm?id={int(appt_id)}&token={token}" in text

    # O link que vai na mensagem funciona de verdade, sem login.
    confirm_path = text[text.index("/appointments/confirm"):].split()[0]
    r = client.get(confirm_path)
    assert r.status_code == 200
    assert r.json()["is_checked"] is True

    del_appointment(int(appt_id))
    del_patient(cpf)


def test_email_link_asks_patient_to_reply_by_default(client, regular_user, valid_cpf):
    cpf = valid_cpf()
    appt_id = _create_appointment_with_patient(client, regular_user["headers"], cpf, "Dr Agenda Teste 13", "2027-06-03")

    r = client.get("/appointments/notify/email-link", headers=regular_user["headers"], params={"id": appt_id})
    assert r.status_code == 200
    body = r.json()
    assert body["channel"] == "email"
    assert body["to"] == "maria@example.com"

    url = urlsplit(body["url"])
    assert url.scheme == "mailto"
    assert url.path == "maria@example.com"
    query = parse_qs(url.query)
    assert query["subject"] == ["Confirme sua consulta"]
    assert "Responda SIM" in query["body"][0]
    assert "03/06/2027 às 14:00" in query["body"][0]

    del_appointment(int(appt_id))
    del_patient(cpf)


def test_email_link_with_link_includes_confirmation(client, regular_user, valid_cpf):
    cpf = valid_cpf()
    appt_id = _create_appointment_with_patient(client, regular_user["headers"], cpf, "Dr Agenda Teste 14", "2027-06-04")
    token = get_confirmation_token(int(appt_id))

    r = client.get("/appointments/notify/email-link", headers=regular_user["headers"],
                   params={"id": appt_id, "with_link": True})
    assert r.status_code == 200
    message = parse_qs(urlsplit(r.json()["url"]).query)["body"][0]
    assert f"/appointments/confirm?id={int(appt_id)}&token={token}" in message

    del_appointment(int(appt_id))
    del_patient(cpf)


def test_notify_link_patient_not_registered(client, regular_user, valid_cpf):
    r1 = client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "Sem Cadastro", "patient_cpf": valid_cpf(), "doctor_name": "Dr Agenda Teste 15",
        "date": "2027-06-05", "time": "14:00:00",
    })
    appt_id = r1.json()["id"]

    r = client.get("/appointments/notify/whatsapp-link", headers=regular_user["headers"], params={"id": appt_id})
    assert r.status_code == 404
    assert "Paciente" in r.json()["detail"]

    del_appointment(int(appt_id))


def test_to_whatsapp_number_formats():
    assert _to_whatsapp_number("(11) 98888-7777") == "+5511988887777"
    assert _to_whatsapp_number("1133334444") == "+551133334444"
    assert _to_whatsapp_number("+55 11 98888-7777") == "+5511988887777"
    # DDD 55 (RS) não pode ser confundido com o código do país.
    assert _to_whatsapp_number("55 98888-7777") == "+5555988887777"


def test_notify_whatsapp_link_requires_login(client):
    r = client.get("/appointments/notify/whatsapp-link", params={"id": "00001"})
    assert r.status_code == 401


def test_notify_email_link_requires_login(client):
    r = client.get("/appointments/notify/email-link", params={"id": "00001"})
    assert r.status_code == 401


def test_notify_whatsapp_link_nonexistent_appointment(client, regular_user):
    r = client.get("/appointments/notify/whatsapp-link", headers=regular_user["headers"], params={"id": "999999"})
    assert r.status_code == 404


def test_notify_email_link_nonexistent_appointment(client, regular_user):
    r = client.get("/appointments/notify/email-link", headers=regular_user["headers"], params={"id": "999999"})
    assert r.status_code == 404
