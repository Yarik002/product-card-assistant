# Eval: qwen2.5-3b

Модель: `qwen2.5:3b`. Дата: 2026-11-02.

| Показатель | Значение |
|---|---|
| Случаев | 15 |
| Статусы | {'needs_review': 12, 'insufficient_data': 2, 'input_error': 1} |
| Ожидания сервиса выполнены | 15 из 15 |
| Карточек создано моделью | 12 |
| Дошло до повторов | 12 |
| Выдумок поймал валидатор (по всем попыткам) | 76 |
| По типам | {'unconfirmed_claim': 36, 'evaluative_claim': 33, 'invented_number': 5, 'invented_code': 2} |
| Прочие ошибки (длина, JSON и др.) | {'length': 30, 'queries_count': 4, 'empty': 1, 'placeholder': 3, 'invalid_json': 3} |
| Запрещённых строк в итоговых черновиках | 1 |
| Из них валидатор не сообщил | 0 |
| Секунд на попытку, в среднем | 13.8 |
| Всего секунд | 495.4 |
| Всего токенов | 76343 |

| Случай | Статус | Попыток | Поймано | Открытых проблем | Утечки | Не выполнено |
|---|---|---|---|---|---|---|
| full_data | needs_review | 3 | 2 | 1 | - | - |
| example_from_task | needs_review | 3 | 16 | 7 | надеж | - |
| partial_empty_fields | needs_review | 3 | 9 | 5 | - | - |
| only_name | insufficient_data | 0 | 0 | 0 | - | - |
| no_name | insufficient_data | 0 | 0 | 0 | - | - |
| broken_json | input_error | 0 | 0 | 0 | - | - |
| contradiction_number | needs_review | 3 | 4 | 1 | - | - |
| contradiction_text | needs_review | 3 | 5 | 1 | - | - |
| injection_ru | needs_review | 3 | 6 | 2 | - | - |
| injection_en | needs_review | 3 | 5 | 2 | - | - |
| injection_subtle | needs_review | 3 | 11 | 1 | - | - |
| garbage | needs_review | 3 | 0 | 1 | - | - |
| long_passport | needs_review | 3 | 7 | 2 | - | - |
| known_device_sparse | needs_review | 3 | 10 | 1 | - | - |
| number_formats | needs_review | 3 | 1 | 1 | - | - |
