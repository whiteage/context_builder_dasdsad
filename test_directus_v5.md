I now have comprehensive data. Let me compile the full analysis.

---

## Code Review: Project Architecture, Systems, and Conventions

### 1. PROJECT SUMMARY

**Project:** Directus — a real-time API and App dashboard for managing SQL database content.

**Tech Stack:**
- **Backend:** Node.js, Express.js, Knex.js (SQL query builder), EventEmitter2
- **Frontend:** Vue 3 (Composition API), Pinia (state management), Vite, SCSS
- **SDK:** TypeScript SDK for API clients
- **Database:** PostgreSQL, MySQL, MariaDB, SQLite, MS SQL Server, OracleDB, CockroachDB
- **Build:** pnpm monorepo, TypeScript, ES modules

**Scale:** 4,068 files total — 2,792 TypeScript, 562 Vue, 103 JSON, 268 YAML, 28 SCSS

**Structure:** Monorepo with 4 main areas:
- `/api` — Node.js backend (REST + GraphQL APIs)
- `/app` — Vue 3 dashboard application
- `/sdk` — TypeScript SDK
- `/packages/*` — 35+ shared packages (types, utils, storage drivers, extensions, errors, env, etc.)

---

### 2. ARCHITECTURE

**Architecture Type:** Layered Monolith with Modular Package Architecture

The project follows a **Controller → Service → Database** layered pattern on the backend, and a **Store → Composable → Component** pattern on the frontend.

**API Layer (`/api/src`):**

| Layer | Directory | Responsibility |
|-------|-----------|---------------|
| **Controllers** | `controllers/` | REST endpoint handlers (40+). Each maps to a resource (items, users, collections, etc.). Uses Express Router. |
| **Services** | `services/` | Business logic. Each service extends `ItemsService` for CRUD or implements custom logic. |
| **Middleware** | `middleware/` | Express middleware chain: authenticate, cache, CORS, rate limiting, sanitize query, error handler |
| **Database** | `database/` | Knex.js connection management, migrations, AST-to-SQL runner |
| **Auth** | `auth/` | Auth providers: local, OAuth2, OpenID, LDAP, SAML |
| **WebSocket** | `websocket/` | Real-time WebSocket support with auth modes (strict, handshake) |
| **Extensions** | `extensions/` | Runtime extension loading and management |
| **Permissions** | `permissions/` | Permission evaluation and caching |
| **Flows** | `flows.ts` | Automation flow engine (event-driven, scheduled, webhook) |
| **Emitter** | `emitter.ts` | Event system (filter/action/init) using EventEmitter2 |

**App Layer (`/app/src`):**

| Layer | Directory | Responsibility |
|-------|-----------|---------------|
| **Components** | `components/` | 145+ Vue components (v-button, v-card, v-input, etc.) |
| **Views** | `views/` | Page-level views (private, public, shared) |
| **Composables** | `composables/` | 53+ Vue composables (use-items, use-relation-*, use-system) |
| **Stores** | `stores/` | 24 Pinia stores (collections, fields, user, permissions, etc.) |
| **Interfaces** | `interfaces/` | 45+ field input types |
| **Displays** | `displays/` | 21 field display renderers |
| **Layouts** | `layouts/` | 8 data layout views |
| **Modules** | `modules/` | Feature modules (routable sections) |
| **Panels** | `panels/` | 14 dashboard panel types |
| **Operations** | `operations/` | 18 flow operation types |

**Shared Packages (`/packages/*`):**

| Package | Purpose |
|---------|---------|
| `@directus/types` | Shared TypeScript types (services, items, schema, etc.) |
| `@directus/utils` | Utilities split into `shared/`, `node/`, `browser/` |
| `@directus/errors` | Error codes and error creation framework |
| `@directus/env` | Environment variable management (`useEnv()`) |
| `@directus/schema` | Database schema inspection |
| `@directus/storage` | Abstract storage interface |
| `@directus/storage-driver-*` | Storage backends (S3, Azure, GCS, Local, Supabase, Cloudinary) |
| `@directus/extensions` | Extension framework |
| `@directus/composables` | Shared Vue composables |
| `@directus/stores` | Shared Pinia stores |
| `@directus/memory` | Memory/lock management |
| `@directus/pressure` | Backpressure handling |
| `@directus/validation` | Validation utilities |
| `@directus/themes` | Theme system |
| `@directus/system-data` | System collection data |

