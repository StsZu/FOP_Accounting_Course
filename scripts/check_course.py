#!/usr/bin/env python3
"""Один прохід перевірки всього курсу: структура модулів, джерела, квізи, дати актуальності.

Запуск: python3 scripts/check_course.py [--root .]
Повертає 1, якщо є хоча б одна помилка.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


SKILL = Path(".agents/skills/fop-course-builder/scripts")
REQUIRED_MARKDOWN = ["lesson.md", "practice.md", "case_study.md", "checklist.md", "glossary.md", "reference_card.md", "references.md"]
REQUIRED_META = ["schema", "id", "level", "title", "language", "version", "status", "last_verified", "next_review", "outcomes", "source_ids"]
KNOWN_STATUSES = {"planned", "sources_collected", "draft", "fact_checked", "human_reviewed", "quiz_ready", "app_ready", "released"}
PUBLISHED = {"app_ready", "released"}
ACTIVITY_KEYS = {
    "practice_activity.json": ["title", "instructions", "how_to", "facts", "threshold", "source_options", "fields"],
    "case_activity.json": ["title", "instructions", "how_to", "threshold", "situation", "categories", "owners", "risks", "actions", "initial_order"],
    "checklist_activity.json": ["title", "instructions", "how_to", "statuses", "items"],
}


def load(path: Path, errors: list[str]):
    if not path.exists():
        errors.append(f"{path}: файл відсутній")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{path}: некоректний JSON ({exc})")
        return None


def load_anticue():
    """Бере перевірку антипідказок із валідатора квізів, щоб правило було одне на весь курс."""
    import importlib.util
    script = Path(__file__).resolve().parents[1] / SKILL / "validate_quiz.py"
    spec = importlib.util.spec_from_file_location("validate_quiz", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.anticue_errors


def check_lesson_activities(path: Path, items, errors: list[str]) -> None:
    if not isinstance(items, list) or not items:
        errors.append(f"{path}: очікується непорожній список мікроперевірок")
        return
    seen: set[str] = set()
    for number, item in enumerate(items, 1):
        label = f"{path.name}, мікроперевірка {number}"
        if not isinstance(item, dict):
            errors.append(f"{label}: очікується об’єкт")
            continue
        for field in ("id", "section", "scenario", "question", "source_reference"):
            if not item.get(field):
                errors.append(f"{label}: немає поля {field}")
        if item.get("id") in seen:
            errors.append(f"{label}: дублікат id {item.get('id')}")
        seen.add(item.get("id"))
        options = item.get("options")
        if not isinstance(options, list) or len(options) != 3:
            errors.append(f"{label}: options має містити рівно 3 варіанти")
            continue
        if sum(1 for option in options if option.get("correct") is True) != 1:
            errors.append(f"{label}: має бути рівно одна правильна відповідь")
        for index, option in enumerate(options, 1):
            if len(str(option.get("feedback", "")).strip()) < 20:
                errors.append(f"{label}, варіант {index}: feedback відсутній або надто короткий")


def check_module(directory: Path, root: Path, source_ids: set[str], errors: list[str]) -> dict | None:
    meta = load(directory / "module_meta.json", errors)
    if not isinstance(meta, dict):
        return None
    rel = directory.relative_to(root)
    for field in REQUIRED_META:
        if not meta.get(field):
            errors.append(f"{rel}/module_meta.json: немає поля {field}")
    if meta.get("status") not in KNOWN_STATUSES:
        errors.append(f"{rel}/module_meta.json: невідомий статус {meta.get('status')}")
    outcomes = meta.get("outcomes") or []
    if not 2 <= len(outcomes) <= 5:
        errors.append(f"{rel}/module_meta.json: потрібно 2–5 результатів навчання, зараз {len(outcomes)}")
    for source in meta.get("source_ids") or []:
        if source not in source_ids:
            errors.append(f"{rel}/module_meta.json: джерело {source} відсутнє в sources/SOURCE_REGISTER.md")

    for name in REQUIRED_MARKDOWN:
        path = directory / name
        if not path.exists() or not path.read_text(encoding="utf-8").strip():
            errors.append(f"{rel}/{name}: файл відсутній або порожній")

    for name, keys in ACTIVITY_KEYS.items():
        data = load(directory / name, errors)
        if not isinstance(data, dict):
            continue
        for key in keys:
            if key not in data or data[key] in (None, "", [], {}):
                errors.append(f"{rel}/{name}: немає поля {key}")
        if not isinstance(data.get("how_to"), list) or len(data.get("how_to") or []) < 3:
            errors.append(f"{rel}/{name}: how_to має містити щонайменше 3 кроки")

    case = load(directory / "case_activity.json", errors)
    if isinstance(case, dict) and isinstance(case.get("actions"), list):
        action_ids = [a.get("id") for a in case["actions"]]
        initial = case.get("initial_order")
        if not isinstance(initial, list) or sorted(map(str, initial)) != sorted(map(str, action_ids)):
            errors.append(f"{rel}/case_activity.json: initial_order має містити ті самі дії, що й actions")
        elif initial == action_ids:
            errors.append(f"{rel}/case_activity.json: initial_order дорівнює правильному порядку — бали давалися б без роботи")
        for risk in case.get("risks") or []:
            if risk.get("critical") and (risk.get("category") not in (case.get("categories") or []) or risk.get("owner") not in (case.get("owners") or [])):
                errors.append(f"{rel}/case_activity.json: ризик {risk.get('id')} має категорію або відповідального поза списком")
            for key in ("hint", "feedback"):
                if len(str(risk.get(key, "")).strip()) < 20:
                    errors.append(f"{rel}/case_activity.json: ризик {risk.get('id')} без {key} або з надто коротким {key}")
        if len(str(case.get("order_hint", "")).strip()) < 20:
            errors.append(f"{rel}/case_activity.json: немає order_hint — підказки до послідовності дій")
        if not isinstance(case.get("reasoning_hint"), list) or len(case.get("reasoning_hint") or []) < 3:
            errors.append(f"{rel}/case_activity.json: reasoning_hint має містити щонайменше 3 пункти")
        aspects = case.get("reasoning_aspects")
        if not isinstance(aspects, list) or len(aspects) < 3:
            errors.append(f"{rel}/case_activity.json: reasoning_aspects має містити щонайменше 3 аспекти")
        else:
            for aspect in aspects:
                if not str(aspect.get("label", "")).strip() or not aspect.get("terms"):
                    errors.append(f"{rel}/case_activity.json: аспект пояснення без label або terms")
        if len(str(case.get("reasoning_model", "")).strip()) < int(case.get("reasoning_min_chars") or 60):
            errors.append(f"{rel}/case_activity.json: reasoning_model коротший за власний поріг reasoning_min_chars")

    checklist = load(directory / "checklist_activity.json", errors)
    if isinstance(checklist, dict):
        statuses = checklist.get("statuses") or []
        if not any(str(s.get("value", "")) == "" for s in statuses):
            errors.append(f"{rel}/checklist_activity.json: потрібен порожній стартовий статус")
        if not any(s.get("blocks_critical") for s in statuses):
            errors.append(f"{rel}/checklist_activity.json: жоден статус не позначено blocks_critical")
        for item in checklist.get("items") or []:
            for key in ("hint", "why"):
                if len(str(item.get(key, "")).strip()) < 20:
                    errors.append(f"{rel}/checklist_activity.json: пункт {item.get('id')} без {key} або з надто коротким {key}")

    practice = load(directory / "practice_activity.json", errors)
    if isinstance(practice, dict):
        allowed = {o.get("value") for o in practice.get("source_options") or []}
        for field in practice.get("fields") or []:
            name = field.get("id")
            if field.get("mode") == "known" and not (field.get("must_include") or field.get("accepted")):
                errors.append(f"{rel}/practice_activity.json: поле {name} має mode=known без must_include і без accepted")
            rules = field.get("must_include")
            if rules is not None:
                if not isinstance(rules, list) or not rules:
                    errors.append(f"{rel}/practice_activity.json: поле {name}: must_include має бути непорожнім списком груп")
                else:
                    for group in rules:
                        terms = group if isinstance(group, list) else [group]
                        if not terms or any(not str(term).strip() for term in terms):
                            errors.append(f"{rel}/practice_activity.json: поле {name}: порожня група в must_include")
            if field.get("must_not_include") is not None and not isinstance(field.get("must_not_include"), list):
                errors.append(f"{rel}/practice_activity.json: поле {name}: must_not_include має бути списком")
            for source in field.get("sources") or []:
                if source not in allowed:
                    errors.append(f"{rel}/practice_activity.json: поле {name} посилається на невідоме джерело {source}")
            for key in ("hint", "hint_where", "example"):
                if not str(field.get(key, "")).strip():
                    errors.append(f"{rel}/practice_activity.json: поле {name} без {key}")
            tight = lambda value: re.sub(r"[^\w]+", "", str(value).lower(), flags=re.UNICODE)
            for value in field.get("accepted") or []:
                if len(str(value)) > 3 and any(tight(value) in tight(step) for step in (field.get("hint_where"), field.get("example")) if step):
                    errors.append(f"{rel}/practice_activity.json: підказка поля {name} містить еталонне значення «{value}»")

    glossary = load(directory / "glossary_activity.json", errors)
    if not isinstance(glossary, list) or not glossary:
        errors.append(f"{rel}/glossary_activity.json: очікується непорожній список термінів")

    precheck = load(directory / "lesson_precheck.json", errors)
    if isinstance(precheck, list):
        if len(precheck) < 2:
            errors.append(f"{rel}/lesson_precheck.json: потрібно щонайменше 2 передперевірки до читання уроку")
        for item in precheck:
            if len(str(item.get("note", "")).strip()) < 30:
                errors.append(f"{rel}/lesson_precheck.json: передперевірка {item.get('id')} без пояснення note")
            if not isinstance(item.get("options"), list) or sum(1 for o in item.get("options") or [] if o.get("correct")) != 1:
                errors.append(f"{rel}/lesson_precheck.json: передперевірка {item.get('id')} має мати рівно одну правильну відповідь")

    glossary_terms = load(directory / "glossary_activity.json", errors)
    if isinstance(glossary_terms, list):
        for term in glossary_terms:
            if len(str(term.get("avoid", "")).strip()) < 10:
                errors.append(f"{rel}/glossary_activity.json: термін «{term.get('term')}» без поля avoid (чого не казати)")

    lesson_text = (directory / "lesson.md")
    if lesson_text.exists():
        marks = len(re.findall(r"\[SRC-\d{3}\]", lesson_text.read_text(encoding="utf-8")))
        if marks < 5:
            errors.append(f"{rel}/lesson.md: лише {marks} інлайн-посилань [SRC-NNN] — нормативні твердження мають бути підкріплені в тексті")

    if not meta.get("primary_source", {}).get("id"):
        errors.append(f"{rel}/module_meta.json: немає primary_source — першоджерела для самостійного читання")
    sessions = meta.get("sessions") or []
    if len(sessions) < 2:
        errors.append(f"{rel}/module_meta.json: модуль треба поділити щонайменше на 2 сесії")
    else:
        covered = {page for session in sessions for page in session.get("pages") or []}
        needed = {"overview", "guide", "lesson", "practice", "case", "checklist", "glossary", "reference", "sources", "quiz"}
        if needed - covered:
            errors.append(f"{rel}/module_meta.json: сесії не покривають сторінки {sorted(needed - covered)}")
    notes = meta.get("mission_notes") or {}
    for mission in (load(root / "course_meta.json", errors) or {}).get("missions") or []:
        if len(str(notes.get(mission.get("id"), "")).strip()) < 30:
            errors.append(f"{rel}/module_meta.json: немає mission_notes для мети «{mission.get('id')}»")

    lesson_activities = load(directory / "lesson_activities.json", errors)
    if lesson_activities is not None:
        check_lesson_activities(directory / "lesson_activities.json", lesson_activities, errors)
        if isinstance(lesson_activities, list):
            errors.extend(load_anticue()(lesson_activities, f"{rel}/lesson_activities.json"))

    quiz_path = root / "quizzes" / "modules" / f"{str(meta.get('id')).replace('-', '_')}_quiz.json"
    if meta.get("status") in PUBLISHED and not quiz_path.exists():
        errors.append(f"{rel}: статус {meta['status']}, але немає {quiz_path.relative_to(root)}")

    quiz = load(quiz_path, errors) if quiz_path.exists() else None
    if isinstance(quiz, list):
        for question in quiz:
            for source in question.get("source_reference") or []:
                if source not in source_ids:
                    errors.append(f"{quiz_path.relative_to(root)}: питання {question.get('id')} посилається на невідоме джерело {source}")
    return meta


def check_level_quizzes(root: Path, course: dict, metas: list[dict], source_ids: set[str], errors: list[str]) -> None:
    """Рівневий квіз: 12–15 наскрізних питань, кожне спирається на ≥2 модулі свого рівня."""
    directory = root / "quizzes" / "levels"
    if not directory.exists():
        return
    config = (course or {}).get("level_quiz") or {}
    low, high = int(config.get("min_questions") or 12), int(config.get("max_questions") or 15)
    levels = {level.get("level") for level in (course or {}).get("levels") or []}
    by_level = {}
    for meta in metas:
        by_level.setdefault(meta.get("level"), set()).add(meta.get("id"))
    for path in sorted(directory.glob("*_quiz.json")):
        rel = path.relative_to(root)
        match = re.search(r"level_(\d+)_quiz\.json$", path.name)
        if not match:
            errors.append(f"{rel}: назва має бути виду level_NN_quiz.json")
            continue
        level = int(match.group(1))
        if level not in levels:
            errors.append(f"{rel}: рівень {level} не описано в course_meta.json")
            continue
        quiz = load(path, errors)
        if not isinstance(quiz, list):
            continue
        if not low <= len(quiz) <= high:
            errors.append(f"{rel}: потрібно {low}–{high} питань, зараз {len(quiz)}")
        known = by_level.get(level, set())
        for question in quiz:
            label = f"{rel}: питання {question.get('id')}"
            modules = question.get("modules")
            if not isinstance(modules, list) or len(modules) < 2:
                errors.append(f"{label}: рівневе питання має спиратися щонайменше на два модулі — інакше це дублікат модульного квізу")
                continue
            if len(set(modules)) != len(modules):
                errors.append(f"{label}: повтор модуля у списку modules")
            for module_id in modules:
                if module_id not in known:
                    errors.append(f"{label}: модуль {module_id} не належить рівню {level} або не опубліковано")
            for source in question.get("source_reference") or []:
                if source not in source_ids:
                    errors.append(f"{label}: посилання на невідоме джерело {source}")


def run(script: Path, args: list[str], errors: list[str], root: Path) -> None:
    if not script.exists():
        errors.append(f"{script}: скрипт відсутній")
        return
    result = subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True, cwd=root)
    output = (result.stdout + result.stderr).strip()
    print(f"— {script.name} {' '.join(Path(a).name if Path(a).exists() else a for a in args)}: {output.splitlines()[0] if output else 'без виводу'}")
    if result.returncode != 0:
        errors.extend(line.strip("- ") for line in output.splitlines() if line.strip() and not line.startswith("FAIL"))
        errors.append(f"{script.name}: перевірка не пройдена")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    errors: list[str] = []

    register = root / "sources/SOURCE_REGISTER.md"
    source_ids = set(re.findall(r"\bSRC-\d{3}\b", register.read_text(encoding="utf-8"))) if register.exists() else set()
    if not source_ids:
        errors.append("sources/SOURCE_REGISTER.md: не знайдено жодного джерела SRC-NNN")

    template = root / "app/index.template.html"
    if template.exists():
        marker_count = template.read_text(encoding="utf-8").count("__COURSE_DATA__")
        if marker_count != 1:
            errors.append(f"app/index.template.html: маркерів __COURSE_DATA__ {marker_count}, потрібен рівно 1")
    else:
        errors.append("app/index.template.html: файл відсутній")

    course = load(root / "course_meta.json", errors)
    levels = {}
    if isinstance(course, dict):
        levels = {level["level"]: level for level in course.get("levels") or []}
        planned = sum(level.get("planned_modules", 0) for level in levels.values())
        if planned != course.get("planned_modules"):
            errors.append(f"course_meta.json: сума модулів по рівнях {planned} ≠ planned_modules {course.get('planned_modules')}")

    directories = sorted((root / "curriculum").glob("level_*/module_*/module_meta.json"))
    print(f"модулів знайдено: {len(directories)}")
    metas = []
    for meta_path in directories:
        meta = check_module(meta_path.parent, root, source_ids, errors)
        if meta:
            metas.append(meta)
            if meta.get("level") not in levels:
                errors.append(f"{meta_path.parent.name}: рівень {meta.get('level')} не описано в course_meta.json")

    ids = [meta.get("id") for meta in metas]
    if len(set(ids)) != len(ids):
        errors.append(f"дублікати id модулів: {sorted(i for i in ids if ids.count(i) > 1)}")

    check_level_quizzes(root, course if isinstance(course, dict) else {}, metas, source_ids, errors)

    for quiz_path in sorted((root / "quizzes/modules").glob("*_quiz.json")) + sorted((root / "quizzes/levels").glob("*_quiz.json")):
        run(root / SKILL / "validate_quiz.py", [str(quiz_path)], errors, root)
    run(root / SKILL / "check_freshness.py", [str(root)], errors, root)

    if errors:
        print("\nFAIL")
        for error in dict.fromkeys(errors):
            print(f"- {error}")
        return 1
    level_quizzes = len(list((root / "quizzes/levels").glob("*_quiz.json"))) if (root / "quizzes/levels").exists() else 0
    print(f"\nOK: модулів {len(metas)}, рівневих квізів {level_quizzes}, джерел {len(source_ids)}, помилок немає")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
