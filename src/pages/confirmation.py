"""Páginas que o paciente vê ao abrir o link de confirmação (sem login).

Só mostram o primeiro nome do paciente, o médico, a data e o horário; nunca o CPF.
"""
from html import escape

from fastapi.responses import HTMLResponse

_WEEKDAYS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
_MONTHS = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]

# O token vai na URL: sem cache, sem indexação e sem Referer para outros sites.
_SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
    "X-Robots-Tag": "noindex, nofollow",
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": (
        "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; "
        "frame-ancestors 'none'; base-uri 'none'"
    ),
}

_STYLE = """
    :root {
        --bg: #f3f6f9; --card: #ffffff; --text: #1f2933; --muted: #5f6b7a; --line: #e3e8ee;
        --primary: #0d6efd; --primary-hover: #0b5ed7;
        --ok: #198754; --ok-bg: #e8f5ee; --warn: #b26a00; --warn-bg: #fff4e0; --error: #c0392b; --error-bg: #fdecea;
    }
    @media (prefers-color-scheme: dark) {
        :root {
            --bg: #12161b; --card: #1b2128; --text: #e6eaef; --muted: #9aa5b1; --line: #2c343d;
            --primary: #4c8dff; --primary-hover: #6aa1ff;
            --ok: #4cc38a; --ok-bg: #16301f; --warn: #f0a83c; --warn-bg: #33270f; --error: #f0796b; --error-bg: #3a1c19;
        }
    }
    * { box-sizing: border-box; }
    body {
        margin: 0; min-height: 100vh; display: flex; flex-direction: column; align-items: center;
        justify-content: center; padding: 24px 16px; background: var(--bg); color: var(--text);
        font: 16px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    }
    .card {
        width: 100%; max-width: 440px; background: var(--card); border: 1px solid var(--line);
        border-radius: 16px; padding: 32px 24px; text-align: center; box-shadow: 0 8px 24px rgba(0, 0, 0, .06);
    }
    .icon {
        width: 64px; height: 64px; margin: 0 auto 16px; border-radius: 50%; display: flex;
        align-items: center; justify-content: center; font-size: 32px; font-weight: 700;
    }
    .icon.ask { background: var(--bg); color: var(--primary); }
    .icon.ok { background: var(--ok-bg); color: var(--ok); }
    .icon.warn { background: var(--warn-bg); color: var(--warn); }
    .icon.error { background: var(--error-bg); color: var(--error); }
    h1 { font-size: 1.5rem; margin: 0 0 8px; }
    p { margin: 0 0 16px; color: var(--muted); }
    .details { margin: 24px 0; padding: 0; border: 1px solid var(--line); border-radius: 12px; text-align: left; }
    .details div { display: flex; justify-content: space-between; gap: 16px; padding: 12px 16px; }
    .details div + div { border-top: 1px solid var(--line); }
    .details dt { color: var(--muted); }
    .details dd { margin: 0; font-weight: 600; text-align: right; }
    button {
        width: 100%; padding: 14px; border: 0; border-radius: 10px; background: var(--primary);
        color: #fff; font: inherit; font-size: 1.1rem; font-weight: 600; cursor: pointer;
    }
    button:hover { background: var(--primary-hover); }
    .hint { margin: 16px 0 0; font-size: .9rem; }
    .footer { margin-top: 16px; color: var(--muted); font-size: .85rem; }
"""


def _first_name(full_name: str) -> str:
    return full_name.strip().split(" ")[0] if full_name.strip() else ""


def _long_date(d) -> str:
    return f"{_WEEKDAYS[d.weekday()]}, {d.day} de {_MONTHS[d.month - 1]} de {d.year}"


def _details(appointment) -> str:
    return f"""
        <dl class="details">
            <div><dt>Profissional</dt><dd>{escape(appointment.doctor_name)}</dd></div>
            <div><dt>Data</dt><dd>{_long_date(appointment.date)}</dd></div>
            <div><dt>Horário</dt><dd>{appointment.time.strftime('%H:%M')}</dd></div>
        </dl>
    """


def _page(title: str, icon_kind: str, icon: str, body: str, status_code: int = 200) -> HTMLResponse:
    html = f"""<!doctype html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="robots" content="noindex, nofollow">
    <title>{escape(title)} · MinhaAgenda</title>
    <style>{_STYLE}</style>
</head>
<body>
    <main class="card">
        <div class="icon {icon_kind}" aria-hidden="true">{icon}</div>
        <h1>{escape(title)}</h1>
        {body}
    </main>
    <p class="footer">MinhaAgenda</p>
</body>
</html>"""
    return HTMLResponse(html, status_code=status_code, headers=_SECURITY_HEADERS)


def confirm_form_page(appointment, id: int, token: str) -> HTMLResponse:
    """Abrir o link não confirma nada: o paciente precisa apertar o botão.
    Assim a prévia de link do WhatsApp/email não confirma a consulta sozinha."""
    nome = escape(_first_name(appointment.patient_name))
    body = f"""
        <p>Olá, {nome}! Você tem uma consulta marcada:</p>
        {_details(appointment)}
        <form method="post" action="confirm">
            <input type="hidden" name="id" value="{id}">
            <input type="hidden" name="token" value="{escape(token)}">
            <button type="submit">Confirmar presença</button>
        </form>
        <p class="hint">Não vai poder ir? Responda a mensagem que você recebeu ou entre em contato com a clínica.</p>
    """
    return _page("Confirme sua presença", "ask", "?", body)


def confirmed_page(appointment) -> HTMLResponse:
    nome = escape(_first_name(appointment.patient_name))
    body = f"""
        <p>Obrigado, {nome}! Esperamos você.</p>
        {_details(appointment)}
        <p class="hint">Se precisar remarcar, entre em contato com a clínica.</p>
    """
    return _page("Presença confirmada", "ok", "✓", body)


def closed_page(appointment) -> HTMLResponse:
    motivos = {
        "cancelado": "Esta consulta foi cancelada.",
        "concluido": "Esta consulta já foi realizada.",
    }
    motivo = motivos.get(appointment.status, "A data desta consulta já passou.")
    body = f"""
        <p>{motivo}</p>
        {_details(appointment)}
        <p class="hint">Em caso de dúvida, entre em contato com a clínica.</p>
    """
    return _page("Não é possível confirmar", "warn", "!", body, status_code=409)


def invalid_link_page() -> HTMLResponse:
    body = """
        <p>Este link de confirmação não é válido. Confira se ele foi copiado por inteiro
        ou peça uma nova mensagem à clínica.</p>
    """
    return _page("Link inválido", "error", "✕", body, status_code=404)
