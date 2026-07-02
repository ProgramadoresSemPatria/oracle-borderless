"""Base de comandos CLI com DSL de `signature` (estilo Laravel Artisan).

DSL da signature:
  - `{name:type}`      argumento posicional obrigatório (type ∈ str/int/float/bool, default str)
  - `{--flag:bool}`    flag booleana (--flag / --no-flag, default False)
  - `{--option:type=}` opção com valor (--option VALUE, default None)

`handle()` pode ser sync ou `async def`. Os valores parseados ficam em `self.input`.
"""

import argparse
import re
from abc import ABC, abstractmethod
from typing import Any

_TYPES: dict[str, type] = {"str": str, "int": int, "float": float, "bool": bool}
_TOKEN = re.compile(r"\{([^}]+)\}")


class Command(ABC):
    """Subclasse define `signature`, `description` e implementa `handle()`."""

    signature: str = ""
    description: str = ""

    def __init__(self) -> None:
        self.input: dict[str, Any] = {}

    # --- metadados derivados da signature ---

    @classmethod
    def name(cls) -> str:
        """Nome do comando: o texto antes do primeiro `{` (ex.: `documents:ingest`)."""
        head = cls.signature.split("{", 1)[0]
        return head.strip()

    @classmethod
    def _build_parser(cls) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog=cls.name(), description=cls.description)
        for raw in _TOKEN.findall(cls.signature):
            token = raw.strip()
            if token.startswith("--"):
                cls._add_option(parser, token[2:])
            else:
                cls._add_argument(parser, token)
        return parser

    @staticmethod
    def _split_type(token: str) -> tuple[str, str, str | None]:
        """Retorna (nome, tipo, marca_default) a partir de `nome:tipo` ou `nome:tipo=`."""
        default_marker = None
        if "=" in token:
            token, default_marker = token.split("=", 1)
        name, _, type_name = token.partition(":")
        return name.strip(), (type_name.strip() or "str"), default_marker

    @classmethod
    def _add_argument(cls, parser: argparse.ArgumentParser, token: str) -> None:
        name, type_name, _ = cls._split_type(token)
        parser.add_argument(name, type=_TYPES.get(type_name, str))

    @classmethod
    def _add_option(cls, parser: argparse.ArgumentParser, token: str) -> None:
        name, type_name, has_value = cls._split_type(token)
        dest = name.replace("-", "_")
        if type_name == "bool" and has_value is None:
            parser.add_argument(
                f"--{name}", dest=dest, action=argparse.BooleanOptionalAction, default=False
            )
        else:
            parser.add_argument(
                f"--{name}", dest=dest, type=_TYPES.get(type_name, str), default=None
            )

    # --- execução ---

    def parse(self, argv: list[str]) -> None:
        parsed = self._build_parser().parse_args(argv)
        self.input = vars(parsed)

    @abstractmethod
    def handle(self) -> Any:
        """Lógica do comando. Pode ser sync ou async."""
        raise NotImplementedError
