// Перевірка логіки зібраного застосунку без браузера:
// витягує вбудований JSON і скрипт із dist/index.html, підставляє мінімальні заглушки DOM
// і перевіряє курсову оболонку, рендер усіх сторінок, оцінювання, пороги, прогрес
// та відсутність зовнішніх запитів.
// Запуск: node tests/logic_smoke.mjs [шлях/до/index.html]

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const target = process.argv[2] ? resolve(process.argv[2]) : resolve(root, "dist/index.html");
const html = readFileSync(target, "utf8");
const dataMatch = html.match(/<script id="course-data" type="application\/json">([\s\S]*?)<\/script>/);
const scriptMatch = html.match(/<script>\s*"use strict";([\s\S]*?)<\/script>/);
if (!dataMatch || !scriptMatch) throw new Error("не знайдено дані або скрипт");
const payloadText = dataMatch[1];

function node(id = "") {
  const n = {
    id,
    _html: "",
    style: {},
    classList: { add() {}, remove() {}, contains: () => false },
    dataset: {},
    disabled: false,
    textContent: "",
    className: "",
    type: "",
    value: "",
    set innerHTML(v) { this._html = String(v); },
    get innerHTML() { return this._html; },
    setAttribute() {},
    getAttribute: () => null,
    appendChild: (c) => c,
    append() {},
    insertAdjacentHTML() {},
    addEventListener() {},
    removeEventListener() {},
    focus() {},
    querySelector: () => node(),
    querySelectorAll: () => [node(), node(), node()],
    closest: () => null,
  };
  return n;
}

const store = new Map();
const stubs = {
  document: {
    getElementById: (id) => (id === "course-data" ? { textContent: payloadText } : node(id)),
    querySelector: () => node(),
    querySelectorAll: () => [],
    createElement: () => node(),
    title: "",
  },
  localStorage: {
    get length() { return store.size; },
    key: (i) => [...store.keys()][i] ?? null,
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, v),
    removeItem: (k) => store.delete(k),
  },
  window: { scrollTo() {} },
  confirm: () => true,
};

const exposed = `;globalThis.__api={get state(){return state},set state(v){state=v},get view(){return view},set view(v){view=v},get current(){return current},set current(v){current=v},get mod(){return mod},get ms(){return ms},COURSE,MODULES,PAGES,STORAGE_KEY,STATE_VERSION,weights,quizThreshold,noteMin,reasonMin,blockingStatuses,startOrder,freshState,freshModuleState,stateOf,peekState,openModule,openCourse,neighbour,resetModule,resetCourse,checkPractice,checkCase,moveTo,orderVerdict,caseHintLevel,raiseCaseHint,matches,normalize,words,compact,hintSteps,hintLevel,raiseHint,hintsUsed,lessonDone,practiceDone,caseDone,checklistDone,checklistItemValid,checklistIssue,checklistHintLevel,raiseChecklistHint,quizHintLevel,raiseQuizHint,quizHintsUsed,quizDone,quizPercent,glossaryDone,pageDone,progressOf,courseProgress,completedModules,render,go,correctIndex,legacyKeys,reviewAdd,reviewDrop,reviewAll,reviewDue,reviewPass,reviewFail,reviewContent,reviewStore,todayISO,addDays,REVIEW,missionById,sessionOf,openReview};`;

const fn = new Function(...Object.keys(stubs), `"use strict";${scriptMatch[1]}${exposed}`);
fn(...Object.values(stubs));
const api = globalThis.__api;

let failures = 0;
const check = (name, cond, extra = "") => {
  if (cond) console.log(`OK   ${name}${extra ? " — " + extra : ""}`);
  else { failures++; console.log(`FAIL ${name}${extra ? " — " + extra : ""}`); }
};

// 1. Курсова оболонка
check("стартовий вид — список модулів", api.view === "course");
check("є принаймні один модуль", api.MODULES.length >= 1, `${api.MODULES.length} модулів`);
check("модулі відсортовані за рівнем і номером",
  api.MODULES.every((m, i, all) => i === 0 || all[i - 1].level < m.level || (all[i - 1].level === m.level && all[i - 1].index < m.index)));
