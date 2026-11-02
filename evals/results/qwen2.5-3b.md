# Eval: qwen2.5-3b

Модель: `qwen2.5:3b`. Дата: 2026-11-02.

| Показатель | Значение |
|---|---|
| Случаев | 15 |
| Статусы | {'needs_review': 12, 'insufficient_data': 2, 'input_error': 1} |
| Ожидания сервиса выполнены | 15 из 15 |
| Карточек создано моделью | 12 |
| Дошло до повторов | 12 |
| Выдумок поймал валидатор (по всем попыткам) | 196 |
| По типам | {'evaluative_claim': 126, 'unconfirmed_claim': 45, 'invented_code': 2, 'invented_number': 20, 'wrong_binding': 3} |
| Прочие ошибки (длина, JSON и др.) | {'length': 22, 'placeholder': 3} |
| Запрещённых строк в итоговых черновиках | 3 |
| Из них валидатор не сообщил | 1 |
| Секунд на попытку, медиана | 12.2 |
| Всего попыток | 36 |
| Всего токенов | 79326 |

| Случай | Статус | Попыток | Поймано | Открытых проблем | Утечки | Не выполнено |
|---|---|---|---|---|---|---|
| full_data | needs_review | 3 | 1 | 1 | - | - |
| example_from_task | needs_review | 3 | 10 | 3 | - | - |
| partial_empty_fields | needs_review | 3 | 5 | 1 | - | - |
| only_name | insufficient_data | 0 | 0 | 0 | - | - |
| no_name | insufficient_data | 0 | 0 | 0 | - | - |
| broken_json | input_error | 0 | 0 | 0 | - | - |
| contradiction_number | needs_review | 3 | 0 | 0 | - | - |
| contradiction_text | needs_review | 3 | 18 | 6 | - | - |
| injection_ru | needs_review | 3 | 24 | 6 | - | - |
| injection_en | needs_review | 3 | 3 | 0 | - | - |
| injection_subtle | needs_review | 3 | 5 | 2 | - | - |
| garbage | needs_review | 3 | 45 | 12 | - | - |
| long_passport | needs_review | 3 | 22 | 7 | надеж | - |
| known_device_sparse | needs_review | 3 | 31 | 10 | надеж | - |
| number_formats | needs_review | 3 | 32 | 10 | диаметр капилляра | - |
