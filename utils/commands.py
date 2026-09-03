"""
utils/commands.py
Registro central de comandos.

O decorator @cmd() substitui o padrão repetido em todo plugin
(@Client.on_message(cmd_filter("x") & filters.me)) por uma única linha,
e guarda metadados (descrição tirada da docstring, módulo de origem) num
registro em memória — usado pelo ,menu pra montar a listagem sem precisar
reabrir e reparsear cada arquivo de plugin a cada chamada.
"""
from dataclasses import dataclass

from pyrogram import Client, filters

from utils.helpers import cmd_filter


@dataclass
class ComandoInfo:
    nome: str
    modulo: str
    desc: str = ""
    func_nome: str = ""


# {modulo (ex: "moderation.py"): [ComandoInfo, ...]}, na ordem em que os
# plugins foram carregados (main.py já carrega em ordem alfabética estável).
REGISTRY: dict[str, list[ComandoInfo]] = {}


def cmd(nome: str, group: int = 0):
    """
    Registra e cria o handler de um comando.

    A descrição exibida no ,menu vem automaticamente da primeira linha
    da docstring da função — não precisa duplicar o texto.

    Uso:
        @cmd("ping")
        async def cmd_ping(client, message):
            \"\"\"Mede a latência do bot.\"\"\"
            ...
    """
    def decorator(func):
        modulo = func.__module__.rsplit(".", 1)[-1] + ".py"
        desc = (func.__doc__ or "").strip().splitlines()[0].strip() if func.__doc__ else ""
        REGISTRY.setdefault(modulo, []).append(
            ComandoInfo(nome=nome, modulo=modulo, desc=desc, func_nome=func.__name__)
        )
        handler = Client.on_message(cmd_filter(nome) & filters.me, group=group)
        return handler(func)
    return decorator
