Now I have enough context to produce the comprehensive code review. Let me compile everything.

---

## CODE REVIEW: Strapi Project Architecture, Systems & Conventions

### 1. PROJECT SUMMARY

**Project**: Strapi — Open-source headless CMS (self-hosted or cloud)
**Tech Stack**: TypeScript (3605 files, 61%), JavaScript (824 files, 14%), JSON (743 files, 13%), YAML (46 files)
**Scale**: 5907 total files across a monorepo managed with Yarn workspaces + Nx
**Repository Structure**: Monorepo with `packages/` containing core modules, plugins, providers, CLI tools, and utilities

**Key packages**:
- `packages/core/core` — Core Strapi engine (Strapi class, loaders, registries, services)
- `packages/core/strapi` — CLI entry point (commands for build, develop, start, transfer, etc.)
- `packages/core/admin` — Admin panel (React frontend + server-side controllers/services)
- `packages/core/database` — Database abstraction layer (Knex-based, multi-dialect)
- `packages/core/content-manager` — Content management plugin (CRUD for content types)
- `packages/core/content-releases` — Content scheduling/releases
- `packages/core/content-type-builder` — Visual content type builder
- `packages/core/data-transfer` — Import/export/transfer engine
- `packages/core/permissions` — Permission engine
- `packages/core/types` — TypeScript type definitions
- `packages/core/upload` — Media upload management
- `packages/core/email` — Email sending
- `packages/plugins/*` — Official plugins (i18n, users-permissions, graphql, documentation, sentry, cloud, color-picker)
- `packages/providers/*` — Provider packages (upload-aws-s3, upload-cloudinary, email-sendgrid, etc.)

---

### 2. ARCHITECTURE

**Architecture Type**: **Modular Monolith with Plugin Architecture** — a single application server with a plugin system for extension.

**Lifecycle Phases** (defined in `packages/core/core/src/Strapi.ts`):
1. **Constructor** → `loadConfiguration()` + `registerInternalServices()` (DI container setup)
2. **`start()`** → `load()` → `register()` → `bootstrap()` → `listen()`
3. **`register()`** → EE init → provider register → plugin register → user register → custom field conversion
4. **`bootstrap()`** → DB init → schema sync → middleware init → routing init → permissions register → plugin bootstrap → user bootstrap
5. **`destroy()`** → plugin destroy → provider destroy → server destroy → DB destroy

**Layered Architecture** (backend request flow: **Routes → Middlewares → Controllers → Services → Database**):

| Layer | Responsibility | Location |
|-------|---------------|----------|
| **Container/DI** | IoC container (`Container` class) | `packages/core/core/src/container.ts` |
| **Configuration** | Config loading from files/env | `packages/core/core/src/configuration/` |
| **Loaders** | Load APIs, plugins, components, middlewares, policies | `packages/core/core/src/loaders/` |
| **Registries** | Named registries for content-types, services, controllers, etc. | `packages/core/core/src/registries/` |
| **Domain** | Content type & module domain models | `packages/core/core/src/domain/` |
| **Core API** | Auto-generated CRUD controllers/services/routes | `packages/core/core/src/core-api/` |
| **Services** | Entity service, document service, auth, content API, server, metrics | `packages/core/core/src/services/` |
| **Middlewares** | Body parser, CORS, compression, errors, favicon, etc. | `packages/core/core/src/middlewares/` |
| **Database** | Knex-based ORM with entity manager, migrations, schema sync | `packages/core/database/src/` |
| **Permissions** | Action/condition providers, permission engine | `packages/core/permissions/src/` |
| **Admin Panel** | React SPA with Redux store, RBAC, plugin injection | `packages/core/admin/admin/src/` |
| **Plugins** | Self-contained modules (register/bootstrap/destroy lifecycle) | `packages/core/*/server/src/`, `packages/plugins/*/server/` |

**Key Architectural Patterns**:
- **Service Locator / DI Container**: `Container` class with lazy singleton resolution via `.add(name, resolver)` and `.get(name)`
- **Plugin System**: Each plugin exports `{ register, bootstrap, destroy, controllers, services, routes, policies, contentTypes, config }`
- **Document Service Pattern**: Newer abstraction over entity service, supporting draft/publish, localization, versioning
- **Middleware Pipeline**: Koa-based middleware chain with error handling
- **Provider Pattern**: Upload and email providers follow a strategy pattern
- **Registry Pattern**: Named registries for content-types, services, controllers, policies, middlewares, etc.
- **Factory Pattern**: `factories.createCoreController()`, `factories.createCoreService()`, `factories.createCoreRouter()`

