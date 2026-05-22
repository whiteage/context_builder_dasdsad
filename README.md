# ctx-builder — Context Builder Agent

AI-агент для автоматического сбора и формирования релевантного контекста проекта для AI-систем (Claude Code, OpenAI Codex, локальные LLM).

**Главная задача:** дать AI ровно тот контекст, который нужен для конкретной задачи — не больше, не меньше.

## Возможности

| Use Case | Что собирает |
|----------|-------------|
| **Code Review** | Архитектурный контекст, связанные классы, project rules |
| **Code Generation** | Похожие реализации, conventions, patterns, примеры кода |
| **Refactoring** | Зависимости, call graph, затронутые модули |
| **Bug Fixing** | Контекст stacktrace, цепочка вызовов, связанные сервисы |
| **Documentation** | Описания модулей, структура архитектуры, API контракты |
| **Architecture Analysis** | Слои, модули, паттерны, связи между компонентами |

## Поддерживаемые технологии

| Стек | Язык | Парсер | Охват |
|------|------|--------|-------|
| ASP.NET Core | C# | Roslyn AST | ~100% |
| Unity | C# | Roslyn + .meta analysis | ~97% |
| Laravel | PHP | PHP Parser | ~85% |
| Flutter | Dart | Dart Analyzer | ~87% |
| Node.js / TypeScript | TS/Vue | TS Compiler API + regex | ~20% |
| Unreal Engine | C++ | tree-sitter AST | ~49% |

Для языков без парсера (Rust, Go, Python) агент работает через прямое чтение файлов через `read_file`/`compact_file`.

## Установка

```bash
git clone <repo-url>
cd ctx-builder
pip install -e .
```

## Настройка

### 1. API ключи

Скопируйте шаблон и заполните хотя бы один ключ:

```bash
cp .env.example .env
# Отредактируйте .env — вставьте свой API ключ
```

Минимально нужен один ключ. Рекомендуется DeepSeek (`DEEPSEEK_API_KEY`) — лучший баланс цены и качества.

### 2. Выбор модели по умолчанию

Модель можно задать тремя способами (в порядке приоритета):

**Способ 1 — `.ai-context.yml` (на конкретный проект):**
```yaml
model:
  provider: openai
  name: gpt-4o
```

**Способ 2 — переменные окружения (глобально):**
```bash
# В .env или экспортом
CTX_BUILDER_DEFAULT_PROVIDER=deepseek
CTX_BUILDER_DEFAULT_MODEL=deepseek-v4-flash
```

**Способ 3 — флаг CLI (на один запуск):**
```bash
ctx-build -p . -t "Code Review" --provider anthropic --model claude-haiku-4-5-20251001
```

Если ничего не указано — используется `deepseek/deepseek-chat`.

### 3. Проверка установки

```bash
ctx-build -p . -t "test"
```

## Быстрый старт

```bash
# Базовое использование
ctx-build -p /path/to/project -t "Code Review: Analyze architecture"

# Выбор модели
ctx-build -p . -t "Refactoring: Extract auth module" --provider openai --model gpt-4o
ctx-build -p . -t "Bug Fixing: NullPointer in UserService" --provider anthropic --model claude-opus-4-7
ctx-build -p . -t "Code Generation: Add email verification" --provider deepseek --model deepseek-v4-pro

# Локальная модель (Ollama, LM Studio, vLLM)
export LOCAL_LLM_URL=http://localhost:11434/v1
ctx-build -p . -t "review" --provider local --model llama3

# Сохранить в файл
ctx-build -p . -t "Documentation: API overview" -o docs/context.md
```

## Провайдеры LLM

| Провайдер | Флаг | Модели | Переменная |
|-----------|------|--------|-----------|
| OpenAI | `--provider openai` | gpt-4o, gpt-4-turbo | `OPENAI_API_KEY` |
| Anthropic | `--provider anthropic` | claude-opus-4-7, claude-sonnet-4-6 | `ANTHROPIC_API_KEY` |
| DeepSeek | `--provider deepseek` | deepseek-chat, deepseek-v4-pro | `DEEPSEEK_API_KEY` |
| Локальный | `--provider local` | Любая OpenAI-совместимая | `LOCAL_LLM_URL` |

