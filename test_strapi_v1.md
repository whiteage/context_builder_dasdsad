Now I have enough context to produce the comprehensive architecture analysis. Let me compile everything.

---

## Project Summary

**Strapi** is an open-source headless CMS built with **TypeScript** (3,606 files) and **JavaScript** (824 files), totaling **5,908 files** across a monorepo structure managed with Yarn workspaces. The project follows a **Modular Monolith** architecture with a plugin ecosystem, organized into core packages, plugins, providers, and CLI tools.

The monorepo is organized under `packages/`:
- **packages/core/**: Core modules (strapi, core, admin, database, content-manager, content-type-builder, content-releases, data-transfer, email, openapi, permissions, review-workflows, types, upload, utils)
- **packages/plugins/**: Official plugins (cloud, color-picker, documentation, graphql, i18n, sentry, users-permissions)
- **packages/providers/**: Email and upload provider implementations
- **packages/cli/**: CLI tools (cloud, create-strapi, create-strapi-app)
- **packages/generators/**: Code generators
- **packages/utils/**: Shared utilities

---

## Architecture

### Architecture Type: **Modular Monolith with Plugin Architecture**

Strapi uses a **layered architecture** with a **Service Container** (IoC) pattern at its core. The system is built around:

### Layers

| Layer | Responsibility | Key Packages |
|-------|---------------|--------------|
| **Core Kernel** | Application lifecycle, service container, configuration | `packages/core/core/` |
| **CLI Layer** | Command-line interface, dev/build/start commands | `packages/core/strapi/src/cli/` |
| **Database Layer** | ORM, query builder, migrations, entity management | `packages/core/database/` |
| **Content API Layer** | REST API routing, sanitization, validation | `packages/core/core/src/services/content-api/` |
| **Document Service** | New V5 document CRUD with draft/publish, i18n | `packages/core/core/src/services/document-service/` |
| **Entity Service** | Legacy CRUD (deprecated in V5) | `packages/core/core/src/services/entity-service/` |
| **Admin Panel** | React SPA admin interface | `packages/core/admin/` |
| **Plugin System** | Plugin loading, lifecycle hooks, extensions | `packages/core/core/src/loaders/plugins/` |
| **Permissions** | RBAC, authentication strategies | `packages/core/permissions/` |
| **Data Transfer** | Import/export of content | `packages/core/data-transfer/` |
| **Types** | Shared TypeScript type definitions | `packages/core/types/` |

### Key Architectural Patterns

1. **Service Container (IoC)**: `Container` class with `add()`/`get()` pattern — services are lazily instantiated
2. **Plugin Architecture**: Each plugin exposes `register()`, `bootstrap()`, `destroy()` lifecycle hooks
3. **Middleware Pipeline**: Koa-based HTTP middleware + document service middleware chain
4. **Event Hub**: Pub/sub event system for lifecycle events
5. **Decorator Pattern**: Entity Service uses decorators for extensibility
6. **Repository Pattern**: Database layer uses entity repositories
7. **CQRS-like**: Document Service separates read (findMany/findOne) from write (create/update/delete)

---

## Key Files

### 1. `packages/core/core/src/Strapi.ts`
**The main application class.** Extends `Container` (IoC container). Manages the entire lifecycle: constructor → register → bootstrap → listen → destroy. Registers all internal services (config, logger, server, db, eventHub, entityService, documents, etc.). Provides accessors for all modules (e.g., `strapi.db`, `strapi.documents(uid)`, `strapi.contentTypes`).

### 2. `packages/core/core/src/container.ts`
**IoC Service Container.** Simple `Map`-based container with lazy initialization. `add(name, resolver)` registers a service; `get(name)` resolves it (calling the factory function once, caching the result).

### 3. `packages/core/core/src/services/document-service/index.ts`
**Document Service Factory.** Creates per-content-type repositories with middleware support. The primary API for V5 content operations. Returns a factory function `strapi.documents(uid)` that returns a `ServiceInstance` with CRUD methods.

### 4. `packages/core/core/src/services/document-service/repository.ts`
**Document Repository Implementation.** Contains the actual CRUD logic: `findMany`, `findOne`, `create`, `update`, `delete`, `publish`, `unpublish`, `clone`, `discardDraft`. Uses a pipeline of transformations (validation → draft/publish → i18n → documentId → query params) before executing DB queries.

### 5. `packages/core/database/src/index.ts`
**Database class.** Wraps Knex.js. Manages dialect, connection pool, metadata, migrations, schema sync, entity manager, lifecycles, and query builder. Key methods: `init()`, `query(uid)`, `transaction()`.

### 6. `packages/core/core/src/loaders/index.ts`
**Application Context Loader.** Orchestrates loading of all modules: `loadSrcIndex`, `loadSanitizers`, `loadValidators`, `loadPlugins`, `loadAPIs`, `loadComponents`, `loadMiddlewares`, `loadPolicies`.

### 7. `packages/core/core/src/loaders/apis.ts`
**API Loader.** Scans `src/api/` directories, loads content-types, controllers, services, routes, policies, middlewares for each API. Validates content type name uniqueness.

### 8. `packages/core/core/src/loaders/plugins/index.ts`
**Plugin Loader.** Loads enabled plugins, applies user extensions, formats content types, registers plugin lifecycle hooks.

### 9. `packages/core/core/src/services/server/index.ts`
**HTTP Server.** Creates Koa app, router, and HTTP server. Manages route registration, middleware initialization, and content API + admin API routing.

### 10. `packages/core/core/src/services/event-hub.ts`
**Event Hub.** Pub/sub system with `emit()`, `on()`, `off()`, `once()`, `subscribe()`, `unsubscribe()`. Used for lifecycle events and webhook triggers.

### 11. `packages/core/core/src/services/content-api/index.ts`
**Content API Service.** Manages REST API routes for content types. Handles sanitization, validation, permissions registration, and route prefixing.

### 12. `packages/core/core/src/factories.ts`
**Core API Factories.** `createCoreController()`, `createCoreService()`, `createCoreRouter()` — factory functions that generate default CRUD implementations for content types.

### 13. `packages/core/content-manager/server/src/services/document-manager.ts`
**Content Manager Document Service.** Wraps the core Document Service with content-manager-specific logic (permission checking, deep populate, locale handling).

### 14. `packages/core/content-manager/server/src/controllers/collection-types.ts`
**Content Manager Collection Type Controller.** Handles admin panel CRUD requests with permission checking, sanitization, and draft/publish support.

### 15. `packages/core/admin/admin/src/StrapiApp.tsx`
**Admin Panel Application.** React app that manages plugin registration, routing, RBAC, custom fields, widgets, and theme configuration.

### 16. `packages/core/core/src/ee/index.ts`
**Enterprise Edition Manager.** Handles license verification, online/offline license checks, feature flag management.

### 17. `packages/core/core/src/services/auth/index.ts`
**Authentication Service.** Strategy-based authentication with `register()`, `authenticate()`, `verify()` methods.

### 18. `packages/core/core/src/services/core-store.ts`
**Core Store.** Key-value store backed by the database. Used for storing configuration, content type schemas, and EE information.

### 19. `packages/core/core/src/services/cron.ts`
**Cron Service.** Schedules and manages cron jobs using `node-cron`.

### 20. `packages/core/types/src/index.ts`
**Type Definitions.** Exports all shared types: `Core`, `Modules`, `Schema`, `UID`, `Struct`, `Data`, `Plugin`, etc.

---

## Key Symbols

### Core Classes

| Class | File | Description |
|-------|------|-------------|
| `Strapi` | `packages/core/core/src/Strapi.ts` | Main application class, extends `Container` |
| `Container` | `packages/core/core/src/container.ts` | IoC service container with lazy resolution |
| `Database` | `packages/core/database/src/index.ts` | Database abstraction over Knex.js |

### Key Interfaces (from `@strapi/types`)

| Interface | Module | Description |
|-----------|--------|-------------|
| `Core.Strapi` | `packages/core/types/src/core/` | Main Strapi interface |
| `Modules.Documents.Service` | `packages/core/types/src/modules/documents/` | Document service factory |
| `Modules.Documents.ServiceInstance` | `packages/core/types/src/modules/documents/service-instance.ts` | Per-content-type document CRUD |
| `Modules.EntityService.EntityService` | `packages/core/types/src/modules/entity-service/` | Legacy entity service (deprecated) |
| `Modules.Server.Server` | `packages/core/types/src/modules/server.ts` | HTTP server interface |
| `Modules.EventHub.EventHub` | `packages/core/types/src/modules/event-hub.ts` | Event pub/sub |
| `Schema.ContentType` | `packages/core/types/src/schema/` | Content type schema definition |

### Key Functions

| Function | File | Description |
|----------|------|-------------|
| `createStrapi()` | `packages/core/core/src/index.ts` | Creates and returns a Strapi instance |
| `createCoreController()` | `packages/core/core/src/factories.ts` | Generates default controller for a content type |
| `createCoreService()` | `packages/core/core/src/factories.ts` | Generates default service for a content type |
| `createCoreRouter()` | `packages/core/core/src/factories.ts` | Generates default routes for a content type |
| `loadApplicationContext()` | `packages/core/core/src/loaders/index.ts` | Loads all modules into the Strapi instance |
| `createDocumentService()` | `packages/core/core/src/services/document-service/index.ts` | Creates the document service factory |

### Lifecycle Methods (on Strapi)

| Method | Description |
|--------|-------------|
| `strapi.start()` | Calls `load()` then `listen()` |
| `strapi.load()` | Calls `register()` then `bootstrap()` |
| `strapi.register()` | Initializes EE, runs plugin/user register lifecycles |
| `strapi.bootstrap()` | Initializes DB, syncs schemas, sets up middleware/routing |
| `strapi.destroy()` | Runs destroy lifecycles, shuts down server/DB |
| `strapi.listen()` | Starts the HTTP server |

---

## Dependencies

### Module-Level Dependencies

```
@strapi/strapi (CLI entry point)
  └── @strapi/core (core kernel)
        ├── @strapi/database (ORM)
        ├── @strapi/types (type definitions)
        ├── @strapi/logger (logging)
        ├── @strapi/permissions (RBAC)
        └── @strapi/typescript-utils (TS support)

@strapi/admin (admin panel)
  └── @strapi/core

@strapi/content-manager (admin plugin)
  └── @strapi/core (uses document service, entity service)

@strapi/content-type-builder (admin plugin)
  └── @strapi/core

Plugins (users-permissions, graphql, i18n, etc.)
  └── @strapi/core
```

### Key File Dependencies

**`Strapi.ts` imports:**
- `@strapi/logger` — Logger creation
- `@strapi/database` — Database class
- `@strapi/typescript-utils` — TS config resolution
- `./configuration` — Config loading
- `./container` — IoC container
- `./services/*` — All internal services (server, fs, event-hub, entity-service, document-service, etc.)
- `./providers` — Provider lifecycle hooks

**`document-service/repository.ts` imports:**
- `@strapi/database` — DB query
- `./transform/*` — Data transformation pipeline
- `./middlewares` — Middleware manager
- `../entity-validator` — Validation

**`loaders/apis.ts` imports:**
- Filesystem operations
- Content type validation
- Module domain logic

---

## Conventions

### Naming Conventions

Based on the codebase analysis:

1. **PascalCase** for classes and interfaces: `Strapi`, `Container`, `Database`, `EventHub`
2. **camelCase** for methods, functions, and variables: `createStrapi()`, `loadApplicationContext()`, `findMany()`
3. **UPPER_SNAKE_CASE** for constants: `PUBLISHED_AT_ATTRIBUTE`, `ALLOWED_QUERY_PARAM_KEYS`
4. **kebab-case** for file names and API names: `content-type-builder`, `collection-types.ts`, `entity-repository.ts`
5. **No prefix for interfaces** (unlike C# `I` prefix): `Core.Strapi`, `Modules.Documents.Service`
6. **Suffix conventions**:
   - `Service` suffix for service modules: `EntityService`, `DocumentService`, `FeaturesService`
   - `Controller` suffix for controllers: `CollectionTypeController`, `SingleTypeController`
   - `Repository` suffix for repositories: `EntityRepository`, `ContentTypeRepository`
   - `Manager` suffix for managers: `EntityManager`, `MiddlewareManager`, `SessionManager`
   - `Provider` suffix for providers: `LifecyclesProvider`, `MigrationsProvider`
   - `Validator` suffix for validators: `EntityValidator`
   - `Middleware` suffix for middleware: `DatabaseErrorsMiddleware`

### Architectural Patterns

1. **Service Container (IoC)**: All services are registered via `container.add(name, factory)` and lazily resolved via `container.get(name)`. The `Strapi` class extends `Container`.

2. **Factory Functions**: Most services are created via factory functions: `createDocumentService()`, `createEntityService()`, `createEventHub()`, `createServer()`

3. **Middleware Pipeline**: Two middleware systems:
   - **Koa middleware** for HTTP request/response pipeline
   - **Document Service middleware** for document CRUD operations (e.g., `databaseErrorsMiddleware`)

4. **Lifecycle Hooks**: Plugins and user code can hook into `register`, `bootstrap`, `destroy` lifecycle events.

5. **Event Hub (Pub/Sub)**: `eventHub.emit()`, `eventHub.on()`, `eventHub.subscribe()` for decoupled event handling.

6. **Strategy Pattern**: Authentication uses strategies with `authenticate()` and `verify()` methods.

7. **Decorator Pattern**: Entity Service supports decorators for extending functionality.

8. **Pipeline/Composition**: Document Service uses `async.pipe()` to compose transformation functions (validation → draft/publish → i18n → query params).

### Style Conventions

1. **Async/Await**: All I/O operations use `async/await`
2. **Error Handling**: Custom error classes (`ValidationError`, `ForbiddenError`, `UnauthorizedError`, `LicenseCheckError`)
3. **Validation**: Uses `yup` for schema validation (content types, modules, config)
4. **Functional Programming**: Heavy use of `lodash/fp` (`pipe`, `curry`, `assoc`, `omit`, `pick`, `mapValues`)
5. **TypeScript**: Strict typing with extensive use of generics, conditional types, and template literal types
6. **Dependency Injection**: Services receive `strapi` instance as context parameter
7. **Configuration**: Deeply nested config objects merged from multiple sources (defaults, files, env)

---

## Similar Implementations

### 1. Similar to `Strapi` class (main application class)

**`Container`** (`packages/core/core/src/container.ts`) — The base class that `Strapi` extends. Both use the `add()`/`get()` pattern for service registration and lazy resolution.

**`Database`** (`packages/core/database/src/index.ts`) — Like `Strapi`, it has an `init()` lifecycle, manages internal services (entity manager, lifecycles, migrations), and provides a query interface.

### 2. Similar to `createDocumentService()` (factory pattern)

**`createEntityService()`** (`packages/core/core/src/services/entity-service/index.ts`) — Both are factory functions that create service instances with CRUD operations. Both support decorators/middleware. The Document Service is the V5 replacement for Entity Service.

**`createServer()`** (`packages/core/core/src/services/server/index.ts`) — Both are factory functions that create complex service objects with multiple internal components (router, middleware, lifecycle management).

### 3. Similar to `createCoreController()` (content type factory)

**`createCoreService()`** (`packages/core/core/src/factories.ts`) — Both follow the same pattern: accept a content type UID, create a base implementation, merge with user-defined overrides, and return the composed object.

**`createCoreRouter()`** (`packages/core/core/src/factories.ts`) — Same factory pattern for generating default routes based on content type schema.

---

## Context for the Task

### Architecture Summary

Strapi is a **headless CMS** built as a **Modular Monolith** with a **plugin ecosystem**. The core is a **Service Container (IoC)** pattern where the `Strapi` class (extending `Container`) manages the entire application lifecycle:

1. **Construction**: Load configuration, register internal services (config, logger, server, db, eventHub, entityService, documents)
2. **Registration** (`register()`): Initialize EE, run plugin/user register lifecycles
3. **Bootstrapping** (`bootstrap()`): Initialize database, sync schemas, set up middleware/routing, run plugin/user bootstrap lifecycles
4. **Listening** (`listen()`): Start HTTP server
5. **Destruction** (`destroy()`): Run destroy lifecycles, shut down server/DB

### Key Code Patterns

**Service Container Pattern** (from `container.ts`):
```typescript
class Container {
  private serviceMap = new Map();
  private registerMap = new Map();

  add(name: string, resolver: unknown) {
    this.registerMap.set(name, resolver);
    return this;
  }

  get(name: string, args?: unknown) {
    if (this.serviceMap.has(name)) return this.serviceMap.get(name);
    const resolver = this.registerMap.get(name);
    if (typeof resolver === 'function') {
      const instance = resolver(this, args);
      this.serviceMap.set(name, instance);
      return instance;
    }
    return resolver;
  }
}
```

**Document Service Pipeline** (from `repository.ts`):
```typescript
async function findMany(params = {} as any) {
  const query = await async.pipe(
    validateParams,
    DP.defaultToDraft,
    DP.statusToLookup(contentType),
    i18n.defaultLocale(contentType),
    i18n.multiLocaleToLookup(contentType),
    transformParamsDocumentId(uid),
    transformParamsToQuery(uid)
  )(params || {});
  return strapi.db.query(uid).findMany(query);
}
```

**Plugin Lifecycle** (from `loaders/plugins/index.ts`):
```typescript
// Each plugin exports a strapi-server.js with:
export default () => ({
  register({ strapi }) { /* ... */ },
  bootstrap({ strapi }) { /* ... */ },
  destroy({ strapi }) { /* ... */ },
  contentTypes: { /* ... */ },
  services: { /* ... */ },
  controllers: { /* ... */ },
  routes: { /* ... */ },
  config: { /* ... */ },
  policies: { /* ... */ },
  middlewares: { /* ... */ },
});
```

### Main Systems

1. **Core Kernel** (`@strapi/core`): Application lifecycle, IoC container, configuration, loaders
2. **Database Layer** (`@strapi/database`): Knex-based ORM with entity manager, migrations, schema sync, lifecycles
3. **Document Service**: V5 CRUD API with draft/publish, i18n, middleware pipeline
4. **Content API**: REST API routing with sanitization, validation, permissions
5. **Admin Panel**: React SPA with plugin registration, RBAC, custom fields
6. **Plugin System**: Lifecycle hooks, content type extensions, route registration
7. **CLI**: Commands for develop, build, start, admin management, data transfer
8. **Enterprise Edition**: License verification, feature flags, premium plugins (review-workflows, content-releases)