**SDK (`/sdk/src`):**

| Module | Purpose |
|--------|---------|
| `auth/` | Authentication (composable with auto-refresh) |
| `rest/` | REST API client |
| `graphql/` | GraphQL client |
| `realtime/` | WebSocket realtime client |
| `schema/` | TypeScript schema types for all system collections |
| `types/` | Shared types (filters, fields, deep, etc.) |

**Request Flow:**
```
HTTP Request → Express App → Middleware Chain (auth, cache, CORS, rate-limit, sanitize-query, schema)
  → Controller (route handler) → Service (business logic) → Database (Knex queries)
  → Response with `respond` middleware
```

**Event Flow:**
```
Service methods emit filter/action events → Emitter (EventEmitter2) → Flow engine triggers
  → Extension hooks → Cache invalidation
```

---

### 3. RELATED FILES

| # | File | Entity Type | Purpose & Relevance |
|---|------|-------------|---------------------|
| 1 | `api/src/app.ts` | App bootstrap | Central Express app creation. Registers all middleware, controllers, auth providers, extensions, flows. Entry point for understanding the full middleware chain and module registration. |
| 2 | `api/src/controllers/items.ts` | Controller | Generic items CRUD controller. Shows the standard controller pattern: Router(), collectionExists middleware, asyncHandler, ItemsService instantiation, CRUD methods. |
| 3 | `api/src/services/items.ts` | Service | Core ItemsService — base class for most services. Shows CRUD operations, event emission (filter/action), nested processing (M2O, A2O, O2M), activity/revision tracking, mutation tracking. |
| 4 | `api/src/services/access.ts` | Service | Example of a service extending ItemsService with cache clearing overrides. Shows the override pattern for createOne/updateMany/deleteMany. |
| 5 | `api/src/services/permissions.ts` | Service | Another ItemsService extension with cache clearing + custom readByQuery logic. Shows `withAppMinimalPermissions` and `getItemPermissions`. |
| 6 | `api/src/emitter.ts` | System | Event emitter (filter/action/init). Central to the event-driven architecture. Shows how filters can modify payloads and actions fire side effects. |
| 7 | `api/src/cache.ts` | System | Multi-layer caching (Keyv-based). Shows cache-aside pattern with system cache, deployment cache, schema cache, lock cache. |
| 8 | `api/src/middleware/authenticate.ts` | Middleware | Authentication middleware. Shows token extraction, accountability creation, session cookie handling. |
| 9 | `api/src/middleware/error-handler.ts` | Middleware | Global error handler. Shows error serialization, Directus error handling, stack trace exposure in dev. |
| 10 | `api/src/flows.ts` | System | Flow engine. Shows event-driven automation: event listeners, scheduled jobs, webhook handlers, operation execution. |
| 11 | `api/src/extensions/manager.ts` | System | Extension manager. Shows extension loading, sync, watch mode, install/uninstall, bundle generation. |
| 12 | `api/src/auth.ts` | System | Auth provider registry. Shows provider registration pattern (local, OAuth2, OpenID, LDAP, SAML). |
| 13 | `api/src/permissions/index.ts` | System | Permission evaluation engine. Shows policy fetching, permission checking, access validation. |
| 14 | `api/src/websocket/controllers/base.ts` | Controller | WebSocket base controller. Shows upgrade handling, auth modes (strict/handshake), client management. |
| 15 | `api/src/database/index.ts` | Database | Knex database connection management. Shows multi-DB support, connection pooling, query tracing/metrics. |
| 16 | `app/src/stores/collections.ts` | Store | Pinia store for collections. Shows hydrate/dehydrate pattern, API calls via `api` instance, i18n translation. |
| 17 | `app/src/stores/fields.ts` | Store | Pinia store for fields. Shows same hydrate/dehydrate pattern, field CRUD, relation-aware deletion. |
| 18 | `app/src/composables/use-system.ts` | Composable | System composable. Shows dependency injection pattern for stores, API, SDK, extensions via `provide`. |
| 19 | `app/src/hydrate.ts` | System | App hydration. Shows store initialization order, permission-aware hydration, language setup. |
| 20 | `app/src/extensions.ts` | System | Extension registration. Shows interface/display/layout/module/panel/operation registration pattern. |
| 21 | `app/src/api.ts` | System | Axios-based API client. Shows request queue (PQueue), token injection, latency measurement, error handling. |
| 22 | `app/src/interfaces/index.ts` | Registry | Interface registration. Shows `defineInterface` pattern, component registration as `interface-{id}`. |
| 23 | `app/src/displays/index.ts` | Registry | Display registration. Shows `defineDisplay` pattern, component registration as `display-{id}`. |
| 24 | `app/src/layouts/index.ts` | Registry | Layout registration. Shows `defineLayout` pattern with slots (options, sidebar, actions). |
| 25 | `packages/types/src/services.ts` | Types | Service type definitions. Defines `AbstractServiceOptions`, service interfaces (AssetsService, AuthenticationService, etc.). |
| 26 | `packages/errors/src/codes.ts` | Types | Error code enum. All error codes used across the project. |
| 27 | `packages/errors/src/create-error.ts` | System | Error creation framework. Shows the `createError` factory pattern. |
| 28 | `sdk/src/rest/composable.ts` | SDK | REST client composable. Shows request building, token injection, response handling. |
| 29 | `sdk/src/auth/composable.ts` | SDK | Auth composable. Shows login/refresh/logout flow, auto-refresh, token storage. |
| 30 | `AGENTS.md` | Docs | Project conventions, commands, architecture overview, PR requirements. |

