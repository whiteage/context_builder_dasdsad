Now I have enough information to produce the architecture analysis. Let me compile it.

## 1. PROJECT SUMMARY

**Directus** is an open-source headless CMS and data platform (~4068 files, 2792 TypeScript, 562 Vue). It's a monorepo managed with pnpm workspaces. The project has 4 main top-level directories: `api/` (backend Express server), `app/` (Vue 3 admin SPA), `sdk/` (TypeScript client SDK), and `packages/` (28 shared packages for types, errors, storage drivers, composables, etc.).

## 2. ARCHITECTURE

**Type: Layered Monolith with Modular Packages (API) + Vue SPA (App) + SDK**

```
API (Express)                          APP (Vue 3 SPA)
┌─────────────────────┐               ┌──────────────────────┐
│ Controllers (39)    │  HTTP/WS      │ Modules (content,    │
│   - REST routes     │◄─────────────►│   settings, etc.)    │
│   - GraphQL         │               │   - Interfaces       │
│   - WebSocket       │               │   - Displays         │
│   - MCP             │               │   - Layouts          │
├─────────────────────┤               │   - Panels           │
│ Middleware (21)     │               │   - Operations       │
│   - auth/cors/cache │               ├──────────────────────┤
│   - error-handler   │               │ Composables (59)     │
│   - rate-limit      │               │   - use-items        │
├─────────────────────┤               │   - use-relation-*   │
│ Services (40+)      │               │   - use-collection   │
│   - ItemsService    │               ├──────────────────────┤
│   - UsersService    │               │ Stores (Pinia, 23)   │
│   - GraphQLService  │               │   - collections      │
│   - PayloadService  │               │   - fields           │
├─────────────────────┤               │   - user/server      │
│ Permissions System  │               ├──────────────────────┤
│   - validate-access │               │ Components (130+)    │
│   - filter/action   │               │   - v-* components   │
├─────────────────────┤               └──────────────────────┘
│ Database Layer      │
│   - Knex.js ORM     │               SDK (TypeScript Client)
│   - run-ast (AST→SQL)│              ┌──────────────────────┐
│   - Schema helpers  │               │ REST / GraphQL /     │
├─────────────────────┤               │ Realtime / Auth      │
│ Event System        │               └──────────────────────┘
│   - Emitter (filters│
│     + actions)      │     PACKAGES (28 shared libs)
│   - Flows engine    │     ┌──────────────────────────────┐
├─────────────────────┤     │ types, errors, utils, env,   │
│ Auth Drivers        │     │ storage, memory, schema,     │
│   - LDAP, OAuth,    │     │ validation, themes, stores,  │
│     local           │     │ composables, constants, ai   │
└─────────────────────┘     └──────────────────────────────┘
```

**Dependency Flow:**
- **Controllers** → Middleware → **Services** → Database (Knex)
- **Services** → Permissions System → Database
- **Services** → Event Emitter (filters/actions) → Flows Engine
- **App** → SDK → API (REST/GraphQL/WebSocket)
- **App** → Composables → Stores → SDK
- **All layers** → Packages (types, errors, utils)

**Key architectural patterns:**
- **Service Layer pattern**: All business logic lives in services (ItemsService base class, ~40+ specialized services)
- **Event-driven**: Emitter supports `filter` (payload-modifying, awaitable) and `action` (fire-and-forget) hooks
- **AST-based query building**: REST/GraphQL/WS requests are converted to an AST, then `runAst()` translates to SQL
- **Plugin/Extension system**: Extensions register via `defineInterface`, `defineDisplay`, `defineModule`, etc.
- **Auth driver pattern**: Abstract `AuthDriver` base class with LDAP, OAuth, local implementations

## 3. RELATED FILES

| File | Purpose | Relevance |
|------|---------|-----------|
| `api/src/app.ts` | Express app factory | Central wiring: middleware, routes, extensions, flows |
| `api/src/services/items.ts` | Base CRUD service (ItemsService) | Core business logic for all collections |
| `api/src/controllers/items.ts` | REST routes for items | Entry point for HTTP requests |
| `api/src/emitter.ts` | Event emitter (filters + actions) | Core event system powering flows & hooks |
| `api/src/flows.ts` | Flow manager (automation engine) | Event-driven automation built on emitter |
| `api/src/permissions/modules/validate-access/index.ts` | Permission validation | Access control layer |
| `api/src/database/run-ast/index.ts` | AST-to-SQL translator | Core query engine |
| `api/src/middleware/authenticate.ts` | Auth middleware | Request authentication pipeline |
| `api/src/auth/auth.ts` | Abstract AuthDriver | Auth provider abstraction |
| `api/src/services/graphql/index.ts` | GraphQL service | GraphQL execution layer |
| `app/src/main.ts` | Vue app bootstrap | Frontend initialization |
| `app/src/router.ts` | Vue Router config | Frontend routing + auth guards |
| `app/src/stores/` (23 files) | Pinia stores | Frontend state management |
| `app/src/composables/` (59 files) | Vue composables | Reusable frontend logic |
| `sdk/src/client.ts` | SDK client factory | Client-side API abstraction |
| `packages/types/src/index.ts` | Shared type definitions | Cross-cutting type contracts |