check("рівні курсу описані", Array.isArray(api.COURSE.levels) && api.COURSE.levels.length === 8, `${api.COURSE.levels?.length} рівнів`);
check("сума запланованих модулів по рівнях = planned_modules",
  api.COURSE.levels.reduce((s, l) => s + l.planned_modules, 0) === api.COURSE.planned_modules,
  String(api.COURSE.planned_modules));
check("кожен опублікований модуль належить описаному рівню",
  api.MODULES.every((m) => api.COURSE.levels.some((l) => l.level === m.level)));
check("підсумкова атестація позначена як запланована", api.COURSE.final_assessment.status === "planned");
try { api.render(); check("render:курс", true); } catch (e) { check("render:курс", false, e.message); }

// 2. Рендер усіх сторінок кожного модуля
for (const m of api.MODULES) {
  api.openModule(m.id);
  for (const p of api.PAGES) {
    try { api.current = p.id; api.render(); check(`render:${m.id}/${p.id}`, true); }
    catch (e) { check(`render:${m.id}/${p.id}`, false, e.message); }
  }
}

// 3. Порожній стан
api.state = api.freshState();
api.openModule(api.MODULES[0].id);
const mod = api.mod;
check("порожній модуль → 0%", api.progressOf(mod, api.ms) === 0);
check("порожній курс → 0%", api.courseProgress() === 0);
check("завершених модулів 0", api.completedModules() === 0);

// 4. Кейс: початковий порядок не є відповіддю
const actions = mod.activities.case.actions.map((a) => a.id);
check("початковий порядок кейсу ≠ правильний", JSON.stringify(api.ms.caseWork.order) !== JSON.stringify(actions), api.ms.caseWork.order.join(","));
check("жодна дія не стоїть одразу на правильному місці", api.ms.caseWork.order.filter((id, i) => id === actions[i]).length === 0);
api.checkCase();
check("кейс без роботи < порогу", api.ms.caseWork.result.percent < mod.activities.case.threshold, `${api.ms.caseWork.result.percent}%`);

