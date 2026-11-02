"""Запуск из командной строки.

  python -m card_assistant.cli generate data/products/manometer_dm02.json
  python -m card_assistant.cli check data/products/incomplete_sensor.json
  python -m card_assistant.cli regenerate
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

from .config import ConfigError, load_settings
from .llm import LLMClient, LLMError
from .pipeline import generate_card
from .precheck import run_precheck
from .render import card_to_markdown
from .schemas import InputError, ProductInput, parse_product

PRODUCTS_DIR = Path("data/products")
EXAMPLES_DIR = Path("examples")


def read_product(path: Path) -> ProductInput:
    try:
        return parse_product(path.read_bytes())
    except OSError as exc:
        raise InputError(f"Не удалось прочитать файл {path}.") from exc


def build_card(product: ProductInput, env_file: str | None):
    settings = load_settings(env_file)
    settings.check_ready()
    return generate_card(product, LLMClient(settings), settings.max_attempts)


def cmd_generate(args) -> int:
    card = build_card(read_product(Path(args.file)), args.env_file)
    if args.json:
        print(card.model_dump_json(indent=2))
    else:
        print(card_to_markdown(card))
    return 0


def cmd_check(args) -> int:
    """Только проверки без модели: работает без ключа и без интернета."""
    pre = run_precheck(read_product(Path(args.file)))
    print(f"Данных достаточно для генерации: {'нет' if pre.insufficient else 'да'}")
    for warning in pre.warnings:
        print(f"Предупреждение: {warning}")
    for item in pre.missing_fields:
        print(f"Не хватает: {item.field} ({item.reason})")
    for row in pre.characteristics:
        print(f"{row.name}: {row.value} [{row.source}]")
    return 0


def cmd_regenerate(args) -> int:
    """Пересобирает examples/ из всех файлов data/products/ одной командой."""
    paths = sorted(PRODUCTS_DIR.glob("*.json"))
    if not paths:
        raise InputError(f"В папке {PRODUCTS_DIR} нет файлов .json.")
    EXAMPLES_DIR.mkdir(exist_ok=True)
    for path in paths:
        card = build_card(read_product(path), args.env_file)
        shutil.copyfile(path, EXAMPLES_DIR / f"{path.stem}.input.json")
        (EXAMPLES_DIR / f"{path.stem}.card.json").write_text(
            json.dumps(card.model_dump(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (EXAMPLES_DIR / f"{path.stem}.card.md").write_text(
            card_to_markdown(card), encoding="utf-8"
        )
        print(f"{path.name}: {card.status}, попыток {len(card.attempts)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    # В консоли Windows кодировка по умолчанию может не уметь кириллицу и тире
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Черновик карточки товара")
    parser.add_argument("--env-file", help="файл настроек вместо .env")
    commands = parser.add_subparsers(dest="command", required=True)

    generate = commands.add_parser("generate", help="создать карточку по JSON-файлу")
    generate.add_argument("file")
    generate.add_argument("--json", action="store_true", help="вывести JSON вместо Markdown")
    generate.set_defaults(func=cmd_generate)

    check = commands.add_parser("check", help="проверить данные без обращения к модели")
    check.add_argument("file")
    check.set_defaults(func=cmd_check)

    regenerate = commands.add_parser("regenerate", help="пересобрать examples/ из data/products/")
    regenerate.set_defaults(func=cmd_regenerate)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (InputError, ConfigError, LLMError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