## 4. DEPENDENCY GRAPH

**Module-level:**
```
tests/ → api
api/ → packages/* (types, errors, utils, env, storage, memory, schema, validation)
app/ → packages/* (types, composables, stores, themes, constants)
sdk/ → packages/* (types, errors)
packages/ → packages/* (inter-package deps)
```

**File-level (key chains):**
```
Controllers (items.ts)
  → ItemsService (services/items.ts)
    → PayloadService (services/payload.ts)
    → ActivityService (services/activity.ts)
    → RevisionsService (services/revisions.ts)
    → Database (database/index.ts via Knex)
    → Emitter (emitter.ts) → Flows (flows.ts)
    → Permissions (permissions/)

Middleware (authenticate.ts)
  → getAccountabilityForToken()
  → Database
  → Emitter (emitFilter 'authenticate')

GraphQLService (services/graphql/index.ts)
  → ItemsService (for read/upsert)
  → generateSchema()
  → graphql-js execution
```

**Call Graph (request flow):**
```
HTTP Request
  → Express middleware chain (cors → json → cookieParser → extractToken → authenticate → schema → collection-exists)
  → Controller handler (e.g., items.ts GET /:collection/:pk)
    → ItemsService.readOne()
      → Permissions.validateAccess()
      → runAst() (AST → SQL)
      → Database query (Knex)
      → Emitter.emitFilter('items.read')
      → Return result
    → respond middleware (serializes response)
```

## 5. CONVENTIONS

**Naming (from sample_signatures):**
1. **Services**: `{Entity}Service` — `ItemsService`, `GraphQLService`, `OperationsService`, `PayloadService`
2. **Controllers**: `{entity}.ts` in `api/src/controllers/` — `items.ts`, `users.ts`, `auth.ts`
3. **Auth drivers**: `{Name}AuthDriver` extends `AuthDriver` — `LDAPAuthDriver`
4. **Database helpers**: `{Helper}{Dialect}` — `FnHelperOracle`, `CapabilitiesHelperDefault`
5. **Storage drivers**: `Driver{Name}` — `DriverSupabase` implements `TusDriver`
6. **Interfaces**: PascalCase, no `I` prefix — `DirectusClient`, `Collection`, `Props` (Vue component props)
7. **Config types**: `{Component}Config{Backend}` — `BusConfigRedis`, `KvConfigRedis`, `LimiterConfigRedis`
8. **Vue components**: `v-{name}` — `v-avatar`, `v-badge`, `v-list-item`, `v-textarea`
9. **Composables**: `use-{name}` — `use-items`, `use-collection`, `use-relation-m2o`
10. **Stores**: `{name}Store` via Pinia — `useServerStore`, `useUserStore`, `usePermissionsStore`
11. **Error types**: `{Name}Error` — `InvalidPayloadError`, `ForbiddenError`, `GraphQLValidationError`
12. **Async**: All service methods are `async`, return `Promise<T>`
13. **Constructor pattern**: Services take `AbstractServiceOptions` (knex, schema, accountability)
14. **File naming**: kebab-case for all files — `validate-batch.ts`, `error-handler.ts`, `use-relation-m2o.ts`

**Architectural patterns:**
- **Service pattern**: All business logic in services, controllers are thin
- **Event-driven**: `emitFilter` (modify payload) + `emitAction` (fire-and-forget) via EventEmitter2
- **DI via constructor**: Services receive `knex`, `schema`, `accountability` in options object
- **Error handling**: Custom `DirectusError` hierarchy with error codes (`ErrorCode.RecordNotUnique`, etc.)
- **Permissions**: Centralized `validateAccess()` called from services, not controllers

## 6. SIMILAR IMPLEMENTATIONS

