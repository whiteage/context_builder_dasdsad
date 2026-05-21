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

**Рекомендация:** deepseek-v4-pro — лучший баланс качества и скорости. Лучше следует инструкциям, не выдумывает код, использует реальные данные из тулзов.

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
  agent_token_budget: 50000   # бюджет gatherer'а на чтение тулзов
  max_steps: 25               # макс. итераций gatherer'а
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
              Plan-and-Execute pattern
         ┌─────────┴─────────┐
    Gatherer              Writer
 (agent + tools,      (LLM без тулзов,
  сбор данных)         пишет документ)
         │
    Tools (tools.py)     Prompts (prompts/system.py)
    15 тулзов +            gatherer/writer промпты
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

### Plan-and-Execute

Агент работает в два этапа:

1. **Gatherer** — агент с тулзами, только собирает данные (get_summary → search_symbol → get_dependencies → compact_file → read_file). Не пишет документ.
2. **Writer** — одиночный LLM-вызов без тулзов. Получает собранные данные → формирует 8-секционный документ.

Разделение решает проблему deepseek-chat: модель в режиме tool-calling залипает на вызовах тулзов и не переключается на написание документа.

### Инкрементальное сканирование

Повторный запуск на неизменённом проекте — **<0.5 секунд** (вместо 10-40с первого сканирования). Индекс кешируется в `.ai-context.db` (SQLite), а `_quick_scan` проверяет mtimes директорий и пропускает неизменённые поддеревья.

## Безопасность

- Секреты маскируются при чтении: API keys (`sk-...`), JWT токены, приватные ключи, connection strings
- Исключены из индексации: `.env`, `.env.*`, `*.pem`, `*.key`, `*.pfx`, `*secret*`, `*credential*`, `*private_key*`
- `.ai-context.db` исключён из сканирования

## SQLite кеш

Индекс сохраняется в `.ai-context.db` (SQLite, 6 таблиц): `meta`, `files`, `classes`, `methods`, `deps`, `calls`.

- **Холодный старт** (первый запуск): полное сканирование + AST-парсинг (10-40 сек в зависимости от размера)
- **Горячий старт** (без изменений): загрузка из кеша (<0.5 сек)
- **Инкремент** (есть изменения): перепарсинг только изменённых файлов

## Результаты тестирования (2026-05-21)

| Проект | Файлов | Классов | Методов | Deps | Индекс | ctx_build |
|--------|--------|---------|---------|------|--------|-----------|
| nopCommerce (C#) | 6 350 | 3 617 | 9 869 | 50 986 | 38s | ~2000 tok |
| monica (PHP) | 2 091 | 1 409 | 4 879 | 184K | 10s | ~2000 tok |
| rustdesk (Dart+Rust) | 928 | 570 | 2 838 | 216 | 5s | ~1500 tok |
| directus (TS) | 4 068 | 624 | 1 321 | 7 985 | 15s | ~2000 tok |
| strapi (TS) | 5 907 | 2 279 | 1 069 | 8 969 | 25s | ~1800 tok |
| FPSSample (C#/Unity) | 12 727 | 2 152 | 8 239 | 81K | 38s | ~2200 tok |
| EpicSurvivalGame (C++) | 764 | 38 | 329 | 120 | 2s | ~2000 tok |

**Качество вывода (deepseek-v4-pro):** все 8 секций заполнены, dependency graph из реальных данных, conventions project-specific, сниппеты только из read_file/compact_file (без fabrication).

## Лицензия

MIT
