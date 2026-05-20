I now have comprehensive information. Here is the architecture analysis.

---

## Architecture Analysis: Directus

### 1. PROJECT SUMMARY

Directus is an open-source headless CMS and backend-as-a-service platform. It provides a REST/GraphQL API with a dynamic admin app, supporting any SQL database. The project is a **monorepo** with ~4,069 files (2,792 TypeScript, 562 Vue, 103 JSON, 28 SCSS). It uses pnpm workspaces and is organized into three main deployable units plus ~32 shared packages.

### 2. ARCHITECTURE

Directus follows a **Layered Monolith with Modular Extensions** architecture. The system has three primary layers:

**Layer 1: API (api/) — Backend Server**
- **Controllers** (api/src/controllers/) — Express routers. Handle HTTP request/response. Each controller (items, collections, auth, activity, files, etc.) validates routes, delegates to services, and sends responses. Controllers are thin — they instantiate services and call methods.
- **Middleware** (api/src/middleware/) — Express middleware pipeline: authenticate, cache, CORS, error-handler, extract-token, graphql, rate-limiter, etc. Runs before controllers.
- **Services** (api/src/services/) — Business logic layer. ItemsService (the core CRUD service), AuthenticationService, CollectionsService, ActivityService, etc. Services extend AbstractServiceOptions and receive knex, schema, accountability.
- **Database** (api/src/database/) — Knex.js connection management, schema helpers (per-dialect: PostgreSQL, MySQL, SQLite, MSSQL, Oracle, CockroachDB, Redshift), and the AST-to-SQL engine (run-ast/).
- **Permissions** (api/src/permissions/) — Dynamic permission evaluation. Fetches access policies per user/role, caches them, and filters queries.
- **WebSocket** (api/src/websocket/) — WebSocket handlers for real-time subscriptions, GraphQL over WS, and REST over WS.
- **Auth** (api/src/auth/) — Authentication provider drivers (local, LDAP, OAuth, OpenID).
- **Extensions** (api/src/extensions/) — Extension manager that loads custom bundles, endpoints, hooks.
- **Flows** (api/src/flows.ts) — Automation engine (webhook triggers, scheduled operations).
- **Emitter** (api/src/emitter.ts) — Event system (EventEmitter2) with filter (before) and action (after) hooks. Used by extensions and flows.

**Layer 2: App (app/) — Admin Vue 3 SPA**
- **Modules** (app/src/modules/) — Top-level feature modules (Content, Insights, Settings, Users, Files, etc.). Each module registers routes and components.
- **Components** (app/src/components/) — Reusable UI components (v-avatar, v-button, v-card, v-table, etc.) prefixed with `v-`.
- **Composables** (app/src/composables/) — Vue 3 composables (use-collection, use-alias-fields, use-clipboard, etc.).
- **Stores** (app/src/stores/) — Pinia stores (collections, fields, files, flows, insights, permissions, relations, requests, server, user, etc.).
- **Interfaces/Displays/Layouts/Panels/Operations** — Extension points for custom field inputs, display formats, layout views, dashboard panels, and flow operations.
- **Routes** (app/src/routes/) — Top-level route definitions (login, logout, accept-invite, etc.).
- **API Client** (app/src/api.ts) — Axios-based HTTP client with request queue, token management, and latency tracking.

**Layer 3: SDK (sdk/) — Client SDK**
- REST, GraphQL, Auth, Realtime composable clients.
- Schema types for all system collections.
- Filter/query builders.

**Shared Packages (packages/) — ~32 packages**
- **types** — Core TypeScript interfaces (collections, fields, permissions, flows, etc.).
- **errors** — Error classes (InvalidPayloadError, ForbiddenError, etc.) with error codes.
- **utils** — Shared utilities (node/, browser/, shared/).
- **storage** + **storage-driver-*** — File storage abstraction (local, S3, GCS, Azure, Cloudinary, Supabase).
- **schema** — Database schema inspector (per-dialect).
- **schema-builder** — Schema migration builder.
- **memory** — Cache abstraction (in-memory, Redis).
- **validation** — Validation engine.
- **composables** — Shared Vue composables.
- **env** — Environment variable parsing.
- **extensions** / **extensions-sdk** / **extensions-registry** — Extension system.
- **ai** — AI integration types.
- **themes** — Theme system.
- **system-data** — System collection defaults.

**Dependency Flow (text tree):**

```
HTTP Request
  -> Express Middleware Pipeline (authenticate, cors, rate-limit, cache, extract-token)
    -> Controller (validates route, instantiates Service)
      -> Service (business logic, calls other services)
        -> Database (Knex queries, AST-to-SQL, schema helpers)
        -> Permissions (filters queries by access policies)
        -> Emitter (emitFilter before, emitAction after)
        -> Cache (read/write cache)
  <- Response (JSON with errors array on failure)
```

