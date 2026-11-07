from urllib.parse import parse_qs, unquote, urlsplit

from src.services.agenda import del_appointment, get_confirmation_token
from src.services.notifications import _to_whatsapp_number
from src.services.medicos import del_doctor
from src.services.pacientes import del_patient


def _create_appointment_with_patient(client, headers, cpf, doctor_cpf, date):
    """As mensagens usam o nome, email e telefone do cadastro do paciente, então ele precisa existir."""
    client.post("/patients/create", headers=headers, json={
        "name": "Maria Teste", "cpf": cpf, "email": "maria@example.com",
        "tel": "(11) 98888-7777", "dt_nasc": "1990-01-01",
    })
    r = client.post("/appointments/create", headers=headers, json={
        "patient_name": "Maria Teste", "patient_cpf": cpf, "doctor_cpf": doctor_cpf,
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


def test_create_appointment_allowed_for_any_logged_in_user(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Agenda Teste 1")
    r = client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "P", "patient_cpf": valid_cpf(), "doctor_cpf": doctor_cpf,
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


def test_create_appointment_conflict_same_doctor_datetime(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Agenda Teste 2")
    body = {
        "patient_name": "P1", "patient_cpf": valid_cpf(), "doctor_cpf": doctor_cpf,
        "date": "2027-02-01", "time": "10:00:00",
    }
    r1 = client.post("/appointments/create", headers=regular_user["headers"], json=body)
    assert r1.status_code == 200
    id1 = r1.json()["id"]

    body2 = {**body, "patient_cpf": valid_cpf(), "patient_name": "P2"}
    r2 = client.post("/appointments/create", headers=regular_user["headers"], json=body2)
    assert r2.status_code == 409

    del_appointment(int(id1))


def test_update_appointment(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Agenda Teste 3")
    r1 = client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "P", "patient_cpf": valid_cpf(), "doctor_cpf": doctor_cpf,
        "date": "2027-03-01", "time": "08:00:00",
    })
    appt_id = r1.json()["id"]

    r = client.put("/appointments/update", headers=regular_user["headers"],
                    params={"id": appt_id}, json={"time": "09:30:00"})
    assert r.status_code == 200
    assert r.json()["time"] == "09:30:00"

    del_appointment(int(appt_id))


def test_update_appointment_conflict(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Agenda Teste 4")
    client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "P1", "patient_cpf": valid_cpf(), "doctor_cpf": doctor_cpf,
        "date": "2027-03-05", "time": "08:00:00",
    })
    r2 = client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "P2", "patient_cpf": valid_cpf(), "doctor_cpf": doctor_cpf,
        "date": "2027-03-05", "time": "09:00:00",
    })
    id2 = r2.json()["id"]

    r = client.put("/appointments/update", headers=regular_user["headers"],
                    params={"id": id2}, json={"time": "08:00:00"})
    assert r.status_code == 409

    del_appointment(int(id2))


def test_update_appointment_invalid_id_format(client, regular_user):
    r = client.put("/appointments/update", headers=regular_user["headers"],
                    params={"id": "abc"}, json={"time": "09:00:00"})
    assert r.status_code == 422


def test_delete_appointment(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Agenda Teste 5")
    r1 = client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "P", "patient_cpf": valid_cpf(), "doctor_cpf": doctor_cpf,
        "date": "2027-04-01", "time": "08:00:00",
    })
    appt_id = r1.json()["id"]

    r = client.delete("/appointments/delete", headers=regular_user["headers"], params={"id": appt_id})
    assert r.status_code == 200


def test_delete_nonexistent_appointment(client, regular_user):
    r = client.delete("/appointments/delete", headers=regular_user["headers"], params={"id": "999999"})
    assert r.status_code == 404


def test_appointment_is_checked_defaults_false(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Agenda Teste 6")
    r = client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "P", "patient_cpf": valid_cpf(), "doctor_cpf": doctor_cpf,
        "date": "2027-05-10", "time": "08:00:00",
    })
    assert r.json()["is_checked"] is False
    del_appointment(int(r.json()["id"]))


def _appointment_status(client, headers, appt_id):
    r = client.get("/appointments/list", headers=headers)
    return next(a["status"] for a in r.json() if a["id"] == appt_id)


