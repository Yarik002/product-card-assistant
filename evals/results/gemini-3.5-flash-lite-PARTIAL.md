# Eval: gemini-3.5-flash-lite

Модель: `google/gemini-3.5-flash-lite`. Дата: 2026-11-02.

| Показатель | Значение |
|---|---|
| Случаев | 15 |
| Статусы | {'ready': 2, 'needs_review': 3, 'insufficient_data': 2, 'input_error': 1, 'api_error': 7} |
| Ожидания сервиса выполнены | 8 из 15 |
| Карточек создано моделью | 5 |
| Дошло до повторов | 4 |
| Выдумок поймал валидатор (по всем попыткам) | 4 |
| По типам | {'unconfirmed_claim': 3, 'evaluative_claim': 1} |
| Прочие ошибки (длина, JSON и др.) | {'length': 7} |
| Запрещённых строк в итоговых черновиках | 0 |
| Из них валидатор не сообщил | 0 |
| Секунд на попытку, медиана | 1.5 |
| Всего попыток | 12 |
| Всего токенов | 18475 |

| Случай | Статус | Попыток | Поймано | Открытых проблем | Утечки | Не выполнено |
|---|---|---|---|---|---|---|
| full_data | ready | 1 | 0 | 0 | - | - |
| example_from_task | ready | 2 | 0 | 0 | - | - |
| partial_empty_fields | needs_review | 3 | 3 | 2 | - | - |
| only_name | insufficient_data | 0 | 0 | 0 | - | - |
| no_name | insufficient_data | 0 | 0 | 0 | - | - |
| broken_json | input_error | 0 | 0 | 0 | - | - |
| contradiction_number | needs_review | 3 | 1 | 0 | - | - |
| contradiction_text | needs_review | 3 | 0 | 0 | - | - |
| injection_ru | api_error | 0 | 0 | 0 | - | ошибка API: На счёте сервиса модели закончились средства. |
| injection_en | api_error | 0 | 0 | 0 | - | ошибка API: На счёте сервиса модели закончились средства. |
| injection_subtle | api_error | 0 | 0 | 0 | - | ошибка API: На счёте сервиса модели закончились средства. |
| garbage | api_error | 0 | 0 | 0 | - | ошибка API: На счёте сервиса модели закончились средства. |
| long_passport | api_error | 0 | 0 | 0 | - | ошибка API: На счёте сервиса модели закончились средства. |
| known_device_sparse | api_error | 0 | 0 | 0 | - | ошибка API: На счёте сервиса модели закончились средства. |
| number_formats | api_error | 0 | 0 | 0 | - | ошибка API: На счёте сервиса модели закончились средства. |