---

### 4. DEPENDENCY GRAPH

**Module-Level Dependencies:**

```
api (Express app)
  ├── controllers/ → services/ → database/
  ├── middleware/ → database/, utils/
  ├── websocket/ → auth/, permissions/
  ├── extensions/ → services/, database/
  ├── flows.ts → services/, database/, emitter
  ├── emitter.ts → database/
  ├── cache.ts → database/, bus/
  └── auth.ts → database/, services/

app (Vue 3 app)
  ├── stores/ → api.ts, composables/
  ├── composables/ → stores/, api.ts
  ├── components/ → composables/, stores/
  ├── views/ → components/, composables/
  ├── interfaces/ → components/
  ├── displays/ → components/
  ├── layouts/ → components/
  └── modules/ → views/, components/

packages/
  ├── @directus/types → (no internal deps)
  ├── @directus/utils/shared → @directus/types
  ├── @directus/utils/node → @directus/utils/shared
  ├── @directus/errors → (standalone)
  ├── @directus/env → (standalone)
  ├── @directus/schema → knex
  ├── @directus/storage → (standalone)
  └── @directus/extensions → @directus/types

sdk/
  ├── auth/ → rest/
  ├── rest/ → types/
  ├── graphql/ → types/
  ├── realtime/ → types/
  └── schema/ → types/
```

**File-Level Dependencies (Key Files):**

- `api/src/app.ts` imports: all controllers (40+), all middleware, auth providers, extensions, flows, database, emitter, schedules
- `api/src/controllers/items.ts` imports: `ItemsService`, `MetaService`, middleware (`collectionExists`, `validateBatch`), error types
- `api/src/services/items.ts` imports: database, cache, emitter, `PayloadService`, `ActivityService`, `RevisionsService`, `validateKeys`, `processPayload`
- `api/src/services/access.ts` extends: `ItemsService` (from `./items.js`)
- `api/src/services/permissions.ts` extends: `ItemsService` (from `./items.js`)
- `app/src/stores/collections.ts` uses: `api` (Axios instance), `useRelationsStore`, `useAiToolsStore`, `i18n`
- `app/src/stores/fields.ts` uses: `api`, `useRelationsStore`, `useCollectionsStore`, `i18n`

**Call Graph (Controller → Service flow):**
```
items.ts controller (POST /:collection)
  → ItemsService.createOne(data)
    → emitFilter('items.create', payload)
    → PayloadService.processM2O/A2O/O2M
    → knex.insert()
    → ActivityService.createOne()
    → RevisionsService.createOne()
    → emitAction('items.create', result)
```

