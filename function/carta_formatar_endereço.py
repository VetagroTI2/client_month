def formatar_endereco(texto):
    if texto.startswith("ENDERECO="):
        texto = texto[len("ENDERECO="):]
    partes = texto.split(";")
    rua = partes[0] if len(partes) > 0 else ""
    numero = partes[1] if len(partes) > 1 else ""
    bairro = partes[2] if len(partes) > 2 else ""
    cidade = partes[3] if len(partes) > 3 else ""
    estado = partes[4] if len(partes) > 4 else ""
    cep = partes[5] if len(partes) > 5 else ""

    return (f"Endereço: {rua}, nº{numero}\nBairro: {bairro}\nCidade: {cidade} - {estado}\nCEP: {cep}")