```
App (Vue SPA)
  -> Pinia Stores (collections, fields, permissions, etc.)
    -> API Client (Axios with queue)
      -> API Backend
  -> Composables (use-collection, use-alias-fields, etc.)
  -> Components (v-*, reusable UI)
  -> Modules (Content, Insights, Settings, etc.)
    -> Interfaces / Displays / Layouts / Panels
```

```
Packages dependency direction:
  types (no deps on other packages)
  errors (depends on types)
  utils (depends on types)
  env (standalone)
  schema (depends on types)
  storage (depends on types)
  memory (standalone)
  validation (depends on errors)
  composables (depends on types, utils)
  stores (depends on types)
  themes (depends on types)
  api -> packages/* (imports types, errors, utils, storage, memory, schema, etc.)
  app -> packages/* (imports types, composables, stores, themes, utils)
  sdk -> packages/types
```

### 3. RELATED FILES (Key Architectural Files)

| File | Path | Entity Type | Role |
|------|------|-------------|------|
| App bootstrap | `api/src/app.ts` | Entry point | Creates Express app, registers all middleware, controllers, serves admin app |
| Items Controller | `api/src/controllers/items.ts` | Controller | Generic CRUD router for any collection — POST/GET/PATCH/DELETE |
| Items Service | `api/src/services/items.ts` | Service | Core CRUD logic: createOne, readByQuery, updateMany, deleteMany, with nested processing |
| Authentication Service | `api/src/services/authentication.ts` | Service | Login, logout, refresh, OTP, session management |
| Database | `api/src/database/index.ts` | Database | Knex connection factory, per-dialect config, query tracing |
| Emitter | `api/src/emitter.ts` | Event System | EventEmitter2 wrapper — emitFilter (before hooks), emitAction (after hooks) |
| Permissions Cache | `api/src/permissions/cache.ts` | Permissions | Redis-backed permission cache with TTL |
| Error Handler | `api/src/middleware/error-handler.ts` | Middleware | Catches all errors, formats as `{ errors: [...] }` JSON |
| Authenticate Middleware | `api/src/middleware/authenticate.ts` | Middleware | Token extraction, accountability creation, permission context |
| App Root | `app/src/app.vue` | Vue App | Root Vue component, theme initialization, idle tracking |
| API Client | `app/src/api.ts` | HTTP Client | Axios instance with request queue, token injection, latency tracking |
| Collections Store | `app/src/stores/collections.ts` | Pinia Store | Hydrates collection metadata, manages CRUD for collections |
| Extensions Loader | `app/src/extensions.ts` | Extension System | Loads custom extensions, registers interfaces/displays/layouts/modules |
| Modules Registry | `app/src/modules/index.ts` | Module System | Registers internal and custom modules with routes |
| Types Package | `packages/types/src/index.ts` | Types | Core interfaces: SchemaOverview, Field, Collection, Permission, etc. |
| Errors Package | `packages/errors/src/index.ts` | Errors | Error hierarchy: DirectusError -> InvalidPayloadError, ForbiddenError, etc. |

### 4. DEPENDENCY GRAPH

**Module-level dependencies:**
```
tests/ -> api
```

**File-level dependency chains (key flows):**

```
HTTP Request flow:
  app.ts (creates Express app)
    -> middleware/authenticate.ts (creates accountability, attaches to req)
    -> middleware/error-handler.ts (catches all errors)
    -> controllers/items.ts (routes /:collection)
      -> services/items.ts (CRUD logic)
        -> database/index.ts (Knex queries)
        -> database/run-ast/index.ts (AST-to-SQL translation)
        -> permissions/cache.ts (check access)
        -> emitter.ts (emitFilter/emitAction hooks)
        -> services/activity.ts (track changes)
        -> services/revisions.ts (track revisions)

Authentication flow:
  controllers/auth.ts
    -> services/authentication.ts
      -> auth/drivers/* (provider-specific login)
      -> services/tfa.ts (2FA)
      -> permissions/modules/fetch-global-access (role/policy resolution)
      -> emitter.ts (auth.login events)

App flow:
  app.vue
    -> stores/* (Pinia stores hydrate on mount)
    -> api.ts (Axios calls to API)
    -> modules/* (route registration)
    -> components/* (UI rendering)
```

