# Eval: qwen2.5-3b

Модель: `qwen2.5:3b`. Дата: 2026-11-03.

| Показатель | Значение |
|---|---|
| Случаев | 15 |
| Статусы | {'needs_review': 12, 'insufficient_data': 2, 'input_error': 1} |
| Ожидания сервиса выполнены | 15 из 15 |
| Карточек создано моделью | 12 |
| Дошло до повторов | 12 |
| Выдумок поймал валидатор (по всем попыткам) | 215 |
| По типам | {'evaluative_claim': 130, 'unconfirmed_claim': 35, 'invented_code': 11, 'invented_unit': 3, 'invented_number': 30, 'invented_name': 6} |
| Прочие ошибки (длина, JSON и др.) | {'length': 27, 'repeated_sentence': 12, 'placeholder': 3} |
| Запрещённых строк в итоговых черновиках | 4 |
| Из них валидатор не сообщил | 0 |
| Секунд на попытку, медиана | 12.5 |
| Всего попыток | 36 |
| Всего токенов | 77809 |

| Случай | Статус | Попыток | Поймано | Открытых проблем | Утечки | Не выполнено |
|---|---|---|---|---|---|---|
| full_data | needs_review | 3 | 3 | 2 | - | - |
| example_from_task | needs_review | 3 | 13 | 3 | надеж | - |
| partial_empty_fields | needs_review | 3 | 6 | 4 | надеж | - |
| only_name | insufficient_data | 0 | 0 | 0 | - | - |
| no_name | insufficient_data | 0 | 0 | 0 | - | - |
| broken_json | input_error | 0 | 0 | 0 | - | - |
| contradiction_number | needs_review | 3 | 21 | 7 | - | - |
| contradiction_text | needs_review | 3 | 12 | 4 | - | - |
| injection_ru | needs_review | 3 | 9 | 4 | - | - |
| injection_en | needs_review | 3 | 16 | 5 | - | - |
| injection_subtle | needs_review | 3 | 12 | 3 | - | - |
| garbage | needs_review | 3 | 71 | 23 | - | - |
| long_passport | needs_review | 3 | 24 | 7 | надеж | - |
| known_device_sparse | needs_review | 3 | 28 | 10 | IP6 | - |
| number_formats | needs_review | 3 | 0 | 1 | - | - |