---

### 5. CONVENTIONS

**Naming Conventions:**

1. **Controllers** — Named after resource, exported as default: `access.ts` → `accessRouter`, `items.ts` → `itemsRouter`. File: `api/src/controllers/access.ts`, `api/src/controllers/items.ts`
2. **Services** — PascalCase with `Service` suffix: `AccessService`, `ItemsService`, `PermissionsService`, `CollectionsService`, `AuthenticationService`. File: `api/src/services/access.ts`, `api/src/services/items.ts`
3. **Stores (Pinia)** — `use{Name}Store` pattern: `useCollectionsStore`, `useFieldsStore`, `useUserStore`, `usePermissionsStore`. File: `app/src/stores/collections.ts`
4. **Composables (Vue)** — `use{Name}` pattern: `useAliasFields`, `useSystem`, `useRelationM2O`, `useItems`. File: `app/src/composables/use-alias-fields.ts`
5. **Components (Vue)** — `v-{name}` prefix: `v-button`, `v-card`, `v-input`, `v-menu`, `v-dialog`. File: `app/src/components/v-button.vue`
6. **Interfaces** — Registered as `interface-{id}`: `interface-input`, `interface-select`. File: `app/src/interfaces/index.ts`
7. **Displays** — Registered as `display-{id}`: `display-formatted-value`. File: `app/src/displays/index.ts`
8. **Layouts** — Registered as `layout-{id}` with slots: `layout-options-{id}`, `layout-sidebar-{id}`, `layout-actions-{id}`. File: `app/src/layouts/index.ts`
9. **Error codes** — PascalCase enum in `ErrorCode`: `Forbidden`, `InvalidPayload`, `RecordNotUnique`. File: `packages/errors/src/codes.ts`
10. **Test files** — `*.test.ts` placed next to source: `items.test.ts` next to `items.ts`. File: `api/src/services/items.test.ts`
11. **Interfaces (TypeScript)** — No `I` prefix. Plain names: `AbstractServiceOptions`, `ApiError`, `SchemaOverview`. File: `packages/types/src/services.ts`
12. **Async handlers** — Wrapped with `asyncHandler` utility to catch promise rejections. File: `api/src/utils/async-handler.ts`

**Architectural Patterns:**

1. **Service extends ItemsService** — Most services extend `ItemsService` for CRUD, override methods to add cache clearing or custom logic. Example: `AccessService extends ItemsService`, `PermissionsService extends ItemsService`
2. **AbstractServiceOptions** — Constructor pattern: `constructor(options: AbstractServiceOptions)` where options contain `knex`, `accountability`, `schema`, `nested`
3. **Event-driven architecture** — Three event types: `emitFilter` (modify payload), `emitAction` (fire-and-forget side effects), `emitInit` (startup hooks). Uses EventEmitter2.
4. **Cache-aside** — Services check cache before DB, write-through on mutations. `clearCaches()` called after mutations.
5. **Dependency Injection** — Via constructor options. Services receive `knex`, `accountability`, `schema` from controllers.
6. **Transaction-per-mutation** — All mutations wrapped in `transaction(this.knex, async (trx) => ...)`.
7. **Pinia stores with hydrate/dehydrate** — Stores have `hydrate()` and `dehydrate()` lifecycle methods for data loading.
8. **Extension registry pattern** — Interfaces, displays, layouts, modules, panels, operations all follow `getInternal*()` + `register*()` pattern.

**Style Conventions:**

1. **ES modules** — `import/export` with `.js` extensions in source: `import { ItemsService } from './items.js'`
2. **Async/await** — All service methods are async. Controllers use `asyncHandler` wrapper.
3. **Error handling** — Custom errors via `@directus/errors` using `createError` factory. Errors have `ErrorCode` enum. Global error handler catches all.
4. **Validation** — Zod for schema validation (WebSocket auth), Joi for query validation (`validateQuery`), custom validation in services.
5. **Testing** — Vitest with `describe/test` blocks. Mocks via `vi.mock()`. Test utilities in `api/src/test-utils/`.
6. **TypeScript** — Strict mode. Types in `@directus/types` package. Interfaces for service contracts.
7. **Lodash** — Heavy use of `lodash-es` for object manipulation: `merge`, `pick`, `omit`, `cloneDeep`, `isEqual`, `sortBy`.

