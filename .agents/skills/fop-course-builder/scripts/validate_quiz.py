#!/usr/bin/env python3
"""Перевіряє JSON-квіз курсу ФОП."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path



MARKER_WORDS = ("ніколи", "завжди", "повністю", "лише", "тільки", "автоматично", "одразу", "достатньо", "усі ", "всі ")
MAX_LENGTH_RATIO = 1.4          # найдовший варіант питання / найкоротший
MAX_LONGEST_SHARE = 0.4         # частка питань, де правильна відповідь найдовша
MAX_POSITION_SHARE = 0.5        # частка питань, де правильна відповідь на одній позиції
MAX_POSITION_RUN = 3            # поспіль однакова позиція правильної відповіді
MAX_MARKER_GAP = 0.35           # наскільки частіше маркерні слова трапляються в дистракторах
MAX_BLIND_SCORE = 0.4           # результат стратегії «не читаю умову»


def has_marker(text: str) -> bool:
    lowered = f" {str(text).casefold()} "
    return any(word in lowered for word in MARKER_WORDS)


def blind_pick(options: list) -> int:
    """Стратегія тестового шахрая: викинути варіанти з маркерними словами, з решти взяти найдовший."""
    clean = [index for index, option in enumerate(options) if not has_marker(option.get("text", ""))]
    pool = clean if len(clean) == 1 else (clean or list(range(len(options))))
    return max(pool, key=lambda index: len(str(options[index].get("text", ""))))


def anticue_errors(items: list, label: str = "набір") -> list[str]:
    """Перевіряє, чи не видають варіанти правильну відповідь формою, а не змістом."""
    errors: list[str] = []
    usable = [item for item in items if isinstance(item, dict) and isinstance(item.get("options"), list) and len(item["options"]) >= 2]
    if not usable:
        return errors
    positions, longest, blind, marker_correct, marker_wrong, options_total = [], 0, 0, 0, 0, 0
    for number, item in enumerate(usable, 1):
        options = item["options"]
        lengths = [len(str(option.get("text", ""))) for option in options]
        correct = next((index for index, option in enumerate(options) if option.get("correct") is True), None)
        if correct is None:
            continue
        if min(lengths) and max(lengths) / min(lengths) > MAX_LENGTH_RATIO:
            errors.append(
                f"{label}, питання {number}: варіанти надто різні за довжиною ({lengths}) — "
                f"довжина підказує відповідь; тримайте розкид до {MAX_LENGTH_RATIO}×"
            )
        positions.append(correct)
        if lengths[correct] == max(lengths):
            longest += 1
        if options[blind_pick(options)].get("correct") is True:
            blind += 1
        for index, option in enumerate(options):
            options_total += 1
            if has_marker(option.get("text", "")):
                if index == correct:
                    marker_correct += 1
                else:
                    marker_wrong += 1

    total = len(positions)
    if not total:
        return errors
    if longest / total > MAX_LONGEST_SHARE:
        errors.append(
            f"{label}: правильна відповідь найдовша у {longest} із {total} питань — "
            f"допустимо не більше {int(MAX_LONGEST_SHARE * 100)}%"
        )
    counts = Counter(positions)
    top_position, top_count = counts.most_common(1)[0]
    if total >= 4 and top_count / total > MAX_POSITION_SHARE:
        errors.append(
            f"{label}: правильна відповідь стоїть на позиції {top_position + 1} у {top_count} із {total} питань — "
            f"розкидайте позиції"
        )
    run = best = 1
    for previous, current in zip(positions, positions[1:]):
        run = run + 1 if current == previous else 1
        best = max(best, run)
    if best > MAX_POSITION_RUN:
        errors.append(f"{label}: {best} питань поспіль мають правильну відповідь на одній позиції")
    correct_rate = marker_correct / total
    wrong_rate = marker_wrong / max(options_total - total, 1)
    if wrong_rate - correct_rate > MAX_MARKER_GAP:
        errors.append(
            f"{label}: слова на кшталт «ніколи/завжди/лише/автоматично» трапляються в дистракторах "
            f"({marker_wrong}) значно частіше, ніж у правильних відповідях ({marker_correct}) — "
            f"їх наявність стає підказкою"
        )
    if blind / total > MAX_BLIND_SCORE:
        errors.append(
            f"{label}: стратегія «не читати умову, взяти найдовший варіант без абсолютних слів» дає "
            f"{blind} із {total} ({round(blind / total * 100)}%) — питання розв’язуються за формою, а не за змістом"
        )
    return errors

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("quiz", type=Path)
    args = parser.parse_args()

    try:
        data = json.loads(args.quiz.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 1

    questions = data if isinstance(data, list) else data.get("questions", [])
    errors: list[str] = []
    positions: Counter[int] = Counter()
    titles: set[str] = set()

    if not questions:
        errors.append("немає питань")

    for number, item in enumerate(questions, 1):
        label = f"питання {number}"
        if not isinstance(item, dict):
            errors.append(f"{label}: очікується об'єкт")
            continue
        title = str(item.get("title", "")).strip()
        question = str(item.get("question", "")).strip()
        scenario = str(item.get("scenario", "")).strip()
        competency = str(item.get("competency", "")).strip()
        options = item.get("options")
        explanation = str(item.get("explanation", "")).strip()
        hint = str(item.get("hint", "")).strip()
        sources = item.get("source_reference")

        if not title:
            errors.append(f"{label}: немає title")
        elif title.casefold() in titles:
            errors.append(f"{label}: дублікат title")
        titles.add(title.casefold())
        if len(question) < 5:
            errors.append(f"{label}: надто короткий question")
        if len(scenario) < 20:
            errors.append(f"{label}: scenario відсутній або надто короткий")
        if not competency:
            errors.append(f"{label}: немає competency")
        if not isinstance(options, list) or len(options) != 3:
            errors.append(f"{label}: options має містити рівно 3 варіанти")
            continue
        if not all(isinstance(option, dict) for option in options):
            errors.append(f"{label}: кожен варіант має бути об'єктом із text, correct і feedback")
            continue
        normalized = [str(option.get("text", "")).strip().casefold() for option in options]
        if any(not option for option in normalized):
            errors.append(f"{label}: є порожній варіант")
        if len(set(normalized)) != 3:
            errors.append(f"{label}: варіанти повторюються")
        correct_indexes = [index for index, option in enumerate(options) if option.get("correct") is True]
        if len(correct_indexes) != 1:
            errors.append(f"{label}: має бути рівно одна правильна відповідь")
        else:
            positions[correct_indexes[0]] += 1
        for option_number, option in enumerate(options, 1):
            feedback = str(option.get("feedback", "")).strip()
            if len(feedback) < 20:
                errors.append(f"{label}, варіант {option_number}: feedback відсутній або надто короткий")
        if len(explanation) < 30:
            errors.append(f"{label}: explanation відсутній або надто короткий")
        if len(hint) < 20:
            errors.append(f"{label}: hint відсутній або надто короткий — потрібне навідне питання для кнопки «Підказка»")
        else:
            tight = lambda value: "".join(ch for ch in str(value).casefold() if ch.isalnum())
            correct_text = next((option.get("text", "") for option in options if option.get("correct") is True), "")
            if correct_text and tight(correct_text) and tight(correct_text) in tight(hint):
                errors.append(f"{label}: hint містить правильну відповідь")
        if not isinstance(sources, list) or not sources or any(not str(source).strip() for source in sources):
            errors.append(f"{label}: source_reference має бути непорожнім списком")

    errors.extend(anticue_errors(questions, "квіз"))

    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"OK: питань {len(questions)}; правильні позиції {dict(sorted(positions.items()))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