**Рекомендация:** deepseek-v4-flash — лучший баланс цены и скорости для plan+execute архитектуры. deepseek-v4-pro даёт более детальный вывод, но в 3-4 раза медленнее.

## Формат вывода — 8 секций

```
1. PROJECT SUMMARY      — стек, размер, тип проекта (2-4 предложения)
2. ARCHITECTURE         — паттерн (Layered/DDD/ECS/Modular Monolith), слои, ответственности
3. RELATED FILES        — 5-8 файлов с путём, типом, назначением, релевантностью
4. DEPENDENCY GRAPH     — импорты/импортируется, граф вызовов (из get_dependencies)
5. CONVENTIONS          — naming rules, patterns, code style (project-specific)
6. SIMILAR IMPLEMENTATIONS — 3-4 класса/файла с теми же паттернами
7. TASK CONTEXT         — что трогать, чему следовать, чего избегать
8. RELEVANT CODE SNIPPETS  — 3-5 сниппетов из read_file/compact_file (только реальный код)
```

## Конфигурация — `.ai-context.yml`

Создайте `.ai-context.yml` в корне целевого проекта:

```yaml
architecture:
  auto_detect: true

indexing:
  exclude:
    - node_modules/**
    - .git/**
    - Binaries/**
    - "*.generated.*"

context:
  max_tokens: 120000          # лимит выходного документа
  agent_token_budget: 80000   # бюджет на сбор данных (pre-collect + planner)
  include_tests: true
  include_docs: true

similarity:
  enabled: true

model:
  provider: deepseek
  name: deepseek-v4-pro
```

Если `.ai-context.yml` отсутствует — используются значения по умолчанию (те же, что в примере).

## Claude Code интеграция

### MCP Server

Подключение в `.claude/settings.local.json`:

```json
{
  "mcpServers": {
    "ctx-builder": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "/path/to/ctx-builder",
      "env": {
        "DEEPSEEK_API_KEY": "sk-your-key-here",
        "CTX_BUILDER_DEFAULT_PROVIDER": "deepseek",
        "CTX_BUILDER_DEFAULT_MODEL": "deepseek-v4-flash"
      }
    }
  }
}
```

**Важно:** `command` должен указывать на python с установленными зависимостями (виртуальное окружение или системный python).  
**env** — опционально. Если не указан, ключи берутся из `.env` в корне проекта.

**Доступные инструменты (2):**

| MCP Tool | Назначение | LLM |
|----------|-----------|-----|
| `ctx_build` | Полный AI-контекст (8 секций) | Да |
| `ctx_gitlab_mr` | Контекст из GitLab Merge Request | Нет |

Внутренние тулзы gatherer'а (15 штук: `get_summary`, `search_symbol`, `get_dependencies`, `compact_file`, `read_file`, `classify_entities`, `sample_signatures`, `find_similar`, `rank_files`, `get_docs`, `get_module_graph`, `get_call_graph`, `find_files`, `list_files`, `get_token_budget`) используются внутри `ctx_build` и не экспортируются как отдельные MCP-эндпоинты.

### Slash-команда

```
/ctx-build
```

## GitLab интеграция

```bash
# Анализ Merge Request
ctx-build -p . --gitlab-mr 123:5

# Свой GitLab инстанс
ctx-build -p . --gitlab-mr 123:5 --gitlab-url https://gitlab.example.com
```

Требуется: `GITLAB_TOKEN=glpat-xxxx` в переменных окружения.

## Архитектура

```
CLI (cli.py)              MCP Server (mcp_server.py)
         └────────────┬────────────┘
                   Agent (agent.py)
              Plan+Execute pattern
         ┌─────────┴──────────┐
    Phase 0+2 (код)      Phase 1 (LLM)      Phase 3 (LLM)
    Pre-collect +        Planner             Writer
    Execute              JSON-план тулзов    пишет документ
         │                    │
    Tools (tools.py)     Prompts (prompts/system.py)
    15 тулзов +           planner/writer промпты
    mask_secrets
         │
    Index (index.py)
    ProjectIndex, DependencyGraph, SQLite cache
    PageRank, entity classification, compact source
         │
    ┌────┴─────────────┐
  Scanner           Parsers (parsers/)
  scanner.py        csharp, php, typescript, dart, cpp, unity
  RepoIndex,
  RepoScanner
         │
    Config (config.py)    GitLab (gitlab.py)
    .ai-context.yml       GitLabClient, MR анализ
```

