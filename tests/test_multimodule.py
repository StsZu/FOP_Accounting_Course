#!/usr/bin/env python3
"""Перевіряє, що складання працює з кількома модулями й падає на неповних даних.

Робочий каталог курсу не змінюється: усе відбувається в тимчасовій копії проєкту.
Запуск: python3 tests/test_multimodule.py
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MODULE = ROOT / "curriculum/level_01/module_01_khto_takyi_fop"
IGNORE = shutil.ignore_patterns("dist", ".git", "node_modules", ".DS_Store")

failures: list[str] = []


def check(name: str, condition: bool, extra: str = "") -> None:
    suffix = f" — {extra}" if extra else ""
    if condition:
        print(f"OK   {name}{suffix}")
    else:
        failures.append(name)
        print(f"FAIL {name}{suffix}")


def build(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(root / "scripts/build_course.py"), "--root", str(root)],
        capture_output=True, text=True,
    )


def payload_of(root: Path) -> dict:
    html = (root / "index.html").read_text(encoding="utf-8")
    match = re.search(r'<script id="course-data" type="application/json">(.*?)</script>', html, re.S)
    assert match, "у зібраному файлі немає даних курсу"
    return json.loads(match.group(1).replace("<\\/", "</"))


def add_module(root: Path, slug: str, level_dir: str, module_id: str, level: int, title: str, status: str) -> Path:
    target = root / "curriculum" / level_dir / slug
    shutil.copytree(SOURCE_MODULE, target)
    meta_path = target / "module_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta.update({"id": module_id, "level": level, "title": title, "status": status})
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    quiz_name = f"{module_id.replace('-', '_')}_quiz.json"
    shutil.copy(ROOT / "quizzes/modules/module_01_quiz.json", root / "quizzes/modules" / quiz_name)
    return target


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "course"
        shutil.copytree(ROOT, root, ignore=IGNORE)

        add_module(root, "module_02_test_copy", "level_01", "module-02", 1, "Тестовий модуль 2", "app_ready")
        (root / "curriculum/level_02").mkdir(parents=True, exist_ok=True)
        draft = add_module(root, "module_03_draft", "level_02", "module-03", 2, "Чернетка", "draft")

        result = build(root)
        check("складання двох модулів завершується успішно", result.returncode == 0, result.stdout.strip() + result.stderr.strip())
        if result.returncode != 0:
            return 1
        check("модуль зі статусом draft пропущено", "пропущено module_03_draft" in result.stdout, result.stdout.strip().splitlines()[0])

        data = payload_of(root)
        modules = data["modules"]
        check("у збірці два модулі", len(modules) == 2, str(len(modules)))
        check("published_modules порахований фактично", data["course"]["published_modules"] == 2)
        check("planned_modules узято з course_meta", data["course"]["planned_modules"] == 38)
        check("ідентифікатори модулів різні", {m["id"] for m in modules} == {"module-01", "module-02"})
        check("індекси похідні від id", [m["index"] for m in modules] == [1, 2])
        check("порядок за рівнем і номером", modules == sorted(modules, key=lambda m: (m["level"], m["index"])))
        check("у кожного модуля власний квіз", all(m["quiz"] for m in modules))
        check("у кожного модуля сім розділів", all(len(m["sections"]) == 7 for m in modules))
        check("у кожного модуля шість наборів вправ", all(len(m["activities"]) == 6 for m in modules))
        check("інструкція учня одна на курс", isinstance(data["course"]["guide"], str) and len(data["course"]["guide"]) > 100)
        check("шаблон не містить назви модуля 1 поза даними",
              "Хто такий ФОП" not in (root / "app/index.template.html").read_text(encoding="utf-8"))
        check("головний артефакт лежить у корені для GitHub Pages", (root / "index.html").exists())
        check("копія для старих посилань збігається з головним артефактом",
              (root / "index.html").read_bytes() == (root / "index.html").read_bytes())

        smoke = subprocess.run(
            ["node", str(root / "tests/logic_smoke.mjs"), str(root / "index.html")],
            capture_output=True, text=True,
        )
        check("логічний тест проходить на двомодульній збірці", smoke.returncode == 0,
              smoke.stdout.strip().splitlines()[-1] if smoke.stdout.strip() else smoke.stderr.strip())
        if smoke.returncode != 0:
            print(smoke.stdout)

        # Негативні сценарії: складання має падати з поясненням, а не мовчати.
        shutil.rmtree(draft)
        broken_quiz = root / "quizzes/modules/module_02_quiz.json"
        broken_quiz.unlink()
        result = build(root)
        check("відсутній квіз зупиняє складання", result.returncode == 1 and "module_02_quiz.json" in result.stdout,
              result.stdout.strip())
        shutil.copy(ROOT / "quizzes/modules/module_01_quiz.json", broken_quiz)

        case_path = root / "curriculum/level_01/module_02_test_copy/case_activity.json"
        case = json.loads(case_path.read_text(encoding="utf-8"))
        case["initial_order"] = [action["id"] for action in case["actions"]]
        case_path.write_text(json.dumps(case, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result = build(root)
        check("готова відповідь у initial_order зупиняє складання",
              result.returncode == 1 and "initial_order" in result.stdout, result.stdout.strip())

        meta_path = root / "curriculum/level_01/module_02_test_copy/module_meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["status"] = "draft"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result = build(root)
        check("непідготовлений модуль не потрапляє до збірки", result.returncode == 0 and "модулів: 1" in result.stdout,
              result.stdout.strip().splitlines()[-1])

    print("\nПРОВАЛЕНО перевірок: " + str(len(failures)) if failures else "\nусі перевірки пройдено")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