---

### 3. RELATED FILES

| # | File | Purpose | Relevance |
|---|------|---------|-----------|
| 1 | `packages/core/core/src/Strapi.ts` | Main Strapi application class (600 lines) | Central orchestrator — lifecycle, DI container, service accessors |
| 2 | `packages/core/core/src/container.ts` | IoC container with lazy singleton resolution | Foundation of DI pattern used throughout |
| 3 | `packages/core/core/src/loaders/index.ts` | Application context loader (plugins, APIs, components, etc.) | Shows loading order and initialization flow |
| 4 | `packages/core/core/src/loaders/apis.ts` | API loader — reads `src/api/*` directories | Shows how content types, controllers, services are auto-discovered |
| 5 | `packages/core/core/src/loaders/plugins/index.ts` | Plugin loader with user config/extension support | Plugin lifecycle and extension mechanism |
| 6 | `packages/core/core/src/domain/module/index.ts` | Module domain model (bootstrap/register/destroy lifecycle) | Core plugin/module abstraction |
| 7 | `packages/core/core/src/domain/content-type/index.ts` | Content type definition validation and schema building | Content type model lifecycle |
| 8 | `packages/core/core/src/core-api/controller/collection-type.ts` | Auto-generated collection type controller | Core API controller pattern (find, findOne, create, update, delete) |
| 9 | `packages/core/core/src/core-api/service/core-service.ts` | Base core service | Foundation for auto-generated services |
| 10 | `packages/core/core/src/services/entity-service/index.ts` | Entity service (deprecated in favor of document service) | CRUD operations with params wrapping and result wrapping |
| 11 | `packages/core/core/src/services/document-service/index.ts` | Document service (newer, preferred) | Draft/publish, localization, versioning support |
| 12 | `packages/core/core/src/services/server/index.ts` | Koa HTTP server with routing | Server setup, route mounting, middleware registration |
| 13 | `packages/core/core/src/services/content-api/index.ts` | Content API layer (query params, sanitizers, validators) | REST API parameter handling and permissions |
| 14 | `packages/core/core/src/services/auth/index.ts` | Authentication strategy system | Multi-strategy auth (JWT, etc.) |
| 15 | `packages/core/core/src/services/entity-validator/index.ts` | Yup-based entity validation | Validation pipeline for all entity operations |
| 16 | `packages/core/core/src/middlewares/errors.ts` | Error handling middleware | ApplicationError/HttpError handling pattern |
| 17 | `packages/core/core/src/factories.ts` | Core controller/service/router factories | Factory pattern for auto-generated CRUD |
| 18 | `packages/core/core/src/registries/index.ts` | All registry exports | Shows all registry types (content-types, services, controllers, etc.) |
| 19 | `packages/core/database/src/entity-manager/entity-repository.ts` | Entity repository (find, create, update, delete) | Database CRUD abstraction |
| 20 | `packages/core/database/src/index.ts` | Database class (Knex initialization, migrations, entity manager) | Database layer entry point |
| 21 | `packages/core/content-manager/server/src/controllers/collection-types.ts` | Content-manager collection type controller | Admin API CRUD with permissions, draft/publish |
| 22 | `packages/core/content-manager/server/src/services/document-manager.ts` | Document manager service | Admin-level document operations (find, create, update, publish, unpublish, clone) |
| 23 | `packages/core/admin/server/src/controllers/admin.ts` | Admin controller (init, info, plugins, telemetry) | Admin panel backend API |
| 24 | `packages/core/admin/admin/src/core/store/configure.ts` | Redux store configuration | Admin frontend state management |
| 25 | `packages/core/admin/admin/src/core/apis/Plugin.ts` | Plugin API for admin frontend | Frontend plugin injection system |
| 26 | `packages/core/types/src/modules/documents/index.ts` | Document service type definitions | Type system for document service |
| 27 | `packages/core/permissions/src/index.ts` | Permission engine | Action/condition-based permission system |

---

### 4. DEPENDENCY GRAPH

**Module-Level Dependencies** (top-level packages):