**Package dependency chain:**
```
packages/types (foundation, no internal deps)
packages/errors -> types
packages/utils -> types
packages/schema -> types
packages/storage -> types
packages/validation -> errors
packages/memory (standalone)
packages/composables -> types, utils
packages/stores -> types
packages/themes -> types
api -> types, errors, utils, storage, memory, schema, env, validation, etc.
app -> types, composables, stores, themes, utils
sdk -> types
```

### 5. CONVENTIONS

**Naming conventions (from sample_signatures):**
1. **Services end with `Service`**: `ItemsService`, `ActivityService`, `NotificationsService`, `AuthenticationService`, `ExtensionsService`, `CollectionsService`
2. **Controllers are in `controllers/` directory**: `items.ts`, `collections.ts`, `auth.ts`, `activity.ts`, `assets.ts`
3. **Interfaces use PascalCase with descriptive names**: `AbstractServiceOptions`, `SchemaOverview`, `MutationOptions`, `AnyItem`, `Query`
4. **Database helpers use `*Helper` suffix**: `GeometryHelperRedshift`, `SchemaHelperSQLite`, `NumberDatabaseHelper`
5. **Storage drivers use `Driver*` prefix**: `DriverSupabase`, `Driver` (base class)
6. **Error classes use `*Error` suffix**: `InvalidPayloadError`, `InvalidCredentialsError`, `ForbiddenError`, `InvalidOtpError`
7. **Vue components use `v-` prefix**: `v-avatar`, `v-badge`, `v-hover`, `v-banner`
8. **Composables use `use*` prefix**: `use-collection`, `use-alias-fields`, `use-clipboard`, `use-collab`
9. **Pinia stores use `*Store` naming**: `collectionsStore`, `useUserStore`, `usePermissionsStore`
10. **WebSocket handlers use `*Handler` suffix**: `heartbeat`, `items`, `logs`, `subscribe`
11. **WebSocket controllers use `*Controller` suffix**: `base`, `graphql`, `rest`, `logs`
12. **Auth drivers in `auth/drivers/`**: `ldap.ts` (composable pattern)

**Architectural patterns:**
- **Service Layer pattern**: Controllers instantiate services with `AbstractServiceOptions` (containing `knex`, `schema`, `accountability`). Services never touch HTTP directly.
- **Event-driven hooks**: `emitter.ts` provides `emitFilter` (before, can modify payload) and `emitAction` (after, fire-and-forget). Extensions and flows hook into these.
- **Dependency Injection via constructor**: Services receive `AbstractServiceOptions` in constructor. Database is passed as Knex instance (not global).
- **Repository-like pattern**: `ItemsService` acts as a generic repository for any collection, with `createOne`, `readByQuery`, `updateMany`, `deleteMany`.
- **AST-to-SQL**: Queries are parsed into an AST (`FieldNode`, `M2ONode`, `O2MNode`, `A2MNode`) then translated to SQL via `runAst()`.
- **Per-dialect strategy pattern**: Database helpers (`GeometryHelper`, `SchemaHelper`, `NumberDatabaseHelper`) have dialect-specific subclasses.

**Style conventions:**
- **Async everywhere**: All service methods are `async`, use `await` for database operations.
- **Error handling**: Errors are thrown as `DirectusError` subclasses, caught by `error-handler.ts` middleware, returned as `{ errors: [...] }` JSON.
- **Transaction usage**: `transaction(this.knex, async (trx) => ...)` for atomic operations.
- **Validation**: `validateKeys()`, `validateBatch()` middleware, `sanitizeQuery()` for query sanitization.

### 6. SIMILAR IMPLEMENTATIONS

| Class | File | Similarity |
|-------|------|------------|
| `ItemsService` | `api/src/services/items.ts` | Base CRUD service — all other services extend or mirror this pattern |
| `ActivityService` | `api/src/services/activity.ts` | Extends `ItemsService`, same constructor pattern |
| `NotificationsService` | `api/src/services/notifications.ts` | Extends `ItemsService`, same constructor pattern |
| `CollectionsService` | `api/src/services/collections.ts` | Service pattern with `AbstractServiceOptions` constructor |
| `AuthenticationService` | `api/src/services/authentication.ts` | Service pattern, uses `ActivityService` internally |
| `ExtensionsService` | `api/src/services/extensions.ts` | Service pattern with `AbstractServiceOptions` |
| `GeometryHelperRedshift` | `api/src/database/helpers/geometry/dialects/redshift.ts` | Extends `GeometryHelper` — dialect strategy pattern |
| `SchemaHelperSQLite` | `api/src/database/helpers/schema/dialects/sqlite.ts` | Extends `SchemaHelper` — dialect strategy pattern |
| `DriverSupabase` | `packages/storage-driver-supabase/src/index.ts` | Implements `TusDriver` — storage driver pattern |
| `Driver` | `packages/storage/src/index.ts` | Base storage driver class |
| `CacheMulti` | `packages/memory/src/cache/lib/multi.ts` | Implements `Cache` interface — cache strategy pattern |

