# ctx-builder — Context Builder Agent

AI-агент для автоматического сбора и формирования релевантного контекста проекта для AI-систем.

**Задача:** дать AI ровно тот контекст, который нужен для конкретной задачи — не больше, не меньше.

## Возможности

- **Code Review** — архитектурный контекст, связанные классы, project rules
- **Code Generation** — похожие реализации, conventions, patterns
- **Refactoring** — зависимости, call graph, impacted modules
- **Bug Fixing** — stacktrace context, execution chain, related services
- **Documentation** — module descriptions, architecture structure, API contracts
- **Architecture Analysis** — слои, модули, паттерны, связи

## Поддерживаемые технологии

| Стек | Парсер | Метод |
|------|--------|-------|
| ASP.NET Core | C# | Roslyn (subprocess) + regex fallback |
| Laravel | PHP | PHP Parser (subprocess) + regex fallback |
| Node.js / TypeScript | TS | TypeScript Compiler API (subprocess) + regex fallback |
| Vue.js | TS/Vue | TS Compiler API + regex fallback |
| Flutter | Dart | Dart Analyzer (subprocess) + regex fallback |
| Unity | C# | Roslyn + .meta analysis + regex fallback |
| Unreal Engine | C++ | tree-sitter AST + regex fallback |

Без парсера (Rust, Go, Python и др.) — агент работает через прямое чтение файлов.

## Установка

```bash
git clone <repo-url>
cd ctx-builder
pip install -e .
```

Зависимости:
```
click>=8.1, tiktoken>=0.7, pyyaml>=6.0
langgraph>=1.2, langchain-core>=1.4
langchain-openai>=1.2, langchain-anthropic>=1.2
openai>=2.37, python-dotenv>=1.0
tree-sitter>=0.22, tree-sitter-cpp>=0.23
mcp>=1.0 (для Claude Code интеграции)
```

## Быстрый старт

```bash
# Базовое использование
ctx-build -p /path/to/project -t "Code Review: Analyze architecture"

# Выбор модели
ctx-build -p . -t "Refactoring: Extract auth module" \
  --provider openai --model gpt-4o

ctx-build -p . -t "Bug Fixing: NullPointer in UserService" \
  --provider anthropic --model claude-opus-4-7

ctx-build -p . -t "Code Generation: Add email verification" \
  --provider deepseek --model deepseek-chat

# Локальная модель (Ollama, LM Studio, vLLM)
export LOCAL_LLM_URL=http://localhost:11434/v1
ctx-build -p . -t "review" --provider local --model llama3

# Сохранить в файл
ctx-build -p . -t "Documentation: API overview" -o docs/context.md
```

## Провайдеры LLM

| Провайдер | Флаг | Переменные окружения |
|-----------|------|---------------------|
| OpenAI | `--provider openai` | `OPENAI_API_KEY` |
| Anthropic | `--provider anthropic` | `ANTHROPIC_API_KEY` |
| DeepSeek | `--provider deepseek` | `DEEPSEEK_API_KEY` |
| Локальный | `--provider local` | `LOCAL_LLM_URL`, `LOCAL_LLM_API_KEY` |

## Формат вывода — 8 секций

```
1. PROJECT SUMMARY      — что за проект, стек, масштаб
2. ARCHITECTURE         — тип, слои, карта слоёв
3. RELATED FILES        — ключевые файлы с путём и релевантностью
4. DEPENDENCY GRAPH     — файловые, модульные, call-зависимости
5. CONVENTIONS          — naming, patterns, style
6. SIMILAR IMPLEMENTATIONS — классы с теми же паттернами
7. TASK CONTEXT         — что смотреть, ключевые файлы, опасности
8. RELEVANT CODE SNIPPETS  — 3-5 сниппетов с пояснениями
```

## Конфигурация — .ai-context.yml

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
  max_tokens: 120000
  include_tests: true
  include_docs: true

similarity:
  enabled: true

model:
  provider: deepseek
  name: deepseek-chat
```

## Claude Code интеграция

### MCP Server (автоматически)
claude mcp add --scope user --transport stdio ctx-builder -- "C:\Users\wh1te\PycharmProjects\PythonProject10\.venv\Scripts\python.exe" -m
  src.mcp_server

В `.claude/settings.local.json`:
```json
{
  "mcpServers": {
    "ctx-builder": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "/path/to/ctx-builder"
    }
  }
}
```

После перезапуска Claude Code доступны 6 тулов:

| MCP Tool | Назначение | LLM |
|----------|-----------|-----|
| `ctx_summary` | Быстрая сводка проекта | Нет |
| `ctx_search` | Поиск класса/метода | Нет |
| `ctx_dependencies` | Зависимости файла | Нет |
| `ctx_entities` | Классификация сущностей | Нет |
| `ctx_build` | Полный AI-контекст (8 секций) | Да |
| `ctx_gitlab_mr` | Анализ GitLab MR | Да |

### Slash-команда

```
/ctx-build
```
Вызывает skill из `.claude/skills/ctx-build.md`.

## GitLab интеграция

```bash
# Анализ Merge Request
ctx-build -p . --gitlab-mr 123:5