```
packages/core/core (Strapi engine)
  ├── packages/core/database (Knex ORM)
  ├── packages/core/types (TypeScript types)
  ├── packages/core/permissions (permission engine)
  ├── packages/core/logger (logging)
  └── packages/utils/typescript (TS utils)

packages/core/strapi (CLI)
  └── packages/core/core (uses Strapi class)

packages/core/admin (Admin panel)
  ├── packages/core/core (server-side)
  └── React + Redux (frontend)

packages/core/content-manager (Plugin)
  ├── packages/core/core (server-side)
  └── packages/core/admin (frontend injection)

packages/plugins/* (Official plugins)
  └── packages/core/core (server-side)
```

**File-Level Dependencies** (key files):

```
Strapi.ts
  ├── container.ts (Container base class)
  ├── configuration/index.ts (config loading)
  ├── services/server/index.ts (Koa server)
  ├── services/entity-service/index.ts (entity CRUD)
  ├── services/document-service/index.ts (document CRUD)
  ├── services/entity-validator/index.ts (validation)
  ├── services/content-api/index.ts (REST API layer)
  ├── services/auth/index.ts (auth strategies)
  ├── services/fs/index.ts (file system)
  ├── services/event-hub/index.ts (event system)
  ├── services/metrics/index.ts (telemetry)
  ├── services/config/index.ts (config provider)
  ├── services/features/index.ts (feature flags)
  ├── services/custom-fields/index.ts
  ├── services/reloader/index.ts
  ├── services/request-context/index.ts
  ├── services/query-params/index.ts
  ├── services/content-source-maps/index.ts
  ├── providers/index.ts (internal providers)
  ├── factories.ts (core factories)
  └── utils/index.ts (utilities)

loaders/index.ts
  ├── loaders/src-index.ts (user's src/index)
  ├── loaders/sanitizers.ts
  ├── loaders/validators.ts
  ├── loaders/plugins/index.ts (plugin loading)
  ├── loaders/apis.ts (API loading)
  ├── loaders/components.ts
  ├── loaders/middlewares.ts
  └── loaders/policies.ts

content-manager/server/src/controllers/collection-types.ts
  ├── content-manager/server/src/services/document-manager.ts
  ├── content-manager/server/src/services/permission-checker.ts
  ├── content-manager/server/src/services/populate-builder.ts
  └── core/core/src/services/document-service/index.ts (strapi.documents)
```

**Call Graph** (request flow):

```
HTTP Request
  → Koa Middleware Chain (cors, body, compression, errors, ...)
    → Router match
      → Content API / Admin API route handler
        → Controller method (e.g., collection-types.find)
          → Permission checker (can user do this?)
            → Document Manager / Entity Service
              → Database query (Entity Repository)
                → Knex query builder
                  → SQL execution
```

---

### 5. CONVENTIONS

**Naming Conventions** (from codebase analysis):

1. **PascalCase for classes and types**: `Strapi`, `Container`, `Database`, `EntityRepository`
2. **camelCase for methods, functions, and variables**: `findMany()`, `createService()`, `loadAPIs()`
3. **kebab-case for file names and API names**: `collection-types.ts`, `entity-repository.ts`, `content-type-builder`
4. **UPPER_SNAKE_CASE for constants**: `CREATED_AT_ATTRIBUTE`, `PUBLISHED_AT_ATTRIBUTE`, `LIMITED_EVENTS`
5. **`I` prefix for interfaces**: Not used — Strapi uses plain type/interface names without `I` prefix
6. **Suffix `Service` for service modules**: `entity-service`, `document-service`, `entity-validator`
7. **Suffix `Controller` for controller modules**: `collection-types`, `single-types`, `admin`, `authentication`
8. **Suffix `Middleware` for middleware modules**: `errors`, `cors`, `body`, `compression`
9. **Suffix `Provider` for provider classes**: `providers-registry`, database providers
10. **Suffix `Repository` for repository classes**: `entity-repository`, `codemod-repository`
11. **Suffix `Validator` for validator modules**: `entity-validator`, `common-validators`
12. **Suffix `Manager` for manager services**: `document-manager`, `session-manager`
13. **Suffix `Builder` for builder services**: `populate-builder`, `content-type-builder`
14. **UID-based naming for content types**: `api::api-name.content-type-name`, `plugin::plugin-name.content-type-name`

