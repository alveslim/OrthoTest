"""Substituto mínimo do pacote `flet` para testar a LÓGICA das telas sem abrir janela.

Não valida a API do Flet (isso exige rodar o app com a versão fixada); só garante que as telas
montam, que os botões chamam as funções certas e que o estado muda como esperado.
"""
import types


class _Meta(type):
    def __getattr__(cls, nome):  # ft.Border.all(...), ft.Padding.only(...)
        return lambda *a, **k: cls(*a, **k)


class Ctl(metaclass=_Meta):
    def __init__(self, *args, **kw):
        self.args = args
        self.__dict__.update(kw)
        self.kw = kw
        # Contêineres do Flet sempre expõem `.controls` (lista); as telas fazem append/clear.
        # Valores padrão dos controles reais.
        for nome, padrao in (("TextField", {"value": ""}), ("Checkbox", {"value": False}),
                             ("Slider", {"value": 0}), ("Text", {"value": None})):
            if type(self).__name__ == nome:
                for k, v in padrao.items():
                    self.__dict__.setdefault(k, v)
        if type(self).__name__ in ("Column", "Row", "ListView", "Stack") and "controls" not in kw:
            self.controls = list(args[0]) if args else []


class _Ns:
    def __getattr__(self, nome):
        return nome


_ESPACOS = {"Colors", "Icons", "FontWeight", "TextAlign", "MainAxisAlignment", "CrossAxisAlignment",
            "KeyboardType", "ThemeMode", "ScrollMode", "TextThemeStyle"}


def instalar() -> types.ModuleType:
    mod = types.ModuleType("flet")
    cache: dict = {}

    def getattr_(nome):
        if nome in _ESPACOS:
            return _Ns()
        if nome == "run":
            return lambda *a, **k: None
        if nome[0].isupper():
            cache.setdefault(nome, type(nome, (Ctl,), {}))
            return cache[nome]
        raise AttributeError(nome)

    mod.__getattr__ = getattr_
    return mod


class Pagina:
    def __init__(self):
        self.controles: list = []
        self.window = Ctl()
        self.atualizacoes = 0

    def add(self, *ctls):
        self.controles.extend(ctls)

    def clean(self):
        self.controles = []

    def update(self):
        self.atualizacoes += 1


def filhos(c):
    if isinstance(c, (list, tuple)):
        return list(c)
    out = []
    for nome in ("content", "controls"):
        v = getattr(c, nome, None)
        if isinstance(v, Ctl):
            out.append(v)
        elif isinstance(v, (list, tuple)):
            out.extend(v)
    return out


def percorrer(raiz):
    pilha = list(raiz) if isinstance(raiz, (list, tuple)) else [raiz]
    while pilha:
        c = pilha.pop(0)
        if not isinstance(c, Ctl):
            continue
        yield c
        pilha[0:0] = filhos(c)


def texto(c) -> str | None:
    if type(c).__name__ != "Text":
        return None
    return getattr(c, "value", None) or (c.args[0] if c.args else None)


def textos(raiz) -> list[str]:
    return [t for t in (texto(c) for c in percorrer(raiz)) if t]


def clicavel_com_texto(raiz, rotulo: str):
    """Primeiro controle com on_click cujo subtree contém o texto exato `rotulo`."""
    for c in percorrer(raiz):
        if getattr(c, "on_click", None) and rotulo in textos(c):
            return c
    raise AssertionError(f"Nenhum controle clicável com o texto {rotulo!r}")
