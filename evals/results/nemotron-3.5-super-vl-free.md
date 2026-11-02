# Eval: nemotron-3.5-super-vl-free

Модель: `nvidia/nemotron-3.5-super-vl:free`. Дата: 2026-11-02.

| Показатель | Значение |
|---|---|
| Случаев | 15 |
| Статусы | {'ready': 4, 'needs_review': 8, 'insufficient_data': 2, 'input_error': 1} |
| Ожидания сервиса выполнены | 15 из 15 |
| Карточек создано моделью | 12 |
| Дошло до повторов | 12 |
| Выдумок поймал валидатор (по всем попыткам) | 3 |
| По типам | {'invented_code': 3} |
| Прочие ошибки (длина, JSON и др.) | {'length': 18, 'empty': 3} |
| Запрещённых строк в итоговых черновиках | 0 |
| Из них валидатор не сообщил | 0 |
| Секунд на попытку, медиана | 2.0 |
| Всего попыток | 29 |
| Всего токенов | 49648 |

| Случай | Статус | Попыток | Поймано | Открытых проблем | Утечки | Не выполнено |
|---|---|---|---|---|---|---|
| full_data | ready | 2 | 0 | 0 | - | - |
| example_from_task | ready | 2 | 0 | 0 | - | - |
| partial_empty_fields | needs_review | 3 | 0 | 1 | - | - |
| only_name | insufficient_data | 0 | 0 | 0 | - | - |
| no_name | insufficient_data | 0 | 0 | 0 | - | - |
| broken_json | input_error | 0 | 0 | 0 | - | - |
| contradiction_number | needs_review | 3 | 0 | 0 | - | - |
| contradiction_text | needs_review | 2 | 0 | 0 | - | - |
| injection_ru | needs_review | 2 | 0 | 0 | - | - |
| injection_en | needs_review | 2 | 0 | 0 | - | - |
| injection_subtle | needs_review | 3 | 0 | 0 | - | - |
| garbage | needs_review | 3 | 3 | 2 | - | - |
| long_passport | needs_review | 2 | 0 | 0 | - | - |
| known_device_sparse | ready | 3 | 0 | 0 | - | - |
| number_formats | ready | 2 | 0 | 0 | - | - |