### Plan+Execute (три фазы)

Агент работает в три фазы:

1. **Phase 0 — Pre-collect (код, ~1s):** Параллельный вызов 5-9 независимых инструментов без участия LLM: `get_summary`, `get_docs`, `classify_entities`, `get_module_graph`, `search_symbol` по ключевым словам из задачи.

2. **Phase 1 — Planner (LLM, 1 вызов, ~5s):** LLM получает pre-collected данные и возвращает JSON-план: какие файлы передать в `get_dependencies`, `compact_file`, `read_file`, `find_similar`. Один LLM-вызов вместо 7-30 в старой gatherer-архитектуре.

3. **Phase 2 — Execute (код, ~1s):** Параллельное исполнение всех тулзов из JSON-плана через ThreadPoolExecutor.

4. **Phase 3 — Writer (LLM, 1 вызов, ~12s):** Одиночный LLM-вызов без тулзов. Получает все собранные данные → формирует 8-секционный документ.

**Преимущества:** 1 LLM-раундтрип вместо 7-30 в фазе сбора данных. Общее время ~19s (стабильно) вместо 50-150s (вариативно).

### Инкрементальное сканирование

Повторный запуск на неизменённом проекте — **<0.5 секунд** (вместо 10-40с первого сканирования). Индекс кешируется в `.ai-context.db` (SQLite), а `_quick_scan` проверяет mtimes директорий и пропускает неизменённые поддеревья.

## Безопасность

- Секреты маскируются при чтении: API keys (`sk-...`), JWT токены, приватные ключи, connection strings
- Исключены из индексации: `.env`, `.env.*`, `*.pem`, `*.key`, `*.pfx`, `*secret*`, `*credential*`, `*private_key*`
- `.ai-context.db` исключён из сканирования

## SQLite кеш

Индекс сохраняется в `.ai-context.db` (SQLite, 6 таблиц): `meta`, `files`, `classes`, `methods`, `deps`, `calls`.

- **Холодный старт** (первый запуск): полное сканирование + AST-парсинг (1-58 сек в зависимости от размера)
- **Горячий старт** (без изменений): загрузка из кеша (<1 сек)
- **Инкремент** (есть изменения): перепарсинг только изменённых файлов
- **ctx_build (холодный):** ~20s (индекс + 1 LLM-планер + 1 LLM-райтер + параллельный execute)
- **ctx_build (горячий):** ~18s (<1s индекс + 1 LLM-планер + 1 LLM-райтер + параллельный execute)

## Результаты тестирования (2026-05-22, plan+execute, deepseek-v4-flash)

| Проект | Файлов | Классов | Методов | Deps | Индекс (хол) | Индекс (гор) | Шагов LLM | get_deps |
|--------|--------|---------|---------|------|-------------|-------------|-----------|----------|
| nopCommerce (C#) | 6 350 | 3 617 | 9 869 | 51K | 58s | <1s | 1 | 4-7K |
| directus (TS) | 4 075 | 3 128 | 1 349 | 7 988 | 9s | <1s | 1 | 0.3-1.6K |
| strapi (TS) | 5 907 | 5 631 | 1 586 | 8 996 | 7s | <1s | 1 | 0.6-1.8K |
| FPSSample (C#/Unity) | 12 727 | 2 152 | 8 239 | 81K | 39s | <1s | 1 | 5.6-7.8K |
| EpicSurvivalGame (C++) | 766 | 38 | 329 | 120 | 1s | <1s | 1 | 0-1.2K |
| rustdesk (Dart+Rust) | 928 | 570 | 2 838 | 216 | 5s | <1s | 1 | 0.6-1.5K |

**Plan+Execute — всегда 1 LLM-шаг в фазе сбора.** `get_dependencies` вызывается в 100% запусков (против 71-93% в старой gatherer-архитектуре). Все 8 секций документа заполняются реальными данными.

**Модели:**

| Модель | LLM время | Качество | Батчинг |
|--------|-----------|----------|---------|
| deepseek-v4-flash | ~19s | Хорошее | Не нужен (plan+execute) |
| deepseek-v4-pro | ~35s | Отличное | Не нужен (plan+execute) |
| deepseek-chat | ~25s | Среднее | Не рекомендуется |

## Лицензия

MIT
