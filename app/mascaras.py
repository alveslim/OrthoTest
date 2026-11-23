"""Máscaras de digitação: o usuário digita só números e o app põe o ponto."""
import re


def so_digitos(texto: str | None, limite: int) -> str:
    return re.sub(r"\D", "", texto or "")[:limite]


def mascara_altura(texto: str | None) -> str:
    """'156' -> '1.56'; '17' -> '1.7'; '1' -> '1'. Primeiro dígito = metros."""
    d = so_digitos(texto, 3)
    return d if len(d) <= 1 else f"{d[0]}.{d[1:]}"


def mascara_peso(texto: str | None) -> str:
    """Peso em kg inteiros (até 3 dígitos). Decimais: digitar vírgula/ponto, se houver."""
    bruto = (texto or "").replace(",", ".")
    if "." in bruto:
        inteiro, _, dec = bruto.partition(".")
        return f"{so_digitos(inteiro, 3)}.{so_digitos(dec, 1)}"
    return so_digitos(bruto, 3)


def mascara_idade(texto: str | None) -> str:
    return so_digitos(texto, 3)