**Architectural Patterns**:
- **DI Container**: `Container` class with `.add(name, resolver)` and `.get(name)` — lazy singleton resolution
- **Factory Pattern**: `factories.createCoreController()`, `factories.createCoreService()`, `factories.createCoreRouter()`
- **Registry Pattern**: Named registries (`content-types`, `services`, `controllers`, `policies`, `middlewares`, `plugins`, `apis`, `modules`, `sanitizers`, `validators`)
- **Plugin Lifecycle**: Each plugin module exports `{ register, bootstrap, destroy }` functions
- **Middleware Pipeline**: Koa-style async middleware `(ctx, next) => { ... await next() }`
- **Strategy Pattern**: Auth strategies, upload providers, email providers
- **Decorator Pattern**: Entity service uses `decorate()` for extending functionality
- **Error Handling**: Custom error classes (`ApplicationError`, `HttpError`) with format middleware

**Style Conventions**:
- **Async/Await**: All I/O operations use async/await
- **Error Handling**: try/catch with custom error classes, centralized error middleware
- **Validation**: Yup schemas for entity validation, Zod for content API query params
- **TypeScript**: Strict mode, extensive use of generics and utility types
- **Testing**: Jest for unit tests, custom test app setup for integration tests
- **Module System**: ES modules (import/export) for TypeScript, CommonJS (require) for JavaScript

---

### 6. SIMILAR IMPLEMENTATIONS

| Class/Module | File | Why Similar |
|---|---|---|
| **`collection-types` controller** | `packages/core/content-manager/server/src/controllers/collection-types.ts` | Core controller pattern — follows same find/findOne/create/update/delete structure as `core-api/controller/collection-type.ts` |
| **`single-types` controller** | `packages/core/content-manager/server/src/controllers/single-types.ts` | Same controller pattern as collection-types but for single types |
| **`document-manager` service** | `packages/core/content-manager/server/src/services/document-manager.ts` | Service layer wrapping `strapi.documents()` — same pattern as `entity-service` |
| **`admin` controller** | `packages/core/admin/server/src/controllers/admin.ts` | Admin controller following same Koa context pattern |
| **`authentication` controller** | `packages/core/admin/server/src/controllers/authentication.ts` | Auth controller using same `ctx` pattern |
| **`upload` plugin** | `packages/core/upload/server/src/index.ts` | Plugin structure identical to content-manager (register, bootstrap, config, routes, controllers, services, contentTypes) |
| **`i18n` plugin** | `packages/plugins/i18n/server/src/index.ts` | Same plugin export pattern |
| **`users-permissions` plugin** | `packages/plugins/users-permissions/server/` | Same plugin structure (controllers, services, routes, bootstrap, content-types) |
| **`entity-repository`** | `packages/core/database/src/entity-manager/entity-repository.ts` | Repository pattern — findOne/findMany/create/update/delete — mirrored by document service |
| **`core-service`** | `packages/core/core/src/core-api/service/core-service.ts` | Base service that auto-generated services extend |

---

### 7. TASK CONTEXT

**For an AI performing code review on this project:**

**What this project is**: Strapi is a large, mature open-source headless CMS. It's a monorepo with ~5900 files, primarily TypeScript. The core engine is in `packages/core/core/`, with plugins, providers, and admin panel as separate packages.

**Key systems to understand**:

1. **Lifecycle System** (`Strapi.ts`): The `Strapi` class extends `Container` (DI container). Lifecycle: constructor → `register()` → `bootstrap()` → `listen()`. Plugins and user code hook into `register` and `bootstrap` phases.

2. **DI Container** (`container.ts`): Simple lazy singleton container. `.add(name, resolver)` registers a service; `.get(name)` resolves it once and caches. All core services (db, server, entityService, documents, etc.) are registered this way.

3. **Plugin System**: Each plugin exports `{ register, bootstrap, destroy, controllers, services, routes, policies, contentTypes, config }`. Plugins are loaded from `packages/` and user's `src/extensions/`.

4. **Document Service** (new) vs **Entity Service** (deprecated): The document service (`strapi.documents(uid)`) is the newer API supporting draft/publish, localization, and versioning. Entity service is marked deprecated.

5. **Core API Factories** (`factories.ts`): `createCoreController()`, `createCoreService()`, `createCoreRouter()` auto-generate CRUD for content types. User controllers/services can extend these.

6. **Admin Panel**: React SPA with Redux store, plugin injection via `Plugin` API class, custom fields, widgets. Uses `@strapi/design-system` for UI.

7. **Database Layer**: Knex-based with support for SQLite, PostgreSQL, MySQL, MariaDB. Entity manager handles relations, morphs, components. Schema sync handles migrations.