| Class | File | Similarity |
|-------|------|------------|
| `ItemsService` | `api/src/services/items.ts` | Base service — all other services extend or use it |
| `OperationsService` | `api/src/services/operations.ts` | Extends `ItemsService`, same constructor pattern |
| `GraphQLService` | `api/src/services/graphql/index.ts` | Takes `AbstractServiceOptions`, uses `getService()` internally |
| `PayloadService` | `api/src/services/payload.ts` | Takes `collection` + `AbstractServiceOptions`, processes values |
| `LDAPAuthDriver` | `api/src/auth/drivers/ldap.ts` | Extends `AuthDriver`, same constructor `AuthDriverOptions` |
| `DriverSupabase` | `packages/storage-driver-supabase/src/index.ts` | Implements `TusDriver`, storage driver pattern |
| `FnHelperOracle` | `api/src/database/helpers/fn/dialects/oracle.ts` | Extends `FnHelper`, dialect-specific helper pattern |

## 7. TASK CONTEXT

**Directus** is a monorepo with 4 main areas: `api/` (Express backend), `app/` (Vue 3 admin SPA), `sdk/` (TypeScript client), and `packages/` (28 shared libraries).

**API architecture**: Express app with ~39 controllers (thin, route-only), ~21 middleware (auth, cache, CORS, rate-limit, error handling), ~40+ services (business logic), a permissions system, an event emitter (filters + actions), and a flows automation engine. The database layer uses Knex.js with an AST-to-SQL engine (`runAst`). Auth supports pluggable drivers (local, LDAP, OAuth).

**App architecture**: Vue 3 SPA with Pinia stores (23), composables (59), components (130+), and extension points (interfaces, displays, layouts, modules, panels, operations). Uses the SDK to communicate with the API.

**Key patterns to follow**: Services extend or use `ItemsService`, take `AbstractServiceOptions` in constructor, are async. Controllers are thin — they validate, call service, respond. Events use `emitFilter` (modify data) and `emitAction` (side effects). All files use kebab-case. Vue components are `v-{name}`. Composables are `use-{name}`.

## 8. RELEVANT CODE SNIPPETS

**Snippet 1 — Service constructor pattern** (from `api/src/services/items.ts`):
```typescript
// Line ~30: ItemsService constructor
constructor(collection: Collection, options: AbstractServiceOptions) {
    super();
    this.collection = collection;
    this.knex = options.knex || getDatabase();
    this.accountability = options.accountability || null;
    this.schema = options.schema;
    // ...
}
```

**Snippet 2 — Controller thin handler** (from `api/src/controllers/items.ts`):
```typescript
// Lines ~50-70: GET /:collection/:pk
get('/:collection/:pk', collectionExists, asyncHandler(async (req, res, next) => {
    const service = new ItemsService(req.collection, {
        accountability: req.accountability,
        schema: req.schema,
    });
    const result = await service.readOne(req.params['pk']!, req.sanitizedQuery);
    return next(); // respond middleware handles serialization
}));
```

**Snippet 3 — Event emitter with filter/action** (from `api/src/emitter.ts`):
```typescript
// Lines ~20-40: emitFilter and emitAction
public async emitFilter(event: string | string[], payload: unknown, meta: Record<string, any>, context: EventContext | null = null) {
    // calls listeners, passes payload through for modification
    for (const { event, listeners } of eventListeners) {
        for (const listener of listeners) {
            const result = await listener(updatedPayload, { event, ...meta }, context);
            if (result !== undefined) updatedPayload = result;
        }
    }
    return updatedPayload;
}

public emitAction(event: string | string[], meta: Record<string, any>, context: EventContext | null = null) {
    // fire-and-forget, errors are logged not thrown
    return this.emitter.emitAsync(event, { event, ...meta }, context);
}
```

**Snippet 4 — Auth driver abstract class** (from `api/src/auth/auth.ts`):
```typescript
// Lines 1-8: AuthDriver base
export abstract class AuthDriver {
    protected knex: Knex;
    constructor(options: AuthDriverOptions, _config: Record<string, any>) {
        this.knex = options.knex;
    }
    abstract getUserID(payload: Record<string, any>): Promise<string>;
    abstract verify(user: User, password?: string): Promise<void>;
    async login(_user: User, _payload: Record<string, any>): Promise<void> {}
    async refresh(_user: User): Promise<void> {}
    async logout(_user: User): Promise<void> {}
}
```

**Snippet 5 — App bootstrap with extension registration** (from `app/src/main.ts`):
```typescript
// Lines 10-28: App initialization
async function init() {
    const app = createApp(App);
    app.use(i18n);
    app.use(createPinia());
    app.use(createHead());
    registerDirectives(app);
    registerComponents(app);
    registerViews(app);
    await loadExtensions();
    registerExtensions(app);
    app.use(router);
    useSystem(app);
    app.mount('#app');
}
```