"""Loader/dispatcher de comandos CLI — autodescobre comandos em app/console/commands."""

import asyncio
import importlib
import inspect
import pkgutil
import sys

from src.support.core.console.command import Command


def load_commands() -> dict[str, type[Command]]:
    """Descobre todas as subclasses de Command em src/app/console/commands/."""
    import src.app.console.commands as commands_pkg

    registry: dict[str, type[Command]] = {}
    for module_info in pkgutil.iter_modules(commands_pkg.__path__):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"src.app.console.commands.{module_info.name}")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, Command) and obj is not Command and obj.signature:
                registry[obj.name()] = obj
    return registry


def _print_help(registry: dict[str, type[Command]]) -> None:
    print("Comandos disponíveis:\n")
    if not registry:
        print("  (nenhum comando registrado ainda em src/app/console/commands/)")
        return
    for name, command in sorted(registry.items()):
        print(f"  {name:<28} {command.description}")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    registry = load_commands()

    if not argv or argv[0] in ("-h", "--help", "list"):
        _print_help(registry)
        return 0

    name, rest = argv[0], argv[1:]
    command_class = registry.get(name)
    if command_class is None:
        print(f"Comando desconhecido: {name}\n")
        _print_help(registry)
        return 1

    command = command_class()
    command.parse(rest)

    result = command.handle()
    if inspect.iscoroutine(result):
        asyncio.run(result)
    return 0
