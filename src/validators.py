def _calcula_digito(cpf_parcial: str) -> int:
    peso = len(cpf_parcial) + 1
    soma = sum(int(digito) * (peso - i) for i, digito in enumerate(cpf_parcial))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


def validate_cpf(cpf: str) -> str:
    if not cpf.isdigit() or len(cpf) != 11:
        raise ValueError("CPF deve conter exatamente 11 dígitos numéricos")

    if cpf == cpf[0] * 11:
        raise ValueError("CPF inválido")

    digito1 = _calcula_digito(cpf[:9])
    digito2 = _calcula_digito(cpf[:9] + str(digito1))

    if cpf[-2:] != f"{digito1}{digito2}":
        raise ValueError("CPF inválido")

    return cpf
