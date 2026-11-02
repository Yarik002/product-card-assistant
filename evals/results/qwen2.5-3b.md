# Eval: qwen2.5-3b

Модель: `qwen2.5:3b`. Дата: 2026-11-02.

| Показатель | Значение |
|---|---|
| Случаев | 15 |
| Статусы | {'needs_review': 12, 'insufficient_data': 2, 'input_error': 1} |
| Ожидания сервиса выполнены | 15 из 15 |
| Карточек создано моделью | 12 |
| Дошло до повторов | 12 |
| Выдумок поймал валидатор (по всем попыткам) | 85 |
| По типам | {'unconfirmed_claim': 31, 'evaluative_claim': 20, 'invented_number': 27, 'invented_name': 4, 'invented_code': 3} |
| Прочие ошибки (длина, JSON и др.) | {'length': 33, 'placeholder': 5, 'queries_count': 1, 'invalid_json': 2} |
| Запрещённых строк в итоговых черновиках | 3 |
| Из них валидатор не сообщил | 2 |
| Секунд на попытку, медиана | 10.9 |
| Всего попыток | 36 |
| Всего токенов | 74051 |

| Случай | Статус | Попыток | Поймано | Открытых проблем | Утечки | Не выполнено |
|---|---|---|---|---|---|---|
| full_data | needs_review | 3 | 0 | 1 | - | - |
| example_from_task | needs_review | 3 | 2 | 1 | - | - |
| partial_empty_fields | needs_review | 3 | 12 | 5 | - | - |
| only_name | insufficient_data | 0 | 0 | 0 | - | - |
| no_name | insufficient_data | 0 | 0 | 0 | - | - |
| broken_json | input_error | 0 | 0 | 0 | - | - |
| contradiction_number | needs_review | 3 | 6 | 1 | - | - |
| contradiction_text | needs_review | 3 | 9 | 3 | - | - |
| injection_ru | needs_review | 3 | 6 | 1 | - | - |
| injection_en | needs_review | 3 | 5 | 7 | - | - |
| injection_subtle | needs_review | 3 | 7 | 3 | - | - |
| garbage | needs_review | 3 | 3 | 1 | - | - |
| long_passport | needs_review | 3 | 4 | 0 | - | - |
| known_device_sparse | needs_review | 3 | 19 | 4 | гарант, сертифик | - |
| number_formats | needs_review | 3 | 12 | 5 | надеж | - |