# Указание своего GitLab инстанса
ctx-build -p . --gitlab-mr 123:5 --gitlab-url https://gitlab.example.com
```

Требуется: `GITLAB_TOKEN=glpat-xxxx` в переменных окружения.

Python API:
```python
from src.gitlab import GitLabClient

client = GitLabClient("https://gitlab.com")
projects = client.list_projects(search="my-project")
mr_context = client.build_mr_context(project_id=123, mr_iid=5)
```

## Архитектура проекта

```
┌──────────────────────────────────────────────────┐
│  CLI (cli.py)          MCP Server (mcp_server.py) │
├──────────────────────────────────────────────────┤
│  Agent (agent.py)                                 │
│  LangGraph StateGraph: agent_node ↔ tool_node     │
├──────────────────────────────────────────────────┤
│  Tools (tools.py)          Prompts (prompts/)     │
│  14 тулов + mask_secrets   system.py              │
├──────────────────────────────────────────────────┤
│  Index (index.py)                                 │
│  ProjectIndex, DependencyGraph, SQLite cache      │
│  PageRank, entity classification, compact source  │
├──────────────────┬───────────────────────────────┤
│  Scanner          │  Parsers (parsers/)           │
│  scanner.py       │  base.py → registry.py        │
│  FileEntry,       │  csharp.py, php.py,           │
│  RepoIndex,       │  typescript.py, dart.py,     │
│  RepoScanner      │  cpp.py (tree-sitter),       │
│                   │  unity.py                     │
├──────────────────┴───────────────────────────────┤
│  Config (config.py)     GitLab (gitlab.py)        │
│  .ai-context.yml        GitLabClient, analyze MRs │
└──────────────────────────────────────────────────┘
```

### Ключевые модули

| Модуль | Строк | Назначение |
|--------|-------|-----------|
| `src/index.py` | 733 | ProjectIndex, DependencyGraph, SQLite, ranking, similarity |
| `src/tools.py` | 415 | 14 MCP-тулов + mask_secrets |
| `src/config.py` | 274 | Загрузка .ai-context.yml, детекция 7 типов проектов |
| `src/scanner.py` | 274 | Обход файловой системы, классификация файлов |
| `src/parsers/cpp.py` | 340 | Tree-sitter C++ парсер + regex fallback |
| `src/parsers/csharp.py` | 258 | Roslyn subprocess + regex fallback |
| `src/cli.py` | 92 | Click CLI, 4 провайдера, GitLab MR опция |
| `src/agent.py` | 69 | LangGraph агент (agent + tools + router) |
| `src/mcp_server.py` | 250 | MCP сервер (6 тулов, stdio JSON-RPC) |
| `src/gitlab.py` | 160 | GitLab REST API клиент |
| `src/prompts/system.py` | 122 | Системный промпт агента |

## Инструменты агента (14)

| # | Инструмент | Назначение |
|---|-----------|-----------|
| 1 | `get_summary` | Сводка проекта (файлы, языки, дерево) |
| 2 | `get_docs` | Поиск README, ARCHITECTURE, AI_RULES, ADR |
| 3 | `list_files` | Список файлов в директории |
| 4 | `read_file` | Чтение файла с номерами строк |
| 5 | `compact_file` | Только сигнатуры, без тел и комментариев |
| 6 | `search_symbol` | Поиск класса/метода по имени |
| 7 | `find_files` | Фильтр по паттерну, языку, типу |
| 8 | `get_dependencies` | Что импортирует файл и что импортирует его |
| 9 | `get_call_graph` | Граф вызовов методов |
| 10 | `get_module_graph` | Зависимости модулей верхнего уровня |
| 11 | `classify_entities` | Классификация файлов по типу сущности |
| 12 | `sample_signatures` | Случайная выборка сигнатур классов/методов |
| 13 | `rank_files` | Ранжирование файлов по релевантности (PageRank) |
| 14 | `find_similar` | Поиск похожих классов |

## Безопасность

- `.env`, `.env.*`, `*.pem`, `*.key`, `*.pfx` — исключены из индексации
- `*secret*`, `*credential*`, `*private_key*` — исключены
- Маскирование в `read_file` и `compact_file`:
  - API keys (`sk-...` → `***`)
  - JWT tokens (`eyJ...` → `***JWT***`)
  - Private keys (PEM блоки → `***PRIVATE KEY***`)
  - Connection strings (`password=...` → `password=***`)

## SQLite кеш

Индекс сохраняется в `.ai-context.db` (SQLite, 6 таблиц). При повторном запуске:
- Если исходники не изменились → загрузка из кеша
- Если есть изменения → инкрементальное обновление (только изменённые файлы)

Таблицы: `meta`, `files`, `classes`, `methods`, `deps`, `calls`.