// 4.1 Кейс: підказки, перетягування, поетапні пояснення
const caseData = mod.activities.case;
check("кожен ризик має навідне питання", caseData.risks.every((r) => String(r.hint || "").length > 20));
check("є підказка до послідовності", String(caseData.order_hint || "").length > 20);
check("є підказка до пояснення", Array.isArray(caseData.reasoning_hint) && caseData.reasoning_hint.length >= 3);
check("є аспекти пояснення", Array.isArray(caseData.reasoning_aspects) && caseData.reasoning_aspects.every((a) => a.label && a.terms?.length));
check("є орієнтир для самоперевірки", String(caseData.reasoning_model || "").length >= caseData.reasoning_min_chars);
check("підказка ризику не називає відповіді",
  caseData.risks.every((r) => !/\bце ризик\b|\bне ризик\b|обов'?язково познач/i.test(r.hint)));

const wrongRisk = caseData.risks.find((r) => !r.critical);
const rightRisk = caseData.risks.find((r) => r.critical);
api.ms.caseWork.selected[wrongRisk.id] = true;
api.ms.caseWork.selected[rightRisk.id] = true;
api.ms.caseWork.categories[rightRisk.id] = rightRisk.category;
api.ms.caseWork.owners[rightRisk.id] = "хтось інший";
api.checkCase();
const verdicts = api.ms.caseWork.result.risks;
check("вердикт є для кожного ризику", Object.keys(verdicts).length === caseData.risks.length);
check("зайвий вибір позначено помилкою", verdicts[wrongRisk.id].ok === false && /не ризик/i.test(verdicts[wrongRisk.id].message));
check("неправильний відповідальний названо окремо", /Відповідального/.test(verdicts[rightRisk.id].message));
check("пропущений ризик названо окремо",
  caseData.risks.filter((r) => r.critical && r.id !== rightRisk.id).every((r) => /справжній ризик/i.test(verdicts[r.id].message)));
check("вердикт порядку — масив по позиціях",
  Array.isArray(api.ms.caseWork.result.order) && api.ms.caseWork.result.order.length === caseData.actions.length);
check("перемішаний порядок дає всі позиції хибними", api.ms.caseWork.result.order.every((hit) => hit === false));

check("живий вердикт порядку доступний до перевірки", api.orderVerdict().length === caseData.actions.length);
check("перемішаний старт: жодної зеленої картки", api.orderVerdict().every((hit) => hit === false));
api.ms.caseWork.order = caseData.actions.map((a) => a.id);
check("правильний порядок: усі картки зелені живцем", api.orderVerdict().every(Boolean));
api.moveTo(0, 1);
check("після перестановки колір оновлюється миттєво",
  api.orderVerdict().filter(Boolean).length === caseData.actions.length - 2,
  api.orderVerdict().map((h) => (h ? "✓" : "—")).join(""));
api.ms.caseWork.order = caseData.initial_order.slice();
api.ms.caseWork.result = null;

const before = api.ms.caseWork.order.slice();
api.moveTo(0, 2);
check("перетягування переставляє картку",
  api.ms.caseWork.order[2] === before[0] && api.ms.caseWork.order.length === before.length,
  api.ms.caseWork.order.join(","));
check("переміщення скидає попередній результат", api.ms.caseWork.result === null);
api.moveTo(2, 0);
check("повернення на місце відновлює порядок", JSON.stringify(api.ms.caseWork.order) === JSON.stringify(before));
api.moveTo(0, 99);
check("некоректне перетягування ігнорується", JSON.stringify(api.ms.caseWork.order) === JSON.stringify(before));

check("підказка кейсу закрита за замовчуванням", api.caseHintLevel(rightRisk.id) === 0);
api.raiseCaseHint(rightRisk.id);
api.raiseCaseHint("__order");
api.raiseCaseHint("__reasoning");
check("підказки кейсу відкриваються", api.caseHintLevel(rightRisk.id) === 1 && api.caseHintLevel("__order") === 1);

api.state = api.freshState();
api.openModule(api.MODULES[0].id);

// 5. Проходження модуля до 100%
const ms = api.ms;
mod.activities.lesson.forEach((q) => { ms.lessonAnswers[q.id] = api.correctIndex(q); });
ms.caseWork.order = actions.slice();
mod.activities.case.risks.forEach((r) => {
  ms.caseWork.selected[r.id] = Boolean(r.critical);
  if (r.critical) { ms.caseWork.categories[r.id] = r.category; ms.caseWork.owners[r.id] = r.owner; }
});
ms.caseWork.reasoning = "Запис у ЄДР закриває реєстрацію, але не звітні, податкові, договірні та банківські обов'язки, які треба перевірити окремо.";
api.checkCase();
for (const f of mod.activities.practice.fields) {
  ms.practice.answers[f.id] = f.mode === "known"
    ? { value: f.accepted[0], source: f.sources[0], missing: false }
    : { value: "", source: f.sources[0], missing: true };
}
api.checkPractice();
mod.activities.checklist.items.forEach((item) => { ms.checklist[item.id] = { status: "confirmed", note: "Виписка ЄДР від 05.08.2026" }; });
mod.quiz.forEach((q, i) => { ms.quiz.answers[i] = api.correctIndex(q); });
ms.quiz.showResult = true;
check("еталонна практика = 100%", ms.practice.result.percent === 100, `${ms.practice.result.percent}%`);
check("правильний кейс = 100%", ms.caseWork.result.percent === 100, `${ms.caseWork.result.percent}%`);
check("усі позиції порядку зелені", ms.caseWork.result.order.every(Boolean));
check("усі ризики з правильним вердиктом", Object.values(ms.caseWork.result.risks).every((v) => v.ok));
check("аспекти пояснення розпізнано", ms.caseWork.result.aspects.filter((a) => a.covered).length >= 3,
  ms.caseWork.result.aspects.map((a) => `${a.label}:${a.covered ? "✓" : "—"}`).join(" "));
const emptyAspects = mod.activities.case.reasoning_aspects.length;
check("порожнє пояснення не зараховує жодного аспекту", emptyAspects > 0);
check("модуль пройдено на 100%", api.progressOf(mod, ms) === 100, `${api.progressOf(mod, ms)}%`);
check("модуль зарахований у завершені", api.completedModules() === 1);
check("прогрес курсу = середнє по модулях",
  api.courseProgress() === Math.round(100 / api.MODULES.length), `${api.courseProgress()}%`);

// 6. Ізоляція стану між модулями
if (api.MODULES.length > 1) {
  const other = api.MODULES.find((m) => m.id !== mod.id);
  check("інший модуль лишився на 0%", api.progressOf(other, api.peekState(other.id)) === 0);
  api.openModule(other.id);
  check("перемикання модуля змінює активний стан", api.mod.id === other.id && api.ms !== ms);
  check("порядок кейсу іншого модуля власний", JSON.stringify(api.ms.caseWork.order) === JSON.stringify(api.startOrder(other)));
  api.openModule(mod.id);
  check("повернення до модуля зберігає його прогрес", api.progressOf(api.mod, api.ms) === 100);
  check("сусідній модуль знайдено", Boolean(api.neighbour(1) || api.neighbour(-1)));
}

// 7. Збереження й відновлення стану
const saved = stubs.localStorage.getItem(api.STORAGE_KEY);
check("стан збережено в localStorage", Boolean(saved), api.STORAGE_KEY);
check("ключ стану версії v4", /:v4$/.test(api.STORAGE_KEY));
const parsed = JSON.parse(saved);
check("збережено стан кожного відкритого модуля", Boolean(parsed.modules[mod.id]));
check("версія стану у сховищі збігається", parsed.version === api.STATE_VERSION);

// 8. Скидання прогресу
api.resetModule();
check("скидання модуля обнуляє його прогрес", api.progressOf(api.mod, api.ms) === 0);
check("скидання модуля відновлює перемішаний порядок", JSON.stringify(api.ms.caseWork.order) === JSON.stringify(api.startOrder(api.mod)));
api.resetCourse();
check("скидання курсу обнуляє все", api.courseProgress() === 0 && api.completedModules() === 0);

// 9. Практика: толерантність і діагностичні повідомлення
const accept = [
  ["name", "Олена  Прикладенко "],
  ["main_kved", "7410"],
  ["main_kved", "КВЕД 74.10"],
  ["tax_address", "м.Полтава"],
  ["tax_address", "Полтава"],
  ["vat", "Не є платником ПДВ!"],
  ["vat", "без ПДВ"],
  ["tax_group", "третя група єдиного податку, без ПДВ"],
  ["tax_group", "3 група"],
  ["tax_group", "єдиний податок, третя група"],
  ["registration_state", "Активний"],
  ["registration_state", "зареєстровано"],
  ["registration_date", "05.08.2026"],
  ["registration_date", "запис від 05.08.2026"],
];
const reject = [
  ["tax_group", "друга група"],
  ["tax_group", "загальна система"],
  ["tax_group", "третя"],
  ["main_kved", "62.01"],
  ["extra_kved", "74.10"],
  ["tax_address", "Львів"],
  ["registration_state", "припинено"],
  ["vat", "платник ПДВ"],
  ["registration_date", "01.01.2020"],
  ["name", ""],
];
for (const [id, value] of accept) {
  const field = api.MODULES[0].activities.practice.fields.find((f) => f.id === id);
  if (field) check(`приймається: ${id}="${value}"`, api.matches(field, value));
}
for (const [id, value] of reject) {
  const field = api.MODULES[0].activities.practice.fields.find((f) => f.id === id);
  if (field) check(`відхиляється: ${id}="${value}"`, !api.matches(field, value));
}

// 9.1 Підказки: два рівні, без впливу на бал
api.state = api.freshState();
api.openModule(api.MODULES[0].id);
const hinted = api.mod.activities.practice.fields.find((f) => api.hintSteps(f).length === 2);
check("у полів є дворівнева підказка", Boolean(hinted));
const leaking = api.mod.activities.practice.fields.filter((f) =>
  (f.accepted || []).some((v) => String(v).length > 3 && api.hintSteps(f).some((step) => api.compact(step).includes(api.compact(v)))));
check("жодна підказка не містить еталонного значення", leaking.length === 0, leaking.map((f) => f.id).join(", "));
check("підказка не відкрита за замовчуванням", api.hintLevel(hinted.id) === 0);
api.raiseHint(hinted);
check("перший клік відкриває «де шукати»", api.hintLevel(hinted.id) === 1);
api.raiseHint(hinted);
check("другий клік відкриває формат", api.hintLevel(hinted.id) === 2);
api.raiseHint(hinted);
check("більше рівнів немає", api.hintLevel(hinted.id) === 2);
for (const f of api.mod.activities.practice.fields) {
  api.ms.practice.answers[f.id] = f.mode === "known"
    ? { value: f.accepted[0], source: f.sources[0], missing: false }
    : { value: "", source: f.sources[0], missing: true };
}
api.checkPractice();
check("підказки не зменшують бал", api.ms.practice.result.percent === 100, `${api.ms.practice.result.percent}%`);
check("кількість підказок показана в результаті", api.ms.practice.result.hints === 1, String(api.ms.practice.result.hints));
check("кожне поле має де шукати і приклад", api.mod.activities.practice.fields.every((f) => api.hintSteps(f).length === 2));

api.state = api.freshState();
api.openModule(api.MODULES[0].id);
const known = api.mod.activities.practice.fields.find((f) => f.mode === "known");
const absent = api.mod.activities.practice.fields.find((f) => f.mode !== "known");
api.ms.practice.answers[known.id] = { value: known.accepted[0], source: "", missing: false };
api.ms.practice.answers[absent.id] = { value: "вигаданий номер", source: absent.sources[0], missing: false };
api.checkPractice();
const d1 = api.ms.practice.result.details.find((d) => d.id === known.id);
const d2 = api.ms.practice.result.details.find((d) => d.id === absent.id);
check("правильне значення + порожнє джерело → повідомлення про джерело", /Не вибрано джерело/.test(d1.message), d1.message.slice(0, 60));
check("вигадане значення в полі без даних → окреме повідомлення", /приберіть введений текст/.test(d2.message), d2.message.slice(0, 60));
api.ms.practice.answers[known.id] = { value: known.accepted[0], source: api.mod.activities.practice.source_options.find((o) => !known.sources.includes(o.value)).value, missing: false };
api.checkPractice();
check("неправильне джерело → своє повідомлення", /вибрано не те/.test(api.ms.practice.result.details.find((d) => d.id === known.id).message));
api.ms.practice.answers[known.id] = { value: known.accepted[0], source: known.sources[0], missing: true };
api.checkPractice();
check("правильне значення + зайва позначка → підказує зняти позначку",
  /приберіть позначку/.test(api.ms.practice.result.details.find((d) => d.id === known.id).message),
  api.ms.practice.result.details.find((d) => d.id === known.id).message.slice(0, 70));

// 10. Чекліст
api.ms.checklist = {};
const critical = api.mod.activities.checklist.items.find((i) => i.critical);
const blocking = [...api.blockingStatuses(api.mod)][0];
api.ms.checklist[critical.id] = { status: blocking, note: "причина відсутня" };
check("критичний пункт не закривається блокуючим статусом", !api.checklistItemValid(api.mod, api.ms, critical), `status=${blocking}`);
api.ms.checklist[critical.id] = { status: "confirmed", note: "ЄД" };
check("коротка примітка не приймається", !api.checklistItemValid(api.mod, api.ms, critical));
api.ms.checklist[critical.id] = { status: "confirmed", note: "Виписка ЄДР від 05.08.2026" };
check("обґрунтований статус приймається", api.checklistItemValid(api.mod, api.ms, critical));

// 10.1 Чекліст: підказки, «навіщо це» і точні повідомлення
const clData = api.mod.activities.checklist;
check("кожен пункт чекліста має підказку", clData.items.every((i) => String(i.hint || "").length > 20));
check("кожен пункт має пояснення «навіщо»", clData.items.every((i) => String(i.why || "").length > 20));
check("поріг обґрунтування піднято", api.noteMin(api.mod) >= 10, String(api.noteMin(api.mod)));
api.ms.checklist = {};
check("без статусу — просять вибрати статус", /Виберіть статус/.test(api.checklistIssue(api.mod, api.ms, critical)));
api.ms.checklist[critical.id] = { status: blocking, note: "довге обґрунтування причини" };
check("блокуючий статус на критичному — своє повідомлення",
  /не можна закрити цим статусом/.test(api.checklistIssue(api.mod, api.ms, critical)));
api.ms.checklist[critical.id] = { status: "confirmed", note: "ЄДР" };
check("коротке обґрунтування — просять доповнити",
  /щонайменше з \d+ символів/.test(api.checklistIssue(api.mod, api.ms, critical)),
  api.checklistIssue(api.mod, api.ms, critical));
api.ms.checklist[critical.id] = { status: "confirmed", note: "Виписка ЄДР від 05.08.2026" };
check("опрацьований пункт не має зауважень", api.checklistIssue(api.mod, api.ms, critical) === "");
check("підказка чекліста закрита за замовчуванням", api.checklistHintLevel(critical.id) === 0);
api.raiseChecklistHint(critical.id);
check("підказка чекліста відкривається", api.checklistHintLevel(critical.id) === 1);
check("підказка чекліста не диктує статус",
  clData.items.every((i) => !/оберіть «підтверджено»|постав(те|ити) підтверджено/i.test(i.hint)));

// 10.2 Квіз: підказки й розбір помилок
check("кожне питання квізу має навідне питання", api.mod.quiz.every((q) => String(q.hint || "").length > 20));
check("підказка квізу не містить правильної відповіді",
  api.mod.quiz.every((q) => {
    const right = q.options.find((o) => o.correct).text;
    return !api.compact(q.hint).includes(api.compact(right));
  }));
api.state = api.freshState();
api.openModule(api.MODULES[0].id);
check("підказки квізу закриті за замовчуванням", api.quizHintsUsed() === 0);
api.raiseQuizHint(0);
api.raiseQuizHint(3);
check("підказки квізу відкриваються", api.quizHintLevel(0) === 1 && api.quizHintLevel(3) === 1);
check("лічильник підказок квізу рахує", api.quizHintsUsed() === 2);
api.mod.quiz.forEach((q, i) => { api.ms.quiz.answers[i] = api.correctIndex(q); });
api.ms.quiz.showResult = true;
check("підказки квізу не зменшують результат", api.quizPercent(api.mod, api.ms) === 100 && api.quizDone(api.mod, api.ms));
api.ms.quiz = { answers: {}, index: 0, showResult: false, bestScore: 10, hints: {} };
check("повторна спроба скидає підказки квізу", api.quizHintsUsed() === 0);

// 11. Глосарій не впливає на прогрес
api.ms.glossary = { seen: {}, repeat: {} };
api.mod.activities.glossary.forEach((_, i) => { api.ms.glossary.seen[i] = true; });
check("усі картки відкрито → крок виконано", api.glossaryDone(api.mod, api.ms));
api.ms.glossary.seen[0] = false;
check("схована картка знімає виконання", !api.glossaryDone(api.mod, api.ms));

// 12. Квіз
api.state = api.freshState();
api.openModule(api.MODULES[0].id);
api.mod.quiz.forEach((q, i) => { api.ms.quiz.answers[i] = api.correctIndex(q); });
api.ms.quiz.showResult = true;
check("100% квізу зараховано", api.quizDone(api.mod, api.ms), `${api.quizPercent(api.mod, api.ms)}%`);
for (let i = 0; i < Math.ceil(api.mod.quiz.length * 0.3); i++) {
  api.ms.quiz.answers[i] = (api.correctIndex(api.mod.quiz[i]) + 1) % api.mod.quiz[i].options.length;
}
check("нижче порогу не зараховано", !api.quizDone(api.mod, api.ms), `${api.quizPercent(api.mod, api.ms)}%`);

// 13. Ваги прогресу кожного модуля
for (const m of api.MODULES) {
  const sum = Object.values(api.weights(m)).reduce((a, b) => a + b, 0);
  check(`сума ваг прогресу = 100 (${m.id})`, sum === 100, String(sum));
}

// 12.1 Антипідказки: формою відповідь не вгадується
const MARKERS = ["ніколи","завжди","повністю","лише","тільки","автоматично","одразу","достатньо","усі ","всі "];
const hasMarker = (text) => MARKERS.some((w) => ` ${text.toLowerCase()} `.includes(w));
function blindScore(items) {
  let hit = 0;
  for (const it of items) {
    const clean = it.options.map((o, i) => [o, i]).filter(([o]) => !hasMarker(o.text)).map(([, i]) => i);
    const pool = clean.length === 1 ? clean : (clean.length ? clean : it.options.map((_, i) => i));
    const pick = pool.reduce((a, b) => (it.options[a].text.length >= it.options[b].text.length ? a : b));
    if (it.options[pick].correct) hit++;
  }
  return hit / items.length;
}
for (const m of api.MODULES) {
  for (const [label, items] of [["квіз", m.quiz], ["мікроперевірки", m.activities.lesson]]) {
    const positions = items.map((it) => it.options.findIndex((o) => o.correct));
    const counts = positions.reduce((acc, p) => (acc[p] = (acc[p] || 0) + 1, acc), {});
    const longest = items.filter((it) => {
      const lens = it.options.map((o) => o.text.length);
      return lens[it.options.findIndex((o) => o.correct)] === Math.max(...lens);
    }).length;
    const ratio = Math.max(...items.map((it) => {
      const lens = it.options.map((o) => o.text.length);
      return Math.max(...lens) / Math.min(...lens);
    }));
    check(`${label} (${m.id}): позиції правильних розкидані`, Math.max(...Object.values(counts)) / items.length <= 0.5, JSON.stringify(counts));
    check(`${label} (${m.id}): правильна не найдовша systematically`, longest / items.length <= 0.4, `${longest}/${items.length}`);
    check(`${label} (${m.id}): довжини варіантів вирівняні`, ratio <= 1.4, `${ratio.toFixed(2)}×`);
    check(`${label} (${m.id}): сліпа стратегія не працює`, blindScore(items) <= 0.4, `${Math.round(blindScore(items) * 100)}%`);
  }
}

// 12.2 Передперевірка, пам’ятка, сесії, першоджерело, канонічна мова
check("є передперевірка до уроку", (api.mod.activities.precheck || []).length >= 2, String((api.mod.activities.precheck || []).length));
check("передперевірка не входить у прогрес", api.progressOf(api.mod, api.freshModuleState(api.mod)) === 0);
check("є сторінка пам’ятки", api.PAGES.some((p) => p.id === "reference") && Boolean(api.mod.sections.find((s) => s.id === "reference")));
check("пам’ятка не потребує дій для прогресу", api.pageDone(api.mod, api.ms, "reference") === true);
check("сесії описані й покривають усі сторінки", (() => {
  const covered = (api.mod.meta.sessions || []).flatMap((s) => s.pages);
  return api.PAGES.every((p) => covered.includes(p.id));
})(), (api.mod.meta.sessions || []).map((s) => s.title).join(" | "));
check("кожна сторінка знає свою сесію", api.PAGES.every((p) => api.sessionOf(p.id)));
check("вказано першоджерело модуля", Boolean(api.mod.meta.primary_source?.id));
check("у тексті уроку є маркери джерел", (api.mod.sections.find((s) => s.id === "lesson").content.match(/\[SRC-\d{3}\]/g) || []).length >= 5);
check("кожен термін глосарію має «так не кажіть»", api.mod.activities.glossary.every((g) => String(g.avoid || "").length > 10));
check("мета навчання пропонується", (api.COURSE.missions || []).length === 3);
check("модуль пояснює користь під кожну мету", (api.COURSE.missions || []).every((m) => String((api.mod.meta.mission_notes || {})[m.id] || "").length > 30));
check("у кейсі немає абсурдних дистракторів",
  api.mod.activities.case.risks.filter((r) => !r.critical).every((r) => !/погод|логотип/i.test(r.text)),
  api.mod.activities.case.risks.filter((r) => !r.critical).map((r) => r.id).join(", "));

// 13.1 Черга інтервального повторення
api.state = api.freshState();
api.openModule(api.MODULES[0].id);
check("черга повторення порожня на старті", api.reviewAll().length === 0);
const wrongQ = api.mod.activities.lesson[0];
api.reviewAdd(api.mod.id, "lesson", wrongQ.id);
api.reviewAdd(api.mod.id, "quiz", 0);
api.reviewAdd(api.mod.id, "glossary", 1);
api.reviewAdd(api.mod.id, "practice", api.mod.activities.practice.fields[0].id);
check("у чергу потрапляють усі чотири типи", api.reviewAll().length === 4);
check("усе нове — до повторення сьогодні", api.reviewDue().length === 4);
check("кожна позиція знає свій вміст", api.reviewAll().every((i) => Boolean(api.reviewContent(i))));
const key = api.reviewAll()[0].key;
api.reviewPass(key);
check("правильна відповідь відкладає позицію", api.reviewStore()[key].due === api.addDays(api.todayISO(), api.REVIEW.intervals_days[1]), api.reviewStore()[key].due);
check("відкладена позиція зникає з «сьогодні»", api.reviewDue().length === 3);
api.reviewFail(key);
check("помилка повертає на перший інтервал", api.reviewStore()[key].step === 0);
for (let i = 0; i < api.REVIEW.intervals_days.length; i++) api.reviewPass(key);
check("після всіх інтервалів позиція покидає чергу", !api.reviewStore()[key], String(api.reviewAll().length));
api.reviewDrop(api.mod.id, "glossary", 1);
check("зняття позначки прибирає термін із черги", !api.reviewAll().some((i) => i.kind === "glossary"));
check("перемішування: черга не сортована за модулем", api.reviewAll().every((i) => Boolean(i.module)));
api.state = api.freshState();
api.openModule(api.MODULES[0].id);
api.ms.practice.answers[api.mod.activities.practice.fields[0].id] = { value: "хибне значення", source: "", missing: false };
api.checkPractice();
check("помилка практики сама потрапляє в чергу", api.reviewAll().some((i) => i.kind === "practice"));

// 14. Автономність
const external = (html.match(/(https?:)?\/\/[^"'\s)]+/g) || [])
  .filter((u) => !/zakon\.rada|tax\.gov|diia\.gov|ukrstat|www\.w3\.org/.test(u));
check("немає зовнішніх ресурсів у розмітці", external.length === 0, external.slice(0, 3).join(" "));
check("немає fetch/XHR", !/\bfetch\(|XMLHttpRequest|importScripts/.test(html));

console.log(failures ? `\nПРОВАЛЕНО перевірок: ${failures}` : "\nусі перевірки пройдено");
process.exit(failures ? 1 : 0);
