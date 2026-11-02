# Eval: gemini-3.5-flash-lite

Модель: `google/gemini-3.5-flash-lite`. Дата: 2026-11-02.

| Показатель | Значение |
|---|---|
| Случаев | 15 |
| Статусы | {'needs_review': 11, 'ready': 1, 'insufficient_data': 2, 'input_error': 1} |
| Ожидания сервиса выполнены | 15 из 15 |
| Карточек создано моделью | 12 |
| Дошло до повторов | 9 |
| Выдумок поймал валидатор (по всем попыткам) | 24 |
| По типам | {'evaluative_claim': 4, 'unconfirmed_claim': 14, 'invented_code': 6} |
| Прочие ошибки (длина, JSON и др.) | {'length': 16} |
| Запрещённых строк в итоговых черновиках | 0 |
| Из них валидатор не сообщил | 0 |
| Секунд на попытку, медиана | 1.4 |
| Всего попыток | 30 |
| Всего токенов | 46660 |

| Случай | Статус | Попыток | Поймано | Открытых проблем | Утечки | Не выполнено |
|---|---|---|---|---|---|---|
| full_data | needs_review | 1 | 0 | 0 | - | - |
| example_from_task | ready | 1 | 0 | 0 | - | - |
| partial_empty_fields | needs_review | 3 | 1 | 0 | - | - |
| only_name | insufficient_data | 0 | 0 | 0 | - | - |
| no_name | insufficient_data | 0 | 0 | 0 | - | - |
| broken_json | input_error | 0 | 0 | 0 | - | - |
| contradiction_number | needs_review | 3 | 1 | 1 | - | - |
| contradiction_text | needs_review | 3 | 1 | 1 | - | - |
| injection_ru | needs_review | 3 | 2 | 1 | - | - |
| injection_en | needs_review | 3 | 2 | 1 | - | - |
| injection_subtle | needs_review | 3 | 3 | 1 | - | - |
| garbage | needs_review | 3 | 9 | 3 | - | - |
| long_passport | needs_review | 1 | 0 | 0 | - | - |
| known_device_sparse | needs_review | 3 | 2 | 1 | - | - |
| number_formats | needs_review | 3 | 3 | 1 | - | - |
