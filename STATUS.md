# Стан створення курсу

Оновлено: **2026-09-07**

Статуси: `planned → sources_collected → draft → fact_checked → human_reviewed → quiz_ready → app_ready → released`.

**Стан на 07.09.2026:** курс `0.12.0`, опубліковано 7 модулів із 38, 70 джерел у реєстрі. **Рівні 1 і 2 укомплектовано повністю**, обидва мають рівневі перевірки. Усі автоперевірки проходять. **Людської перевірки не проходив жоден модуль**; ручний прохід у браузері не проводився з версії `0.2.2`. Артефакт — 1125 КБ: прогноз розміру перераховано, поріг 2 МБ буде досягнуто близько 13-го модуля (`TASK/SCALING_PLAN.md` §8).

**Рівневі квізи.** Рівні 1 і 2 закрито, обидві рівневі перевірки створені й доступні в застосунку (`quizzes/levels/level_01_quiz.json` і `level_02_quiz.json`, по 12 наскрізних питань; людська перевірка не проводилася). Рівні 3–8 рівневих квізів не мають: вони створюються, коли всі модулі рівня доведено до `app_ready`.

| № | Рівень | Модуль | Відповідальний | Урок | Джерела | Квіз | Застосунок | Перевірено | Відкрите питання |
|---:|---:|---|---|---|---|---|---|---|---|
| 1 | 1 | Хто такий ФОП | AI + людина | fact_checked | current | quiz_ready | app_ready | 2026-08-15 | Виправлено 10 дефектів за `review/pilot_fix_register.md`; застосунок переведено на багатомодульну оболонку, перевірку відповідей за ключовими словами, підказки в Практиці й Кейсі, виконано всі пропозиції з `TASK/COURSE_EVALUATION_AND_PROPOSALS.md` (0.5.0-pilot). **Потрібна повторна людська перевірка**: переписано формулювання варіантів квізу й двох дистракторів кейсу. Далі — ручне відкриття `index.html` через `file://` |
| 2 | 1 | Фінансова грамотність | AI + бухгалтер/юрист | fact_checked | current | quiz_ready | app_ready | 2026-08-24 | Створено за `TASK/MODULE_02_TECHNICAL_ASSIGNMENT.md` без жодної правки `app/index.template.html` і `scripts/build_course.py`. **Людська перевірка не проведена** — запит і три відкриті питання в `review/module_02_human_review.md`. Наступна перевірка джерел — 01.11.2026 (призначено нову редакцію ПКУ) |
| 3 | 1 | Податкові системи | AI + бухгалтер | fact_checked | current | quiz_ready | app_ready | 2026-08-25 | Створено за `TASK/MODULE_03_TECHNICAL_ASSIGNMENT.md` без правок інфраструктури; рівень 1 укомплектовано. **Людська перевірка не проведена** — пʼять відкритих питань у `review/module_03_human_review.md`. Наступна перевірка джерел — 01.11.2026 |
| 4 | 2 | Документування господарської операції | AI + бухгалтер | fact_checked | current | quiz_ready | app_ready | 2026-09-06 | Створено за `TASK/MODULE_04_TECHNICAL_ASSIGNMENT.md` без правок інфраструктури; перший модуль рівня 2. **Людська перевірка не проведена** — чотири відкриті питання в `review/module_04_human_review.md`, головне: перелік обовʼязкових реквізитів адресовано юридичним особам, а не ФОП. Наступна перевірка джерел — 01.11.2026 |
| 5 | 2 | Основні види документів | AI + бухгалтер | fact_checked | current | quiz_ready | app_ready | 2026-09-06 | Створено за `TASK/MODULE_05_TECHNICAL_ASSIGNMENT.md` без правок інфраструктури. **Людська перевірка не проведена** — три відкриті питання в `review/module_05_human_review.md`, головне: статус рахунку-фактури спирається на розʼяснення Мінфіну 2006 року, а не на норму. Наступна перевірка джерел — 01.11.2026 |
| 6 | 2 | Договори | AI + юрист | fact_checked | current | quiz_ready | app_ready | 2026-09-06 | Створено за `TASK/MODULE_06_TECHNICAL_ASSIGNMENT.md` без правок інфраструктури. **Юридична перевірка не проведена** і є обовʼязковою для цього модуля — три відкриті питання в `review/module_06_human_review.md`, головне: доля договорів із посиланнями на скасований Господарський кодекс. Наступна перевірка джерел — 01.11.2026 |
| 7 | 2 | Електронний архів | AI + людина | fact_checked | current | quiz_ready | app_ready | 2026-09-07 | Створено за `TASK/MODULE_07_TECHNICAL_ASSIGNMENT.md`; **рівень 2 укомплектовано**. Людська перевірка не проведена — чотири відкриті питання в `review/module_07_human_review.md`, головне: строк 1095 днів для ФОП досі є висновком методом виключення (тягнеться з модуля 2). Наступна перевірка джерел — 01.11.2026 |
| 8 | 3 | Банківський рахунок ФОП | AI + бухгалтер | planned | needs_review | not_started | not_started | — | — |
| 9 | 3 | Класифікація операцій | AI + бухгалтер | planned | needs_review | not_started | not_started | — | — |
| 10 | 3 | Готівка, РРО і ПРРО | AI + бухгалтер | planned | needs_review | not_started | not_started | — | — |
| 11 | 4 | Єдиний податок | AI + бухгалтер | planned | needs_review | not_started | not_started | — | — |
| 12 | 4 | ЄСВ і військовий збір | AI + бухгалтер | planned | needs_review | not_started | not_started | — | Перетин із `TASK/what_is_happening_after_FOP_closed.md` (ЄСВ після припинення) |
| 13 | 4 | Податковий агент і 4ДФ | AI + бухгалтер | planned | needs_review | not_started | not_started | — | — |
| 14 | 4 | Наймані працівники | AI + бухгалтер | planned | needs_review | not_started | not_started | — | — |
| 15 | 4 | ПДВ | AI + бухгалтер | planned | needs_review | not_started | not_started | — | — |
| 16 | 4 | Майнові податки | AI + бухгалтер | planned | needs_review | not_started | not_started | — | — |
| 17 | 4 | Валютні операції | AI + бухгалтер | planned | needs_review | not_started | not_started | — | — |
| 18 | 5 | Податковий календар | AI + бухгалтер | planned | needs_review | not_started | not_started | — | — |
| 19 | 5 | Декларація платника єдиного податку | AI + бухгалтер | planned | needs_review | not_started | not_started | — | — |
| 20 | 5 | Робота в Електронному кабінеті | AI + бухгалтер | planned | needs_review | not_started | not_started | — | — |
| 21 | 5 | Стан розрахунків із бюджетом | AI + бухгалтер | planned | needs_review | not_started | not_started | — | — |
| 22 | 5 | Перевірки й оскарження | AI + юрист | planned | needs_review | not_started | not_started | — | Врахувати `TASK/what_is_happening_after_FOP_closed.md` (перевірка після припинення ФОП) — сировина, потребує офіційних джерел |
| 23 | 6 | Відкриття нового клієнта | AI + бухгалтер | planned | needs_review | not_started | not_started | — | — |
| 24 | 6 | Щомісячне закриття | AI + бухгалтер | planned | needs_review | not_started | not_started | — | — |
| 25 | 6 | Квартальне і річне закриття | AI + бухгалтер | planned | needs_review | not_started | not_started | — | — |
| 26 | 6 | Внутрішній контроль | AI + бухгалтер | planned | needs_review | not_started | not_started | — | — |
| 27 | 7 | Excel і Google Sheets | AI + людина | planned | needs_review | not_started | not_started | — | Врахувати `TASK/what_is_different_csv_xls_xlsx.md` (CSV/XLS/XLSX, вибір формату) |
| 28 | 7 | OCR і електронні документи | AI + людина | planned | needs_review | not_started | not_started | — | Перетин із `TASK/what_is_different_csv_xls_xlsx.md` (обмін даними з обліковою системою) |
| 29 | 7 | Бухгалтерські програми | AI + бухгалтер | planned | needs_review | not_started | not_started | — | — |
| 30 | 7 | Банківські інтеграції й open banking | AI + людина | planned | needs_review | not_started | not_started | — | — |
| 31 | 7 | AI-помічник бухгалтера | AI + людина | planned | needs_review | not_started | not_started | — | — |
| 32 | 7 | Автоматизація і програмування | AI + людина | planned | needs_review | not_started | not_started | — | — |
| 33 | 7 | Аналітика | AI + бухгалтер | planned | needs_review | not_started | not_started | — | — |
| 34 | 7 | Кібербезпека | AI + людина | planned | needs_review | not_started | not_started | — | — |
| 35 | 8 | Управління кількома ФОП | AI + бухгалтер | planned | needs_review | not_started | not_started | — | — |
| 36 | 8 | Складні ситуації | AI + бухгалтер/юрист | planned | needs_review | not_started | not_started | — | — |
| 37 | 8 | Професійна етика | AI + бухгалтер | planned | needs_review | not_started | not_started | — | — |
| 38 | 8 | Моніторинг законодавства | AI + бухгалтер/юрист | planned | needs_review | not_started | not_started | — | — |
