Now I have a comprehensive understanding of the Directus architecture. Let me compile the full analysis.

---

## Project Summary

**Directus** is an open-source headless CMS and data platform built with **TypeScript** (2796 files) and **Vue.js** (562 files). It has 4073 total files across a monorepo structure.

**Tech Stack:**
- **Backend:** Node.js, Express.js, Knex.js (SQL query builder), Keyv (caching)
- **Frontend:** Vue 3, Pinia (state management), Vue Router, Vite
- **SDK:** TypeScript SDK with REST, GraphQL, and WebSocket clients
- **Database:** Supports PostgreSQL, MySQL, SQLite, MSSQL, Oracle, CockroachDB
- **Packages:** Monorepo with ~30+ packages under `packages/`

**Scale:** 54 controllers, 139 services, 21 middleware, 139 composables, 58 stores, 5 handlers, 5 validators

---

## Architecture

Directus follows a **Layered Architecture** with a **Monorepo** structure, combining **REST API + GraphQL API** backend with a **Vue.js SPA** frontend. The architecture can be described as:

### Backend (api/) — Layered Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                     Express App (app.ts)                     │
│  Middleware: authenticate, cache, cors, error-handler, etc.  │
├─────────────────────────────────────────────────────────────┤
│                    Controllers (routers)                     │
│  items, auth, collections, fields, users, permissions, etc.  │
├─────────────────────────────────────────────────────────────┤
│                      Services (business logic)               │
│  ItemsService, AuthenticationService, PermissionsService,    │
│  CollectionsService, FieldsService, UsersService, etc.       │
├─────────────────────────────────────────────────────────────┤
│              Database / Storage / Cache Layer                │
│  Knex (database), Keyv (cache), Storage drivers             │
├─────────────────────────────────────────────────────────────┤
│              Infrastructure / Cross-cutting                  │
│  Emitter (events), Flows (automation), WebSocket,            │
│  Extensions, Permissions, Telemetry, Metrics                 │
└─────────────────────────────────────────────────────────────┘
```

### Frontend (app/) — Vue 3 SPA with Pinia Stores
```
┌─────────────────────────────────────────────────────────────┐
│                    Vue App (app.vue)                         │
│  Router, Pinia, i18n, Extensions                            │
├─────────────────────────────────────────────────────────────┤
│                    Modules (plugins)                         │
│  Content, Insights, File Library, Settings, etc.            │
├─────────────────────────────────────────────────────────────┤
│              Composables (reusable logic)                    │
│  use-collection, use-relation-*, use-schema, etc.            │
├─────────────────────────────────────────────────────────────┤
│              Pinia Stores (state management)                 │
│  collections, fields, user, permissions, server, etc.       │
├─────────────────────────────────────────────────────────────┤
│              UI Components (v-*)                             │
│  v-avatar, v-button, v-card, v-table, etc.                  │
└─────────────────────────────────────────────────────────────┘
```

### SDK (sdk/) — Client Library
```
┌─────────────────────────────────────────────────────────────┐
│              DirectusClient (composable pattern)             │
│  createDirectus(url).with(rest()).with(auth())              │
├─────────────────────────────────────────────────────────────┤
│  REST Client  │  GraphQL Client  │  WebSocket Client        │
│  Auth Client  │  Schema Client   │  Realtime Client         │
└─────────────────────────────────────────────────────────────┘
```

### Packages (packages/) — Shared Libraries
- **types** — Core TypeScript types (Accountability, Schema, Query, etc.)
- **errors** — Error codes and error creation utilities
- **utils** — Shared utilities (node, browser, shared)
- **storage** — Storage abstraction with drivers (local, S3, GCS, Azure, etc.)
- **schema** — Schema inspection
- **validation** — Validation utilities
- **extensions** — Extension system types
- **composables** — Shared Vue composables
- **system-data** — System collection definitions
- **themes** — Theming system
- **env** — Environment variable handling
- **memory** — Memory utilities
- **pressure** — Backpressure handling
- **format-title** — Title formatting

---

## Key Files

### Backend (api/)

| File | Purpose | Why Relevant |
|------|---------|-------------|
| `api/src/app.ts` | Express app setup, middleware registration, route mounting | Entry point for the entire API |
| `api/src/server.ts` | HTTP server creation, WebSocket setup, graceful shutdown | Server lifecycle management |
| `api/src/controllers/items.ts` | CRUD routes for any collection | Core generic controller pattern |
| `api/src/services/items.ts` | Generic CRUD service for any collection | Core business logic, event emission, tracking |
| `api/src/services/authentication.ts` | Login, refresh, logout, password reset | Auth flow with providers, TFA, rate limiting |
| `api/src/services/payload.ts` | Field value processing (hash, encrypt, dates, etc.) | Data transformation layer |
| `api/src/services/permissions.ts` | Permission checking, cache clearing | Access control system |
| `api/src/middleware/authenticate.ts` | Token extraction and accountability setup | Auth middleware |
| `api/src/middleware/error-handler.ts` | Error formatting and response | Error handling pattern |
| `api/src/middleware/cache.ts` | Request caching logic | Caching layer |
| `api/src/emitter.ts` | Event emitter (filter/action hooks) | Event system for extensibility |
| `api/src/flows.ts` | Flow automation engine | Automation system |
| `api/src/auth.ts` | Auth provider registration | Pluggable auth system |
| `api/src/cache.ts` | Cache configuration (Redis/memory) | Caching infrastructure |
| `api/src/database/index.ts` | Database connection setup | Database abstraction |
| `api/src/extensions/index.ts` | Extension manager | Extension system |
| `api/src/websocket/authenticate.ts` | WebSocket auth | Real-time auth |
| `api/src/websocket/messages.ts` | WebSocket message schemas (Zod) | Real-time protocol |

### Frontend (app/)

| File | Purpose | Why Relevant |
|------|---------|-------------|
| `app/src/main.ts` | Vue app initialization | App entry point |
| `app/src/app.vue` | Root Vue component | App shell |
| `app/src/router.ts` | Vue Router setup with auth guards | Routing and navigation guards |
| `app/src/hydrate.ts` | App hydration (load stores, extensions) | Initialization flow |
| `app/src/extensions.ts` | Extension loading and registration | Extension system |
| `app/src/api.ts` | Axios instance with request queue | API communication |
| `app/src/modules/index.ts` | Module registration system | Plugin architecture |
| `app/src/stores/collections.ts` | Collections Pinia store | State management |
| `app/src/stores/fields.ts` | Fields Pinia store | State management |
| `app/src/stores/user.ts` | User store with auth state | Auth state management |
| `app/src/stores/permissions.ts` | Permissions store | Access control state |
| `app/src/stores/server.ts` | Server info store | Server configuration state |
| `app/src/composables/use-system.ts` | Provides stores, API, SDK via Vue inject | Dependency injection |
| `app/src/composables/use-schema.ts` | Schema overview computed from stores | Schema access pattern |

### SDK (sdk/)

| File | Purpose | Why Relevant |
|------|---------|-------------|
| `sdk/src/client.ts` | `createDirectus()` — base client factory | SDK entry point |
| `sdk/src/rest/composable.ts` | REST client extension | REST API client |
| `sdk/src/auth/composable.ts` | Auth client extension | Auth client |
| `sdk/src/realtime/composable.ts` | WebSocket client extension | Real-time client |
| `sdk/src/graphql/composable.ts` | GraphQL client extension | GraphQL client |

### Packages

| File | Purpose | Why Relevant |
|------|---------|-------------|
| `packages/types/src/accountability.ts` | `Accountability` type | Core auth context type |
| `packages/types/src/schema.ts` | `SchemaOverview`, `CollectionOverview`, `FieldOverview` | Core schema types |
| `packages/types/src/services.ts` | Service interface definitions | Service contract types |
| `packages/errors/src/codes.ts` | `ErrorCode` enum | Error classification |
| `packages/errors/src/create-error.ts` | `createError()` factory | Error creation pattern |

---

## Key Symbols

### Core Types

| Symbol | File | Description |
|--------|------|-------------|
| `Accountability` | `packages/types/src/accountability.ts` | Auth context: role, user, admin, app, ip, etc. |
| `SchemaOverview` | `packages/types/src/schema.ts` | Full schema: collections + relations |
| `CollectionOverview` | `packages/types/src/schema.ts` | Collection metadata: primary key, fields, singleton |
| `FieldOverview` | `packages/types/src/schema.ts` | Field metadata: type, default, nullable, special |
| `ErrorCode` (enum) | `packages/errors/src/codes.ts` | 30+ error codes (Forbidden, InvalidPayload, etc.) |
| `Query` | `packages/types/src/query.ts` | Query parameters: filter, sort, fields, limit, etc. |
| `Item` | `packages/types/src/items.ts` | Generic item type |
| `PrimaryKey` | `packages/types/src/items.ts` | Primary key type |
| `MutationOptions` | `packages/types/src/items.ts` | Options for create/update/delete operations |

### Backend Services

| Symbol | File | Description |
|--------|------|-------------|
| `ItemsService` | `api/src/services/items.ts` | Generic CRUD for any collection. Handles events, tracking, nested relations |
| `AuthenticationService` | `api/src/services/authentication.ts` | Login, refresh, logout, password reset with provider support |
| `PermissionsService` | `api/src/services/permissions.ts` | Permission CRUD + `getItemPermissions()` for access checks |
| `PayloadService` | `api/src/services/payload.ts` | Field value processing: hash, encrypt, dates, UUID, etc. |
| `ActivityService` | `api/src/services/activity.ts` | Activity logging |
| `RevisionsService` | `api/src/services/revisions.ts` | Revision tracking |
| `CollectionsService` | `api/src/services/collections.ts` | Collection CRUD |
| `FieldsService` | `api/src/services/fields.ts` | Field CRUD |
| `UsersService` | `api/src/services/users.ts` | User management |
| `MetaService` | `api/src/services/meta.ts` | Query metadata (total/filter counts) |
| `GraphQLService` | `api/src/services/graphql.ts` | GraphQL execution |
| `SchemaService` | `api/src/services/schema.ts` | Schema snapshot/diff/apply |
| `TFAService` | `api/src/services/tfa.ts` | Two-factor authentication |
| `SettingsService` | `api/src/services/settings.ts` | App settings |
| `FilesService` | `api/src/services/files.ts` | File upload/management |
| `AssetsService` | `api/src/services/assets.ts` | Asset transformation/serving |
| `FlowsService` | `api/src/services/flows.ts` | Flow CRUD |
| `NotificationsService` | `api/src/services/notifications.ts` | Notification management |
| `SharesService` | `api/src/services/shares.ts` | Share link management |
| `VersionsService` | `api/src/services/versions.ts` | Content versioning |
| `ImportExportService` | `api/src/services/import-export.ts` | CSV/JSON import/export |
| `SpecificationsService` | `api/src/services/specifications.ts` | OpenAPI spec generation |
| `DeploymentService` | `api/src/services/deployment.ts` | Deployment management |
| `DeploymentProjectsService` | `api/src/services/deployment-projects.ts` | Deployment project management |
| `DeploymentRunsService` | `api/src/services/deployment-runs.ts` | Deployment run management |

### Backend Infrastructure

| Symbol | File | Description |
|--------|------|-------------|
| `createApp()` | `api/src/app.ts` | Express app factory |
| `createServer()` | `api/src/server.ts` | HTTP server factory |
| `startServer()` | `api/src/server.ts` | Server startup |
| `getDatabase()` | `api/src/database/index.ts` | Knex database singleton |
| `getCache()` | `api/src/cache.ts` | Cache singleton (Keyv) |
| `getExtensionManager()` | `api/src/extensions/index.ts` | Extension manager singleton |
| `getFlowManager()` | `api/src/flows.ts` | Flow manager singleton |
| `getAuthProvider()` | `api/src/auth.ts` | Auth provider registry |
| `registerAuthProviders()` | `api/src/auth.ts` | Auth provider registration |
| `Emitter` (class) | `api/src/emitter.ts` | Event emitter with filter/action/init hooks |
| `FlowManager` (class) | `api/src/flows.ts` | Flow execution engine |
| `ExtensionManager` (class) | `api/src/extensions/manager.ts` | Extension loading/management |

### Frontend Stores (Pinia)

| Symbol | File | Description |
|--------|------|-------------|
| `useCollectionsStore` | `app/src/stores/collections.ts` | Collections state + CRUD |
| `useFieldsStore` | `app/src/stores/fields.ts` | Fields state + CRUD |
| `useUserStore` | `app/src/stores/user.ts` | Current user state |
| `usePermissionsStore` | `app/src/stores/permissions.ts` | User permissions state |
| `useServerStore` | `app/src/stores/server.ts` | Server info state |
| `useRelationsStore` | `app/src/stores/relations.ts` | Relations state |
| `useNotificationsStore` | `app/src/stores/notifications.ts` | Notifications/snackbar state |
| `useSettingsStore` | `app/src/stores/settings.ts` | App settings state |
| `usePresetsStore` | `app/src/stores/presets.ts` | User presets state |
| `useRequestsStore` | `app/src/stores/requests.ts` | Request tracking state |
| `useAppStore` | `packages/stores/src/app.ts` | App-level state (hydrated, authenticated, etc.) |

### SDK

| Symbol | File | Description |
|--------|------|-------------|
| `createDirectus()` | `sdk/src/client.ts` | Base client factory |
| `DirectusClient` | `sdk/src/types/client.ts` | Client interface with `.with()` composable pattern |
| `rest()` | `sdk/src/rest/composable.ts` | REST client extension |
| `auth()` | `sdk/src/auth/composable.ts` | Auth client extension |
| `realtime()` | `sdk/src/realtime/composable.ts` | WebSocket client extension |
| `graphql()` | `sdk/src/graphql/composable.ts` | GraphQL client extension |

---

## Dependencies

### Module-Level Dependencies

**Backend (api/):**
```
Controllers → Services → Database/Cache/Storage
Services → Emitter (events), Permissions, Cache
Middleware → Authentication, Cache, Error Handler
WebSocket → Authentication, Services
Flows → Services, Emitter
Extensions → Services, Database
```

**Frontend (app/):**
```
App.vue → Router, Stores, Composables, Components
Router → Stores (server, user, app)
Stores → API (axios), SDK
Composables → Stores, API
Modules → Router, Stores, Extensions
Extensions → Components, Interfaces, Displays, Layouts, Panels, Operations
```

**SDK (sdk/):**
```
DirectusClient ← rest(), auth(), realtime(), graphql() (composable extensions)
```

### Key Dependency Chains

1. **Request Flow:** `Express Router → Middleware (authenticate, cache) → Controller → Service → Database`
2. **Auth Flow:** `AuthController → AuthenticationService → AuthProvider (local/OAuth/LDAP/SAML) → Database`
3. **Event Flow:** `Service.createOne() → Emitter.emitFilter() → Emitter.emitAction() → FlowManager`
4. **Extension Flow:** `ExtensionManager.load() → registerExtensions() → hydrate()`
5. **Frontend Init:** `main.ts → loadExtensions() → registerExtensions() → router → hydrate()`

---

## Conventions

### Naming Conventions

Based on the sample_signatures and file analysis:

1. **PascalCase for classes/interfaces/types:**
   - `ItemsService`, `AuthenticationService`, `PermissionsService`, `PayloadService`
   - `SchemaOverview`, `CollectionOverview`, `FieldOverview`
   - `Accountability`, `ErrorCode`, `MutationOptions`

2. **camelCase for functions, methods, variables:**
   - `createApp()`, `getDatabase()`, `getCache()`, `registerAuthProviders()`
   - `createOne()`, `readByQuery()`, `updateMany()`, `deleteMany()`
   - `useEnv()`, `useLogger()`, `useBus()`

3. **Suffix conventions:**
   - `*Service` — Business logic services (ItemsService, AuthenticationService, etc.)
   - `*Controller` — Express route handlers (items.ts, auth.ts, etc. — files, not classes)
   - `*Middleware` — Express middleware (authenticate, cache, error-handler)
   - `*Store` — Pinia stores (collectionsStore, fieldsStore, userStore)
   - `use*` — Vue composables (use-collection, use-schema, use-system)
   - `v-*` — Vue components (v-avatar, v-button, v-table)
   - `*Handler` — Event/operation handlers (error-handler, async-handler)

4. **Prefix conventions:**
   - `I` prefix is NOT used for interfaces (TypeScript interfaces use PascalCase without prefix)
   - `$CURRENT_USER`, `$CURRENT_ROLE` — Dynamic variable prefixes in permission presets

### Architectural Patterns

1. **Service Layer Pattern:** All business logic is in Services. Controllers are thin — they parse requests, call services, and return responses.

2. **Repository-like Pattern via ItemsService:** `ItemsService` acts as a generic repository for any collection, with `createOne`, `readByQuery`, `updateOne`, `deleteMany` methods.

3. **Event-Driven Architecture (Emitter):**
   - `emitFilter(event, payload, meta, context)` — Before operations, can modify payload
   - `emitAction(event, meta, context)` — After operations, fire-and-forget
   - `emitInit(event, meta)` — During app initialization
   - Events: `items.create`, `items.update`, `items.delete`, `auth.login`, `server.start`, etc.

4. **Composable Client Pattern (SDK):**
   - `createDirectus(url).with(rest()).with(auth()).with(realtime())`
   - Each extension returns a mixin object that extends the client

5. **Dependency Injection via `use*` functions:**
   - Backend: `useEnv()`, `useLogger()`, `useDatabase()`, `useCache()` — singleton accessors
   - Frontend: `useSystem(app)` provides stores, API, SDK via Vue's `provide/inject`

6. **Pinia Stores for State Management:** All app state is in Pinia stores with `hydrate()`/`dehydrate()` lifecycle

7. **Plugin Architecture (Extensions):**
   - Interfaces, Displays, Layouts, Modules, Panels, Operations, Themes
   - Each registered via `register*()` functions
   - Loaded dynamically at runtime

8. **Auth Provider Pattern:** Pluggable auth drivers (Local, OAuth2, OpenID, LDAP, SAML)

### Style Conventions

1. **Async/Await everywhere:** All service methods are async. Controllers use `asyncHandler` wrapper.

2. **Error Handling:** Custom error classes created via `createError()` factory. Errors have `code`, `status`, `extensions`. Centralized error handler middleware.

3. **Validation:** Zod schemas for WebSocket messages. Custom validation in services. `validateEnv()` for environment variables.

4. **Transaction Usage:** Database operations use `transaction(this.knex, async (trx) => ...)` pattern.

5. **TypeScript:** Strict types. Interfaces defined in `packages/types`. Services typed via `packages/types/src/services.ts`.

6. **Testing:** Vitest with `.test.ts` files alongside source files.

---

## Similar Implementations

### 1. Similar to `ItemsService` — Generic CRUD pattern

All services that extend the generic CRUD pattern:

| Service | File | Why Similar |
|---------|------|-------------|
| `PermissionsService` | `api/src/services/permissions.ts` | Extends ItemsService pattern with cache clearing |
| `CollectionsService` | `api/src/services/collections.ts` | CRUD for collections with schema operations |
| `FieldsService` | `api/src/services/fields.ts` | CRUD for fields with type handling |
| `UsersService` | `api/src/services/users.ts` | CRUD for users with invite/register |
| `RolesService` | `api/src/services/roles.ts` | CRUD for roles |
| `PoliciesService` | `api/src/services/policies.ts` | CRUD for policies |
| `SettingsService` | `api/src/services/settings.ts` | Singleton CRUD for settings |
| `FlowsService` | `api/src/services/flows.ts` | CRUD for flows |
| `NotificationsService` | `api/src/services/notifications.ts` | CRUD for notifications |
| `VersionsService` | `api/src/services/versions.ts` | CRUD for content versions |

### 2. Similar to `AuthenticationService` — Auth provider pattern

| Service | File | Why Similar |
|---------|------|-------------|
| `LocalAuthDriver` | `api/src/auth/drivers/local.ts` | Local auth implementation |
| `OAuth2AuthDriver` | `api/src/auth/drivers/oauth2.ts` | OAuth2 auth implementation |
| `OpenIDAuthDriver` | `api/src/auth/drivers/openid.ts` | OpenID auth implementation |
| `LDAPAuthDriver` | `api/src/auth/drivers/ldap.ts` | LDAP auth implementation |
| `SAMLAuthDriver` | `api/src/auth/drivers/saml.ts` | SAML auth implementation |

### 3. Similar to Pinia Stores — State management pattern

| Store | File | Why Similar |
|-------|------|-------------|
| `useCollectionsStore` | `app/src/stores/collections.ts` | Hydrate/dehydrate pattern |
| `useFieldsStore` | `app/src/stores/fields.ts` | Hydrate/dehydrate pattern |
| `useUserStore` | `app/src/stores/user.ts` | Auth state management |
| `usePermissionsStore` | `app/src/stores/permissions.ts` | Permission state |
| `useRelationsStore` | `app/src/stores/relations.ts` | Relation state |
| `useServerStore` | `app/src/stores/server.ts` | Server info state |

---

## Context for the Task

### Architecture Overview

Directus is a **headless CMS** with a **monorepo** structure containing:
- **`api/`** — Express.js REST+GraphQL API backend
- **`app/`** — Vue 3 SPA admin panel
- **`sdk/`** — TypeScript SDK for client applications
- **`packages/`** — ~30 shared packages (types, errors, utils, storage, etc.)

### Key Architectural Patterns

**1. Service Layer Pattern:** Controllers are thin wrappers. All business logic lives in Services. The `ItemsService` is the generic CRUD service used for any collection:

```typescript
// api/src/controllers/items.ts — Thin controller
new ItemsService(req.collection, {
    accountability: req.accountability,
    schema: req.schema,
});
const result = await service.readByQuery(req.sanitizedQuery);
```

**2. Event-Driven Architecture:** The `Emitter` class provides filter (before, can modify) and action (after, fire-and-forget) hooks:

```typescript
// api/src/emitter.ts — Event system
await emitFilter('items.create', payload, { collection }, context);
await emitAction('items.create', { key, payload }, context);
```

**3. Composable SDK Pattern:** The SDK uses a composable/mixin pattern:

```typescript
// sdk/src/client.ts — Base client
const client = createDirectus('https://example.com')
    .with(rest())
    .with(auth('json'));