def test_confirm_page_shows_appointment_without_confirming(client, regular_user, valid_cpf, make_doctor):
    """Abrir o link não confirma: prévias de link do WhatsApp/email não podem confirmar sozinhas."""
    doctor_cpf = make_doctor("Dr Agenda Teste 7")
    patient_cpf = valid_cpf()
    r1 = client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "Maria da Silva", "patient_cpf": patient_cpf, "doctor_cpf": doctor_cpf,
        "date": "2027-05-11", "time": "08:00:00",
    })
    appt_id = r1.json()["id"]
    token = get_confirmation_token(int(appt_id))

    r = client.get("/appointments/confirm", params={"id": appt_id, "token": token})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "Confirmar presença" in r.text
    assert "Olá, Maria!" in r.text
    assert "Dr Agenda Teste 7" in r.text
    assert "terça-feira, 11 de maio de 2027" in r.text
    assert "08:00" in r.text
    # Nada de dado sensível na página pública
    assert patient_cpf not in r.text
    assert "da Silva" not in r.text

    assert _appointment_status(client, regular_user["headers"], appt_id) == "pendente"


def test_confirm_page_security_headers(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Agenda Teste 8")
    r1 = client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "P", "patient_cpf": valid_cpf(), "doctor_cpf": doctor_cpf,
        "date": "2027-05-12", "time": "08:00:00",
    })
    appt_id = r1.json()["id"]
    token = get_confirmation_token(int(appt_id))

    r = client.get("/appointments/confirm", params={"id": appt_id, "token": token})
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert "noindex" in r.headers["x-robots-tag"]
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]


def test_confirm_button_confirms_without_login(client, regular_user, valid_cpf, make_doctor):
    """A confirmação é pública -- o paciente aperta o botão sem precisar de conta."""
    doctor_cpf = make_doctor("Dr Agenda Teste 9")
    r1 = client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "P", "patient_cpf": valid_cpf(), "doctor_cpf": doctor_cpf,
        "date": "2027-05-13", "time": "08:00:00",
    })
    appt_id = r1.json()["id"]
    token = get_confirmation_token(int(appt_id))

    r = client.post("/appointments/confirm", data={"id": appt_id, "token": token})
    assert r.status_code == 200
    assert "Presença confirmada" in r.text
    assert _appointment_status(client, regular_user["headers"], appt_id) == "confirmado"

    # Abrir o link de novo mostra que já está confirmada, sem botão
    r = client.get("/appointments/confirm", params={"id": appt_id, "token": token})
    assert "Presença confirmada" in r.text
    assert "<button" not in r.text


def test_confirm_wrong_token(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Agenda Teste 16")
    r1 = client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "P", "patient_cpf": valid_cpf(), "doctor_cpf": doctor_cpf,
        "date": "2027-05-15", "time": "08:00:00",
    })
    appt_id = r1.json()["id"]

    r = client.get("/appointments/confirm", params={"id": appt_id, "token": "token-completamente-errado"})
    assert r.status_code == 404
    assert "Link inválido" in r.text
    assert "Dr Agenda Teste 16" not in r.text

    r = client.post("/appointments/confirm", data={"id": appt_id, "token": "token-completamente-errado"})
    assert r.status_code == 404
    assert _appointment_status(client, regular_user["headers"], appt_id) == "pendente"


def test_confirm_link_expires_after_appointment_date(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Agenda Teste 17")
    r1 = client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "P", "patient_cpf": valid_cpf(), "doctor_cpf": doctor_cpf,
        "date": "2020-01-10", "time": "08:00:00",
    })
    appt_id = r1.json()["id"]
    token = get_confirmation_token(int(appt_id))

    r = client.get("/appointments/confirm", params={"id": appt_id, "token": token})
    assert r.status_code == 409
    assert "já passou" in r.text

    r = client.post("/appointments/confirm", data={"id": appt_id, "token": token})
    assert r.status_code == 409
    assert _appointment_status(client, regular_user["headers"], appt_id) == "pendente"


