#!/usr/bin/env python3
"""Збирає курс в один автономний index.html.

Артефакт — index.html у корені проєкту: саме його віддає GitHub Pages
за адресою https://<user>.github.io/<repo>/.

Модулі знаходяться обходом curriculum/level_*/module_*/module_meta.json.
До збірки потрапляють лише модулі зі статусом із course_meta.publishable_statuses.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


MARKER = "__COURSE_DATA__"
ACTIVITY_FILES = {
    "precheck": "lesson_precheck.json",
    "lesson": "lesson_activities.json",
    "practice": "practice_activity.json",
    "case": "case_activity.json",
    "checklist": "checklist_activity.json",
    "glossary": "glossary_activity.json",
}
SECTIONS = [
    ("lesson", "Урок", "lesson.md"),
    ("practice", "Практика", "practice.md"),
    ("case", "Кейс", "case_study.md"),
    ("checklist", "Чекліст", "checklist.md"),
    ("glossary", "Глосарій", "glossary.md"),
    ("reference", "Пам’ятка", "reference_card.md"),
    ("sources", "Джерела", "references.md"),
]


class BuildError(Exception):
    """Помилка складання з поясненням для автора модуля."""


def read_json(path: Path) -> dict | list:
    if not path.exists():
        raise BuildError(f"немає обов’язкового файлу {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BuildError(f"{path}: некоректний JSON ({exc})") from exc


def read_markdown(directory: Path, name: str) -> str:
    path = directory / name
    if not path.exists():
        raise BuildError(f"немає обов’язкового файлу {path}")
    text = path.read_text(encoding="utf-8")
    if text.startswith("---\n"):
        _, _, text = text.partition("\n---\n")
    text = text.strip()
    if not text:
        raise BuildError(f"{path}: файл порожній")
    return text


def module_index(meta: dict, path: Path) -> int:
    match = re.search(r"(\d+)\s*$", str(meta.get("id", "")))
    if not match:
        raise BuildError(f"{path}: id модуля має закінчуватися номером, наприклад module-02")
    return int(match.group(1))


def quiz_path(root: Path, meta: dict) -> Path:
    return root / "quizzes" / "modules" / f"{str(meta['id']).replace('-', '_')}_quiz.json"


def collect_module(directory: Path, root: Path) -> dict:
    meta = read_json(directory / "module_meta.json")
    if not isinstance(meta, dict):
        raise BuildError(f"{directory}/module_meta.json: очікується об’єкт")
    for field in ("id", "level", "title", "status"):
        if not meta.get(field):
            raise BuildError(f"{directory}/module_meta.json: немає поля {field}")
    quiz = read_json(quiz_path(root, meta))
    if not isinstance(quiz, list) or not quiz:
        raise BuildError(f"{quiz_path(root, meta)}: очікується непорожній список питань")
    activities = {name: read_json(directory / filename) for name, filename in ACTIVITY_FILES.items()}
    case = activities["case"]
    action_ids = [action["id"] for action in case.get("actions", [])]
    initial = case.get("initial_order")
    if not initial:
        raise BuildError(f"{directory}: у case_activity.json немає initial_order")
    if sorted(initial) != sorted(action_ids):
        raise BuildError(f"{directory}: initial_order не збігається зі списком actions")
    if initial == action_ids:
        raise BuildError(f"{directory}: initial_order дорівнює правильному порядку — кейс віддавав би бали без роботи")
    pages = {section[0] for section in SECTIONS} | {"overview", "guide", "quiz"}
    for session in meta.get("sessions") or []:
        unknown = [page for page in session.get("pages") or [] if page not in pages]
        if unknown:
            raise BuildError(f"{directory}: сесія «{session.get('title')}» посилається на невідомі сторінки {unknown}")
    return {
        "index": module_index(meta, directory),
        "id": meta["id"],
        "level": meta["level"],
        "slug": directory.name,
        "meta": meta,
        "sections": [
            {"id": key, "title": title, "content": read_markdown(directory, filename)}
            for key, title, filename in SECTIONS
        ],
        "quiz": quiz,
        "activities": activities,
    }


def level_quiz_path(root: Path, level: int) -> Path:
    return root / "quizzes" / "levels" / f"level_{int(level):02d}_quiz.json"


def collect_level_quiz(root: Path, level: dict, published: int, report) -> list | None:
    """Рівневий квіз потрапляє до збірки, лише коли рівень закрито.

    Машинний відповідник вимоги SCALING_PLAN §7.1 «всі модулі рівня готові»:
    інших даних про готовність незібраних модулів у збірці немає.
    """
    path = level_quiz_path(root, level.get("level"))
    if not path.exists():
        return None
    planned = int(level.get("planned_modules") or 0)
    if published < planned:
        report(f"пропущено {path.name}: рівень {level.get('level')} ще не закрито "
               f"({published} із {planned} модулів опубліковано)")
        return None
    quiz = read_json(path)
    if not isinstance(quiz, list) or not quiz:
        raise BuildError(f"{path}: очікується непорожній список питань")
    for question in quiz:
        modules = question.get("modules") if isinstance(question, dict) else None
        if not isinstance(modules, list) or len(modules) < 2:
            raise BuildError(f"{path}: питання {question.get('id') if isinstance(question, dict) else '?'} "
                             f"має спиратися щонайменше на два модулі рівня")
    return quiz


def discover(root: Path) -> list[Path]:
    curriculum = root / "curriculum"
    if not curriculum.exists():
        raise BuildError(f"немає каталогу {curriculum}")
    found = [path.parent for path in curriculum.glob("level_*/module_*/module_meta.json")]
    return sorted(found, key=lambda p: (p.parent.name, p.name))


def build_payload(root: Path, report=print) -> dict:
    course = read_json(root / "course_meta.json")
    publishable = set(course.get("publishable_statuses") or ["app_ready", "released"])
    modules: list[dict] = []
    for directory in discover(root):
        meta = read_json(directory / "module_meta.json")
        status = meta.get("status")
        if status not in publishable:
            report(f"пропущено {directory.name}: статус {status}")
            continue
        modules.append(collect_module(directory, root))
    if not modules:
        raise BuildError("жоден модуль не має статусу, дозволеного для публікації")
    modules.sort(key=lambda m: (m["level"], m["index"]))
    guide_path = root / "LEARNER_GUIDE.md"
    if not guide_path.exists():
        raise BuildError(f"немає {guide_path}")
    course_payload = dict(course)
    course_payload.pop("publishable_statuses", None)
    course_payload["published_modules"] = len(modules)
    levels = []
    for level in course_payload.get("levels") or []:
        entry = dict(level)
        published = sum(1 for module in modules if module["level"] == level.get("level"))
        quiz = collect_level_quiz(root, level, published, report)
        if quiz:
            entry["quiz"] = quiz
        levels.append(entry)
    course_payload["levels"] = levels
    course_payload["guide"] = guide_path.read_text(encoding="utf-8").strip()
    return {"course": course_payload, "modules": modules}


def render(root: Path, output: Path, report=print) -> Path:
    template = (root / "app" / "index.template.html").read_text(encoding="utf-8")
    if template.count(MARKER) != 1:
        raise BuildError(f"Шаблон має містити рівно один маркер {MARKER}")
    payload = build_payload(root, report=report)
    encoded = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(template.replace(MARKER, encoded), encoding="utf-8")
    questions = sum(len(module["quiz"]) for module in payload["modules"])
    level_questions = sum(len(level.get("quiz") or []) for level in payload["course"].get("levels") or [])
    report(
        f"{output}\nмодулів: {len(payload['modules'])} із {payload['course']['planned_modules']} запланованих, "
        f"питань: {questions}"
        + (f" (+{level_questions} рівневих)" if level_questions else "")
        + f", розмір: {output.stat().st_size // 1024} КБ"
    )
    return output


def main() -> int:
    root_default = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=root_default, help="корінь проєкту")
    parser.add_argument("--output", type=Path, default=None,
                        help="шлях до згенерованого HTML (типово index.html у корені проєкту)")
    args = parser.parse_args()
    output = args.output or args.root / "index.html"
    try:
        render(args.root, output)
    except BuildError as exc:
        print(f"FAIL: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