```

**4. Pinia Stores with Hydrate/Dehydrate:** Frontend state management follows a consistent lifecycle:

```typescript
// app/src/stores/collections.ts — Pinia store pattern
defineStore('collectionsStore', () => {
    const collections = ref<Collection[]>([]);
    async function hydrate() { /* fetch from API */ }
    async function dehydrate() { /* reset state */ }
    return { collections, hydrate, dehydrate, ... };
});
```

**5. Auth Context (Accountability):** Every request gets an `Accountability` object passed through middleware:

```typescript
// packages/types/src/accountability.ts
type Accountability = {
    role: string | null;
    roles: string[];
    user: string | null;
    admin: boolean;
    app: boolean;
    ip: string | null;
};
```

**6. Error Handling:** Centralized error handler with typed error codes:

```typescript
// packages/errors/src/codes.ts
enum ErrorCode {
    Forbidden = 'FORBIDDEN',
    InvalidPayload = 'INVALID_PAYLOAD',
    RecordNotUnique = 'RECORD_NOT_UNIQUE',
    // ... 30+ codes
}
```

### Main Systems

| System | Location | Description |
|--------|----------|-------------|
| **REST API** | `api/src/controllers/` + `api/src/services/` | CRUD endpoints for all collections |
| **GraphQL API** | `api/src/controllers/graphql.ts` | GraphQL endpoint (items + system) |
| **Auth System** | `api/src/auth.ts` + `api/src/services/authentication.ts` | Pluggable auth providers |
| **Permissions** | `api/src/services/permissions.ts` + `api/src/permissions/` | Role-based access control |
| **Flows/Automation** | `api/src/flows.ts` | Event-driven automation engine |
| **WebSocket/Realtime** | `api/src/websocket/` | Real-time subscriptions |
| **Extensions** | `api/src/extensions/` + `app/src/extensions.ts` | Plugin system |
| **Caching** | `api/src/cache.ts` | Redis/memory caching |
| **Storage** | `api/src/storage/` + `packages/storage-driver-*` | File storage abstraction |
| **Admin App** | `app/src/` | Vue 3 SPA admin panel |
| **SDK** | `sdk/src/` | TypeScript client library |