8. **Permission System**: Action-based permissions with conditions. Content API permissions auto-register from controller actions.

**What to look for in code review**:
- **Consistency**: Do new modules follow the established patterns (plugin lifecycle, controller/service structure, naming conventions)?
- **Error handling**: Are errors properly caught and formatted through the error middleware?
- **TypeScript usage**: Are types properly imported from `@strapi/types`? Are generics used correctly?
- **Async lifecycle**: Are all lifecycle methods (register, bootstrap, destroy) properly async?
- **DI usage**: Are services accessed via `strapi.get('name')` or `strapi.serviceName` getters?
- **Deprecation**: Is entity service being used where document service should be used?
- **Plugin structure**: Does the plugin export the correct shape? Does it handle config validation?

---

### 8. RELEVANT CODE SNIPPETS

**Snippet 1: Strapi class lifecycle and DI registration** (`packages/core/core/src/Strapi.ts`, lines 259-303)
```typescript
registerInternalServices() {
    const config = createConfigProvider(this.internal_config, this);
    // ...
    this.add('config', () => config)
      .add('query-params', createQueryParamService(this))
      .add('content-api', createContentAPI(this))
      .add('auth', createAuth())
      .add('server', () => createServer(this))
      .add('entityService', () => createEntityService({ strapi: this, db: this.db }))
      .add('documents', () => createDocumentService(this))
      .add('db', () => { /* ... */ return new Database(...) })
      // ... more services
}
```
**Why relevant**: Shows the DI container pattern — all core services are registered as lazy factories. Services are accessed via `strapi.get('name')` or convenience getters like `strapi.documents`.

**Snippet 2: Plugin export structure** (`packages/core/content-manager/server/src/index.ts`, lines 1-19)
```typescript
import register from './register';
import bootstrap from './bootstrap';
import destroy from './destroy';
import routes from './routes';
import policies from './policies';
import controllers from './controllers';
import services from './services';

export default () => {
  return {
    register,
    bootstrap,
    destroy,
    controllers,
    routes,
    policies,
    services,
  };
};
```
**Why relevant**: Canonical plugin shape. Every plugin must export a function returning this structure. The upload plugin also includes `config` and `contentTypes`.

**Snippet 3: Core API controller pattern** (`packages/core/core/src/core-api/controller/collection-type.ts`, lines 1-20)
```typescript
async find(ctx) {
  await this.validateQuery(ctx);
  await this.sanitizeQuery(ctx);

  const { query } = ctx;
  const sanitizedQuery = await this.sanitizeQuery(ctx);
  const results = await this.service.find(sanitizedQuery);
  const sanitizedResults = await this.sanitizeOutput(results, ctx);

  return this.transformResponse(sanitizedResults, { pagination });
}
```
**Why relevant**: Shows the standard controller flow: validate → sanitize → service call → sanitize output → transform response. This pattern is used across all controllers.

**Snippet 4: Error handling middleware** (`packages/core/core/src/middlewares/errors.ts`, lines 1-11)
```typescript
return async (ctx, next) => {
  try {
    await next();
    if (!ctx.response._explicitStatus) {
      ctx.notFound();
    }
  } catch (error) {
    if (error instanceof errors.ApplicationError) {
      return ctx.send(formatApplicationError(error));
    }
    if (error instanceof errors.HttpError) {
      return ctx.send(formatHttpError(error));
    }
    ctx.internalServerError(formatInternalError(error));
  }
};
```
**Why relevant**: Centralized error handling pattern. All errors flow through this middleware. Custom error classes (`ApplicationError`, `HttpError`) are formatted differently from unexpected errors.

**Snippet 5: Document service middleware pattern** (`packages/core/core/src/services/document-service/index.ts`, lines 1-10)
```typescript
createMiddlewareManager()
use(databaseErrorsMiddleware)
function factory(uid: UID.ContentType) {
  if (repositories.has(uid)) return get(uid);
  const contentType = strapi.contentType(uid);
  const repository = createContentTypeRepository(uid, validator);
  const instance = wrapObject(repository, { uid, contentType }, {
    exclude: ['updateComponents', 'omitComponentData'],
  });
  set(uid, instance);
  return instance;
}
assign(factory, {
  utils: { transformData },
  use: middlewares.use.bind(middlewares),
});
```
**Why relevant**: Shows the document service factory pattern — per-content-type repository instances with middleware support. The `.use()` method allows adding middleware for all document operations.