def test_check_appointment_by_receptionist(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Agenda Teste 10")
    r1 = client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "P", "patient_cpf": valid_cpf(), "doctor_cpf": doctor_cpf,
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


def test_confirm_invalid_id_format_shows_invalid_link(client):
    for id in ("abc", "²", "99999999999999999999", "0"):
        r = client.get("/appointments/confirm", params={"id": id, "token": "x"})
        assert r.status_code == 404, id
        assert "Link inválido" in r.text

        r = client.post("/appointments/confirm", data={"id": id, "token": "x"})
        assert r.status_code == 404, id


def test_whatsapp_link_asks_patient_to_reply_by_default(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Agenda Teste 11")
    cpf = valid_cpf()
    appt_id = _create_appointment_with_patient(client, regular_user["headers"], cpf, doctor_cpf, "2027-06-01")

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


def test_whatsapp_link_with_link_lets_patient_confirm(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Agenda Teste 12")
    cpf = valid_cpf()
    appt_id = _create_appointment_with_patient(client, regular_user["headers"], cpf, doctor_cpf, "2027-06-02")
    token = get_confirmation_token(int(appt_id))

    r = client.get("/appointments/notify/whatsapp-link", headers=regular_user["headers"],
                   params={"id": appt_id, "with_link": True})
    assert r.status_code == 200
    text = unquote(r.json()["url"].split("?text=", 1)[1])
    assert "Responda SIM" not in text
    assert f"/appointments/confirm?id={int(appt_id)}&token={token}" in text

    # O link que vai na mensagem funciona de verdade, sem login: abre a página e o botão confirma.
    confirm_path = text[text.index("/appointments/confirm"):].split()[0]
    r = client.get(confirm_path)
    assert r.status_code == 200
    assert 'action="confirm"' in r.text
    r = client.post("/appointments/confirm", data={"id": appt_id, "token": token})
    assert r.status_code == 200
    assert _appointment_status(client, regular_user["headers"], appt_id) == "confirmado"

    del_appointment(int(appt_id))
    del_patient(cpf)


def test_email_link_asks_patient_to_reply_by_default(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Agenda Teste 13")
    cpf = valid_cpf()
    appt_id = _create_appointment_with_patient(client, regular_user["headers"], cpf, doctor_cpf, "2027-06-03")

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


def test_email_link_with_link_includes_confirmation(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Agenda Teste 14")
    cpf = valid_cpf()
    appt_id = _create_appointment_with_patient(client, regular_user["headers"], cpf, doctor_cpf, "2027-06-04")
    token = get_confirmation_token(int(appt_id))

    r = client.get("/appointments/notify/email-link", headers=regular_user["headers"],
                   params={"id": appt_id, "with_link": True})
    assert r.status_code == 200
    message = parse_qs(urlsplit(r.json()["url"]).query)["body"][0]
    assert f"/appointments/confirm?id={int(appt_id)}&token={token}" in message

    del_appointment(int(appt_id))
    del_patient(cpf)


def test_notify_link_patient_not_registered(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Agenda Teste 15")
    r1 = client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "Sem Cadastro", "patient_cpf": valid_cpf(), "doctor_cpf": doctor_cpf,
        "date": "2027-06-05", "time": "14:00:00",
    })
    appt_id = r1.json()["id"]

    r = client.get("/appointments/notify/whatsapp-link", headers=regular_user["headers"], params={"id": appt_id})
    assert r.status_code == 404
    assert "Paciente" in r.json()["detail"]

    del_appointment(int(appt_id))


def test_pending_appointment_gets_confirmation_template(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Modelo Teste 1")
    cpf = valid_cpf()
    appt_id = _create_appointment_with_patient(client, regular_user["headers"], cpf, doctor_cpf, "2027-07-01")

    r = client.get("/appointments/notify/whatsapp-link", headers=regular_user["headers"], params={"id": appt_id})
    assert r.json()["template"] == "confirmacao"

    r = client.get("/appointments/notify/email-link", headers=regular_user["headers"], params={"id": appt_id})
    assert r.json()["template"] == "confirmacao"

    del_appointment(int(appt_id))
    del_patient(cpf)


def test_confirmed_appointment_gets_reminder_on_whatsapp(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Modelo Teste 2")
    cpf = valid_cpf()
    appt_id = _create_appointment_with_patient(client, regular_user["headers"], cpf, doctor_cpf, "2027-07-02")
    client.put("/appointments/check", headers=regular_user["headers"], params={"id": appt_id})

    # with_link é ignorado no lembrete: a consulta já está confirmada
    r = client.get("/appointments/notify/whatsapp-link", headers=regular_user["headers"],
                   params={"id": appt_id, "with_link": True})
    assert r.status_code == 200
    assert r.json()["template"] == "lembrete"

    text = unquote(r.json()["url"].split("?text=", 1)[1])
    assert "Lembrete" in text
    assert "Dr Modelo Teste 2" in text
    assert "02/07/2027 às 14:00" in text
    assert "Responda SIM" not in text
    assert "/appointments/confirm" not in text
    assert regular_user["email"] in text

    del_appointment(int(appt_id))
    del_patient(cpf)


def test_confirmed_appointment_gets_reminder_on_email(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Modelo Teste 3")
    cpf = valid_cpf()
    appt_id = _create_appointment_with_patient(client, regular_user["headers"], cpf, doctor_cpf, "2027-07-03")
    client.put("/appointments/check", headers=regular_user["headers"], params={"id": appt_id})

    r = client.get("/appointments/notify/email-link", headers=regular_user["headers"], params={"id": appt_id})
    assert r.status_code == 200
    assert r.json()["template"] == "lembrete"

    query = parse_qs(urlsplit(r.json()["url"]).query)
    assert query["subject"] == ["Lembrete da sua consulta"]
    assert "Lembrete" in query["body"][0]
    assert "Responda SIM" not in query["body"][0]

    del_appointment(int(appt_id))
    del_patient(cpf)


def test_no_message_for_closed_appointments(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Modelo Teste 4")
    cpf = valid_cpf()
    appt_id = _create_appointment_with_patient(client, regular_user["headers"], cpf, doctor_cpf, "2027-07-04")

    for status in ("concluido", "ausente", "cancelado"):
        client.put("/appointments/status", headers=regular_user["headers"], params={"id": appt_id, "status": status})
        for canal in ("whatsapp", "email"):
            r = client.get(f"/appointments/notify/{canal}-link", headers=regular_user["headers"], params={"id": appt_id})
            assert r.status_code == 409, (status, canal)
            assert status in r.json()["detail"]

    del_appointment(int(appt_id))
    del_patient(cpf)


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


def _create_simple_appointment(client, headers, patient_cpf, doctor_cpf, date="2027-08-01", time="10:00:00"):
    r = client.post("/appointments/create", headers=headers, json={
        "patient_name": "P", "patient_cpf": patient_cpf, "doctor_cpf": doctor_cpf,
        "date": date, "time": time,
    })
    assert r.status_code == 200, r.text
    return r.json()


def test_new_appointment_is_pending_with_doctor_cpf(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Status Teste 1")
    body = _create_simple_appointment(client, regular_user["headers"], valid_cpf(), doctor_cpf)

    assert body["status"] == "pendente"
    assert body["reason"] is None
    assert body["doctor_cpf"] == doctor_cpf
    assert body["doctor_name"] == "Dr Status Teste 1"


def test_create_appointment_by_doctor_name_still_works(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Status Teste Nome Unico")
    r = client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "P", "patient_cpf": valid_cpf(), "doctor_name": "Dr Status Teste Nome Unico",
        "date": "2027-08-02", "time": "10:00:00",
    })
    assert r.status_code == 200
    assert r.json()["doctor_cpf"] == doctor_cpf


def test_create_appointment_unknown_doctor(client, regular_user, valid_cpf):
    r = client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "P", "patient_cpf": valid_cpf(), "doctor_cpf": valid_cpf(),
        "date": "2027-08-03", "time": "10:00:00",
    })
    assert r.status_code == 404


def test_create_appointment_without_doctor(client, regular_user, valid_cpf):
    r = client.post("/appointments/create", headers=regular_user["headers"], json={
        "patient_name": "P", "patient_cpf": valid_cpf(), "date": "2027-08-03", "time": "10:00:00",
    })
    assert r.status_code == 422


def test_status_cancel_with_reason(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Status Teste 2")
    appt = _create_simple_appointment(client, regular_user["headers"], valid_cpf(), doctor_cpf)

    r = client.put("/appointments/status", headers=regular_user["headers"],
                   params={"id": appt["id"], "status": "cancelado", "reason": "Paciente viajou"})
    assert r.status_code == 200
    assert r.json()["status"] == "cancelado"
    assert r.json()["reason"] == "Paciente viajou"
    assert r.json()["is_checked"] is False


def test_status_absent_with_reason(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Status Teste 3")
    appt = _create_simple_appointment(client, regular_user["headers"], valid_cpf(), doctor_cpf)

    r = client.put("/appointments/status", headers=regular_user["headers"],
                   params={"id": appt["id"], "status": "ausente", "reason": "Não avisou"})
    assert r.status_code == 200
    assert r.json()["status"] == "ausente"
    assert r.json()["reason"] == "Não avisou"


def test_status_reason_ignored_for_completed(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Status Teste 4")
    appt = _create_simple_appointment(client, regular_user["headers"], valid_cpf(), doctor_cpf)
    client.put("/appointments/status", headers=regular_user["headers"],
               params={"id": appt["id"], "status": "cancelado", "reason": "x"})

    r = client.put("/appointments/status", headers=regular_user["headers"],
                   params={"id": appt["id"], "status": "concluido", "reason": "não deveria ficar"})
    assert r.status_code == 200
    assert r.json()["status"] == "concluido"
    assert r.json()["reason"] is None


def test_status_confirmed_sets_is_checked(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Status Teste 5")
    appt = _create_simple_appointment(client, regular_user["headers"], valid_cpf(), doctor_cpf)

    r = client.put("/appointments/status", headers=regular_user["headers"],
                   params={"id": appt["id"], "status": "confirmado"})
    assert r.json()["is_checked"] is True

    r = client.put("/appointments/check", headers=regular_user["headers"], params={"id": appt["id"], "is_checked": False})
    assert r.json()["status"] == "pendente"


def test_status_invalid_value(client, regular_user):
    r = client.put("/appointments/status", headers=regular_user["headers"], params={"id": "00001", "status": "sumiu"})
    assert r.status_code == 422


def test_status_requires_login(client):
    r = client.put("/appointments/status", params={"id": "00001", "status": "cancelado"})
    assert r.status_code == 401


def test_status_nonexistent_appointment(client, regular_user):
    r = client.put("/appointments/status", headers=regular_user["headers"], params={"id": "999999", "status": "cancelado"})
    assert r.status_code == 404


def test_cancelled_appointment_frees_the_slot(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Status Teste 6")
    appt = _create_simple_appointment(client, regular_user["headers"], valid_cpf(), doctor_cpf)
    client.put("/appointments/status", headers=regular_user["headers"],
               params={"id": appt["id"], "status": "cancelado"})

    novo = _create_simple_appointment(client, regular_user["headers"], valid_cpf(), doctor_cpf)
    assert novo["status"] == "pendente"

    # Reativar a cancelada agora daria dois pacientes no mesmo horário
    r = client.put("/appointments/status", headers=regular_user["headers"],
                   params={"id": appt["id"], "status": "pendente"})
    assert r.status_code == 409


def test_confirm_link_does_not_reopen_cancelled(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Status Teste 7")
    appt = _create_simple_appointment(client, regular_user["headers"], valid_cpf(), doctor_cpf)
    client.put("/appointments/status", headers=regular_user["headers"],
               params={"id": appt["id"], "status": "cancelado"})

    token = get_confirmation_token(int(appt["id"]))
    r = client.get("/appointments/confirm", params={"id": appt["id"], "token": token})
    assert r.status_code == 409
    assert "foi cancelada" in r.text
    assert "<button" not in r.text

    r = client.post("/appointments/confirm", data={"id": appt["id"], "token": token})
    assert r.status_code == 409
    assert _appointment_status(client, regular_user["headers"], appt["id"]) == "cancelado"


def test_search_appointments_by_status_and_doctor_cpf(client, regular_user, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Status Teste 8")
    a1 = _create_simple_appointment(client, regular_user["headers"], valid_cpf(), doctor_cpf, time="10:00:00")
    _create_simple_appointment(client, regular_user["headers"], valid_cpf(), doctor_cpf, time="11:00:00")
    client.put("/appointments/status", headers=regular_user["headers"],
               params={"id": a1["id"], "status": "cancelado"})

    r = client.get("/appointments/search", headers=regular_user["headers"],
                   params={"doctor_cpf": doctor_cpf, "status": "cancelado"})
    assert r.status_code == 200
    assert [a["id"] for a in r.json()] == [a1["id"]]


def test_renaming_doctor_updates_appointments(client, admin, valid_cpf, make_doctor):
    doctor_cpf = make_doctor("Dr Nome Antigo")
    appt = _create_simple_appointment(client, admin["headers"], valid_cpf(), doctor_cpf)

    r = client.put("/doctors/update", headers=admin["headers"], params={"cpf": doctor_cpf}, json={"name": "Dr Nome Novo"})
    assert r.status_code == 200

    r = client.get("/appointments/search", headers=admin["headers"], params={"doctor_cpf": doctor_cpf})
    assert [a["doctor_name"] for a in r.json()] == ["Dr Nome Novo"]
    assert r.json()[0]["id"] == appt["id"]


def test_changing_doctor_cpf_keeps_appointments_linked(client, admin, valid_cpf, make_doctor):
    old_cpf = make_doctor("Dr Troca CPF")
    appt = _create_simple_appointment(client, admin["headers"], valid_cpf(), old_cpf)
    new_cpf = valid_cpf()

    r = client.put("/doctors/update", headers=admin["headers"], params={"cpf": old_cpf}, json={"cpf": new_cpf})
    assert r.status_code == 200

    r = client.get("/appointments/search", headers=admin["headers"], params={"doctor_cpf": new_cpf})
    assert [a["id"] for a in r.json()] == [appt["id"]]
    assert r.json()[0]["doctor_name"] == "Dr Troca CPF"

    del_appointment(int(appt["id"]))
    del_doctor(new_cpf)