### 7. TASK CONTEXT

**For an AI performing work on this codebase:**

The project is a **monorepo** with three main deployable units: `api/` (Express backend), `app/` (Vue 3 admin SPA), and `sdk/` (client SDK), plus ~32 shared `packages/`. The architecture is a **layered monolith** with a clear dependency direction: Controllers -> Services -> Database/Permissions/Emitter.

Key architectural decisions to be aware of:
- **Services receive `AbstractServiceOptions`** (knex, schema, accountability) via constructor — never import database globally.
- **Controllers are thin** — they validate routes, instantiate services, call methods, and pass to `respond` or `next`.
- **The event system** (`emitter.ts`) has two hook types: `emitFilter` (before, can modify data) and `emitAction` (after, fire-and-forget). Extensions hook into these.
- **Permissions are dynamic** — evaluated per-request via `permissions/cache.ts`, filtering queries at the database level.
- **Database queries go through AST** — `runAst()` converts request parameters into an AST, then to SQL. This is the core query engine.
- **The app is extension-driven** — interfaces, displays, layouts, panels, modules, and operations are all registered via `defineInterface`, `defineDisplay`, etc.
- **Error handling** is centralized in `error-handler.ts` middleware — all errors are `DirectusError` subclasses with `code`, `status`, `extensions`.
- **Storage is abstracted** via `packages/storage/` with pluggable drivers (local, S3, GCS, Azure, Cloudinary, Supabase).
- **Testing** uses Vitest with shared test utilities in `api/src/test-utils/` (mock knex, database, cache, schema, storage).

### 8. RELEVANT CODE SNIPPETS

**Snippet 1: Service constructor pattern (api/src/services/items.ts)**
```typescript
// Lines ~50-60: All services receive AbstractServiceOptions
constructor(collection: Collection, options: AbstractServiceOptions) {
    this.collection = collection;
    this.knex = options.knex || getDatabase();
    this.schema = options.schema;
    this.accountability = options.accountability;
    // ...
}
```
*Why relevant: Shows the DI pattern used by every service in the codebase.*

**Snippet 2: Controller pattern (api/src/controllers/items.ts)**
```typescript
// Lines ~15-30: Controller instantiates service, calls method, passes to next
post('/:collection', collectionExists, asyncHandler(async (req, res, next) => {
    const service = new ItemsService(req.collection, {
        accountability: req.accountability,
        schema: req.schema,
    });
    // ... call service method, then next()
}));
```
*Why relevant: Shows the thin controller pattern — instantiate service, call method, respond.*

**Snippet 3: Event emitter filter/action pattern (api/src/emitter.ts)**
```typescript
// Lines ~30-50: Two hook types
public async emitFilter(event: string | string[], payload: unknown, meta: Record<string, any>, context: EventContext | null = null) {
    // Before hooks — can modify payload
    const eventListeners = this.filterEmitter.listeners(event);
    for (const listener of eventListeners) {
        const result = await listener(payload, { event, ...meta }, context ?? this.getDefaultContext());
        if (result !== undefined) payload = result;
    }
    return payload;
}

public emitAction(event: string | string[], meta: Record<string, any>, context: EventContext | null = null) {
    // After hooks — fire and forget
    return this.actionEmitter.emitAsync(event, { event, ...meta }, context ?? this.getDefaultContext());
}
```
*Why relevant: Core extensibility mechanism — filters can modify data, actions are notifications.*

**Snippet 4: Error handler middleware (api/src/middleware/error-handler.ts)**
```typescript
// Lines ~10-25: Centralized error formatting
asyncErrorHandler(async (err, req, res) => {
    const errors = [];
    // ... collect errors, format as { message, extensions: { code } }
    res.status(status ?? FALLBACK_ERROR.status);
    res.json({ errors: updatedErrors });
});
```
*Why relevant: All errors flow through here — consistent JSON response format.*

**Snippet 5: App extension registration (app/src/extensions.ts)**
```typescript
// Lines ~30-50: Loads and registers all extension types
export async function loadExtensions() {
    // imports custom extensions from @directus-extensions
}

export function registerExtensions(app: App) {
    registerInterfaces(interfaces, app);
    registerDisplays(displays, app);
    registerLayouts(layouts, app);
    registerModules(modules);
    registerPanels(panels, app);
    registerOperations(operations, app);
    registerThemes(themes);
}
```
*Why relevant: Shows the extension system — everything is pluggable via registration functions.*