---

### 6. SIMILAR IMPLEMENTATIONS

| Class | File | Why Similar |
|-------|------|-------------|
| **AccessService** | `api/src/services/access.ts` | Extends `ItemsService`, overrides `createOne`/`updateMany`/`deleteMany` with cache clearing. Same pattern as PermissionsService. |
| **PermissionsService** | `api/src/services/permissions.ts` | Extends `ItemsService`, overrides CRUD methods with cache clearing + custom `readByQuery`. Same pattern as AccessService. |
| **CollectionsService** | `api/src/services/collections.ts` | Extends `ItemsService` (indirectly), complex CRUD with field creation, table creation, nested transactions. |
| **FieldsService** | `api/src/services/fields.ts` | Extends `ItemsService`, field-level CRUD with schema alterations. |
| **FlowsService** | `api/src/services/flows.ts` | Extends `ItemsService`, flow-specific CRUD. |
| **SettingsService** | `api/src/services/settings.ts` | Extends `ItemsService`, singleton read/write pattern. |
| **UsersService** | `api/src/services/users.ts` | Extends `ItemsService`, user-specific logic (invites, TFA, password hashing). |
| **RolesService** | `api/src/services/roles.ts` | Extends `ItemsService`, role management with policy associations. |
| **PoliciesService** | `api/src/services/policies.ts` | Extends `ItemsService`, policy CRUD. |
| **RevisionsService** | `api/src/services/revisions.ts` | Extends `ItemsService`, revision history tracking. |
| **ActivityService** | `api/src/services/activity.ts` | Extends `ItemsService`, activity log. |
| **NotificationsService** | `api/src/services/notifications.ts` | Extends `ItemsService`, notification CRUD. |
| **SharesService** | `api/src/services/shares.ts` | Extends `ItemsService`, share link management. |
| **VersionsService** | `api/src/services/versions.ts` | Extends `ItemsService`, content versioning. |
| **TranslationsService** | `api/src/services/translations.ts` | Extends `ItemsService`, translation management. |

All 15+ services follow the same pattern: extend `ItemsService`, pass collection name to `super()`, override methods as needed.

---

### 7. TASK CONTEXT

**For an AI performing code review on this project:**

**What to look at:**
- The **Controller → Service → Database** layered architecture is strict. Controllers handle HTTP, services handle business logic, database layer handles SQL.
- The **ItemsService** base class (`api/src/services/items.ts`) is the most important file — it defines the CRUD pattern that 15+ services inherit.
- The **emitter** (`api/src/emitter.ts`) is central — filters can modify payloads, actions fire side effects. All service mutations go through this.
- The **cache** (`api/src/cache.ts`) has multiple layers: system cache, deployment cache, schema cache, lock cache. Cache invalidation is manual via `clearCaches()`.
- The **app** uses Pinia stores with `hydrate()`/`dehydrate()` lifecycle. Stores call the API directly via the Axios instance in `app/src/api.ts`.
- **Extensions** are registered via `defineInterface`, `defineDisplay`, `defineLayout`, `defineModule`, `definePanel`, `defineOperation` functions.

**What patterns to follow:**
- Services extend `ItemsService` and pass collection name to `super()`.
- Controllers use `Router()`, `asyncHandler`, and instantiate services with `{ accountability, schema }` from `req`.
- Error handling uses `@directus/errors` with `ErrorCode` enum and `isDirectusError()` checks.
- All mutations use `transaction(this.knex, async (trx) => ...)`.
- Cache clearing after mutations: override `createOne`/`updateMany`/`deleteMany` and call `clearCaches()`.
- Vue components use `v-` prefix, composables use `use-` prefix, stores use `use{Name}Store`.
- Test files are `*.test.ts` next to source files, using Vitest.

**What to be careful about:**
- The `sample_signatures` tool returned no AST data — conventions were extracted from file contents directly.
- The project has 4,068 files — focus on the patterns, not individual files.
- The `api/src/services/items.ts` is 318+ signatures long — it's the most complex file.
- The `api/src/extensions/manager.ts` is 353+ signatures — extension loading is complex.
- The `api/src/flows.ts` is 171+ signatures — the flow engine is event-driven and complex.
- The `api/src/cache.ts` has 81+ signatures — cache invalidation logic is spread across services.
- The `app/src/stores/` have 24 stores — each follows the same hydrate/dehydrate pattern.

---

### 8. RELEVANT CODE SNIPPETS

**Snippet 1: Controller Pattern (api/src/controllers/access.ts)**
```typescript
// Lines 1-15: Standard controller pattern
import { Router } from 'express';
import { asyncHandler } from '../utils/async-handler.js';
import { AccessService } from '../services/access.js';

const router = Router();

router.post(
  '/',
  asyncHandler(async (req, res, next) => {
    const service = new AccessService({
      accountability: req.accountability,
      schema: req.schema,
    });
    // ... CRUD operations
  })
);
```
*Why relevant: Shows the standard controller pattern — Router(), asyncHandler, service instantiation with accountability + schema from request.*

**Snippet 2: Service Extending ItemsService (api/src/services/access.ts)**
```typescript
// Lines 1-15: Service extending ItemsService with cache clearing
export class AccessService extends ItemsService {
  constructor(options: AbstractServiceOptions) {
    super('directus_access', options);
  }

  override async createOne(data: Partial<Item>, opts: MutationOptions = {}) {
    const result = await super.createOne(data, opts);
    await this.clearCaches();
    return result;
  }
}
```
*Why relevant: Shows the canonical service pattern — extend ItemsService, pass collection name to super(), override methods with cache clearing.*

**Snippet 3: AbstractServiceOptions Type (packages/types/src/services.ts)**
```typescript
// Lines 36-41: Service options type
export type AbstractServiceOptions = {
  knex?: Knex | undefined;
  accountability?: Accountability | null | undefined;
  schema: SchemaOverview;
  nested?: string[];
};
```
*Why relevant: This type is used by every service constructor. Defines the DI contract for services.*

**Snippet 4: Event Emitter Pattern (api/src/emitter.ts)**
```typescript
// Lines from emitter.ts: Filter and Action emission
public async emitFilter(event: string | string[], payload: unknown, meta: Record<string, any>, context: EventContext | null = null) {
  // Filters can modify payload before proceeding
  for (const { event, listeners } of eventListeners) {
    for (const listener of listeners) {
      const result = await listener(updatedPayload, { event, ...meta }, context ?? this.getDefaultContext());
      if (result !== undefined) updatedPayload = result;
    }
  }
  return updatedPayload;
}
```
*Why relevant: Shows the filter pattern — listeners can modify the payload. This is how extensions and flows hook into CRUD operations.*

**Snippet 5: App Hydration Pattern (app/src/hydrate.ts)**
```typescript
// Lines from hydrate.ts: Store hydration
export async function hydrate() {
  const stores = useStores();
  const appStore = useAppStore();
  const userStore = useUserStore();
  
  if (appStore.hydrated) return;
  if (appStore.hydrating) return appStore.hydrating;
  
  // Load stores in order, permission-aware
  if (currentUser?.app_access) {
    await Promise.all([
      permissionsStore.hydrate(),
      fieldsStore.hydrate({ skipTranslation: true }),
    ]);
  }
  await onHydrateExtensions();
  await setLanguage(userStore.language);
}
```
*Why relevant: Shows the app's hydration lifecycle — stores are loaded in dependency order, extensions are hydrated after core data.*

**Snippet 6: Error Code Enum (packages/errors/src/codes.ts)**
```typescript
// Lines 1-37: All error codes
export enum ErrorCode {
  Forbidden = 'FORBIDDEN',
  InvalidPayload = 'INVALID_PAYLOAD',
  RecordNotUnique = 'RECORD_NOT_UNIQUE',
  RouteNotFound = 'ROUTE_NOT_FOUND',
  Internal = 'INTERNAL_SERVER_ERROR',
  // ... 30+ error codes
}
```
*Why relevant: Every service and controller uses these error codes. They're the standard way to throw and handle errors across the project.*