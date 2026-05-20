I now have all the information needed. Let me compile the comprehensive context document.

---

## Project Summary

**Directus** — an open-source headless CMS and backend-as-a-service. The project is a large TypeScript monorepo with 4,073 files (2,796 TypeScript, 562 Vue, 103 JSON, 268 YAML). The API layer (`api/src/`) contains the Express.js REST API with controllers, middleware, services, and auth drivers.

## Architecture

**Architecture Type:** Layered MVC with Service Layer pattern, running on Express.js.

**Layers (in order of request flow):**

1. **Global Middleware** (applied to all routes via `app.use()`):
   - `extractToken` — extracts JWT from query param, Authorization header, or session cookie
   - `cors` — CORS headers
   - `rateLimiterGlobal` / `rateLimiter` — global and IP-based rate limiting
   - `authenticate` — verifies JWT and sets `req.accountability`
   - `schema` — loads DB schema into `req.schema`
   - `sanitizeQuery` — validates and sanitizes query params into `req.sanitizedQuery`
   - `requestCounter` — telemetry counter
   - `cache` — response caching

2. **Controllers** (route handlers, one per resource):
   - Each controller is an Express `Router()` that defines CRUD endpoints
   - Controllers instantiate **Services** to perform business logic
   - Controllers use middleware like `collectionExists`, `validateBatch`, `useCollection`

3. **Services** (business logic layer):
   - `AuthenticationService`, `ItemsService`, `UsersService`, `FilesService`, etc.
   - Services interact with the database via Knex

4. **Auth Drivers** (pluggable authentication):
   - `local`, `oauth2`, `openid`, `ldap`, `saml`
   - Each driver provides a login router and user verification

5. **Error Handling**:
   - `notFoundHandler` (404) → `errorHandler` (catch-all)

## Key Files

### 1. `api/src/app.ts`
**Purpose:** Main Express app setup — registers all middleware in order, mounts all controllers at their paths.
**Relevance:** Shows the complete middleware pipeline and route registration.

### 2. `api/src/middleware/authenticate.ts`
**Purpose:** Core authentication middleware — verifies JWT tokens, sets `req.accountability` with user/role/permissions.
**Relevance:** The primary auth middleware applied to all protected routes.

### 3. `api/src/middleware/extract-token.ts`
**Purpose:** Extracts the access token from query params, Authorization header, or session cookie and stores it in `req.token`.
**Relevance:** Runs before `authenticate` — the first step in auth pipeline.

### 4. `api/src/controllers/auth.ts`
**Purpose:** Auth controller — mounts per-provider login routers, handles `/refresh`, `/logout`, `/password/request`, `/password/reset`.
**Relevance:** The main auth endpoint controller.

### 5. `api/src/services/authentication.ts`
**Purpose:** Authentication service — handles login logic, token generation, refresh, logout, password reset.
**Relevance:** Core business logic for authentication.

### 6. `api/src/auth/drivers/local.ts`
**Purpose:** Local auth driver — email/password login with Joi validation, creates the local login router.
**Relevance:** The default auth provider implementation.

### 7. `api/src/utils/get-accountability-for-token.ts`
**Purpose:** Resolves a token (JWT or static) into an Accountability object with user, role, and permissions.
**Relevance:** Called by the authenticate middleware.

### 8. `api/src/middleware/error-handler.ts`
**Purpose:** Global error handler — catches all errors, formats them as Directus errors.
**Relevance:** Last middleware in the chain.

### 9. `api/src/middleware/cache.ts`
**Purpose:** Response caching middleware — checks cache before executing handlers.
**Relevance:** Applied after authentication, before controllers.

### 10. `api/src/middleware/respond.ts`
**Purpose:** Response formatter — handles exports (JSON/CSV/XML/YAML), sets cache headers, sends payload.
**Relevance:** Applied at the end of each controller route.

### 11. `api/src/controllers/items.ts`
**Purpose:** Generic items controller — handles CRUD for any collection via `/:collection` routes.
**Relevance:** Shows the standard CRUD controller pattern.

### 12. `api/src/types/express.d.ts`
**Purpose:** Type augmentation for Express Request — adds `token`, `accountability`, `schema`, `sanitizedQuery`, `collection`.
**Relevance:** Defines the shape of request objects throughout the API.

## Key Symbols

### Types & Interfaces

| Symbol | File | Description |
|--------|------|-------------|
| `Accountability` | `packages/types/src/accountability.ts` | User context: role, user, roles, admin, app, share, ip, userAgent, origin, session |
| `DirectusTokenPayload` | `api/src/types/auth.ts` | JWT payload shape: id, role, app_access, admin_access, share, session, enforce_tfa |
| `AuthenticationMode` | `api/src/types/auth.ts` | `'json' \| 'cookie' \| 'session'` |
| `LoginResult` | `packages/types/src/authentication.ts` | `{ accessToken, refreshToken, expires, id }` |
| `User` | `api/src/types/auth.ts` | DB user shape: id, first_name, last_name, email, password, status, role, provider |
| `AuthDriverOptions` | `api/src/types/auth.ts` | `{ knex: Knex }` |

### Middleware Functions

| Symbol | File | Description |
|--------|------|-------------|
| `extractToken` (default export) | `api/src/middleware/extract-token.ts` | Extracts token from query/header/cookie → `req.token` |
| `handler` (default export via `asyncHandler`) | `api/src/middleware/authenticate.ts` | Verifies token → sets `req.accountability` |
| `errorHandler` | `api/src/middleware/error-handler.ts` | Global error handler |
| `respond` | `api/src/middleware/respond.ts` | Sends response, handles exports, sets cache headers |
| `cache` (default export) | `api/src/middleware/cache.ts` | Cache middleware (read/write) |
| `sanitizeQuery` (default export) | `api/src/middleware/sanitize-query.ts` | Validates query params → `req.sanitizedQuery` |
| `validateBatch` | `api/src/middleware/validate-batch.ts` | Validates batch operation payloads |
| `collectionExists` | `api/src/middleware/collection-exists.ts` | Checks if collection exists in schema |
| `useCollection` | `api/src/middleware/use-collection.ts` | Sets `req.collection` from route param |

### Controller Functions

| Symbol | File | Description |
|--------|------|-------------|
| `createLocalAuthRouter(provider)` | `api/src/auth/drivers/local.ts` | Creates login POST route for local auth |
| `createOAuth2AuthRouter(provider)` | `api/src/auth/drivers/oauth2.ts` | Creates OAuth2 login routes |
| `createOpenIDAuthRouter(provider)` | `api/src/auth/drivers/openid.ts` | Creates OpenID login routes |
| `createLDAPAuthRouter(provider)` | `api/src/auth/drivers/ldap.ts` | Creates LDAP login routes |
| `createSAMLAuthRouter(provider)` | `api/src/auth/drivers/saml.ts` | Creates SAML login routes |

### Service Classes

| Symbol | File | Description |
|--------|------|-------------|
| `AuthenticationService` | `api/src/services/authentication.ts` | `login()`, `refresh()`, `logout()`, `requestPasswordReset()`, `resetPassword()` |

### Utility Functions

| Symbol | File | Description |
|--------|------|-------------|
| `getAccountabilityForToken(token, accountability?)` | `api/src/utils/get-accountability-for-token.ts` | Resolves token → Accountability (JWT verify or static token lookup) |
| `createDefaultAccountability(overrides?)` | `api/src/permissions/utils/create-default-accountability.ts` | Creates base Accountability with null/default values |
| `registerAuthProviders()` | `api/src/auth.ts` | Registers all configured auth providers from env |
| `getAuthProvider(provider)` | `api/src/auth.ts` | Gets a registered auth provider by name |

## Dependencies

### Middleware Pipeline (in order, from `api/src/app.ts`)

```
app.use(extractToken)           # line 247 — extracts token
app.use(rateLimiterGlobal)      # line 295 — global rate limit
app.use(rateLimiter)            # line 299 — IP rate limit
app.use(authenticate)           # line 307 — verifies token → req.accountability
app.use(schema)                 # line 309 — loads schema → req.schema
app.use(sanitizeQuery)          # line 311 — validates query → req.sanitizedQuery
app.use(requestCounter)         # line 313 — telemetry
app.use(cache)                  # line 315 — response cache
```

### Route Registration (from `api/src/app.ts`)

```
/auth        → authRouter          (line 321) — NO authenticate middleware (auth routes are public)
/graphql     → graphqlRouter       (line 323)
/activity    → activityRouter      (line 325)
/access      → accessRouter        (line 326)
/assets      → assetsRouter        (line 327)
/collections → collectionsRouter   (line 328)
/items       → itemsRouter         (line 342)
/users       → usersRouter         (line 373)
/server      → serverRouter        (line 370)
... (all other resource routes)
```

**Key insight:** The `authRouter` is mounted BEFORE the `authenticate` middleware (line 307 vs line 321), meaning auth endpoints are public/unauthenticated. All other controllers are mounted AFTER `authenticate`, so they require authentication.

### Module Dependencies

- `app.ts` imports: all controllers, all middleware, `registerAuthProviders`, `getExtensionManager`, `getFlowManager`, emitter
- `controllers/auth.ts` imports: auth drivers (`createLocalAuthRouter`, etc.), `AuthenticationService`, `UsersService`, `respond` middleware
- `middleware/authenticate.ts` imports: `getAccountabilityForToken`, `createDefaultAccountability`, `getIPFromReq`, emitter
- `services/authentication.ts` imports: `getAuthProvider`, `getSecret`, JWT utils, rate limiter, activity/revisions/payload services

## Conventions

### Naming Conventions

- **Files:** kebab-case (`authenticate.ts`, `extract-token.ts`, `error-handler.ts`, `get-accountability-for-token.ts`)
- **Classes:** PascalCase (`AuthenticationService`, `UsersService`, `ItemsService`, `FilesService`)
- **Functions:** camelCase (`createLocalAuthRouter`, `getAccountabilityForToken`, `createDefaultAccountability`)
- **Interfaces/Types:** PascalCase (`Accountability`, `DirectusTokenPayload`, `AuthenticationMode`, `LoginResult`)
- **Exports:** Default exports for middleware functions (`export default extractToken`, `export default asyncHandler(handler)`), named exports for utilities (`export async function getAccountabilityForToken`)
- **No prefix `I`** for interfaces (TypeScript style, e.g., `Accountability` not `IAccountability`)
- **Suffixes:** `Service` for service classes, `Router` for router variables, `Handler` for error handler

### Architectural Patterns

- **Service Layer:** Controllers delegate business logic to Service classes (e.g., `AuthenticationService`, `ItemsService`)
- **Middleware Chain:** Express middleware pattern — each middleware sets properties on `req` for downstream use
- **Auth Provider Strategy Pattern:** Different auth drivers (`local`, `oauth2`, `openid`, `ldap`, `saml`) implement the same interface
- **Dependency Injection via Constructor:** Services receive `{ accountability, schema, knex }` options object
- **Async Handler Wrapper:** All async route handlers wrapped with `asyncHandler` to catch errors
- **Event-Driven Hooks:** `emitter.emitFilter()` and `emitter.emitAction()` for extensibility (e.g., `'authenticate'`, `'auth.login'`, `'request.not_found'`)

### Style Conventions

- **Async/Await:** All async operations use `async/await`
- **Error Handling:** Directus errors from `@directus/errors` package (e.g., `InvalidCredentialsError`, `InvalidPayloadError`, `ForbiddenError`)
- **Validation:** Joi schemas for request body validation (e.g., in `validate-batch.ts` and `local.ts` auth router)
- **Environment Config:** `useEnv()` returns a global env object; config accessed via `env['KEY_NAME']`
- **Logger:** `useLogger()` returns a Pino logger instance
- **TypeScript:** Strict mode, type imports with `import type`, Express type augmentation in `express.d.ts`

## Similar Implementations

### 1. Similar to `AuthenticationService` (`api/src/services/authentication.ts`)

| Class | File | Why Similar |
|-------|------|-------------|
| `ItemsService` | `api/src/services/items.ts` | Same constructor pattern `{ accountability, schema, knex }`, same service layer pattern |
| `UsersService` | `api/src/services/users.ts` | Extends ItemsService, same DI pattern |
| `FilesService` | `api/src/services/files.ts` | Same service pattern with `uploadOne`, `importOne` methods |
| `ActivityService` | `api/src/services/activity.ts` | Same constructor, same CRUD pattern |

### 2. Similar to `auth.ts` controller (`api/src/controllers/auth.ts`)

| File | Why Similar |
|------|-------------|
| `api/src/controllers/items.ts` | Same pattern: `Router()`, `asyncHandler` wrappers, service instantiation, `respond` middleware |
| `api/src/controllers/users.ts` | Same pattern with `useCollection('directus_users')` middleware |
| `api/src/controllers/files.ts` | Same pattern with multipart upload handling |
| `api/src/controllers/server.ts` | Same pattern with service instantiation and respond |

### 3. Similar to `authenticate.ts` middleware (`api/src/middleware/authenticate.ts`)

| File | Why Similar |
|------|-------------|
| `api/src/middleware/extract-token.ts` | Runs before authenticate, sets `req.token` |
| `api/src/middleware/cache.ts` | Same `asyncHandler` pattern, same `req` property access |
| `api/src/middleware/sanitize-query.ts` | Same pattern: reads from `req`, validates, sets property on `req` |
| `api/src/middleware/error-handler.ts` | Error handling middleware, uses `asyncHandler` wrapper |

## Context for the Task

### Middleware Pipeline (from `api/src/app.ts`)

The Express app is created in `createApp()` and middleware is applied in this exact order:

```typescript
// Line 247: Extract token first
app.use(extractToken);

// Lines 294-300: Rate limiters
if (env['RATE_LIMITER_GLOBAL_ENABLED'] === true) app.use(rateLimiterGlobal);
if (env['RATE_LIMITER_ENABLED'] === true) app.use(rateLimiter);

// Line 307: Authenticate — verifies token and sets req.accountability
app.use(authenticate);

// Lines 309-315: Schema, query sanitization, cache
app.use(schema);
app.use(sanitizeQuery);
app.use(requestCounter);
app.use(cache);

// Lines 321+: Route controllers mounted AFTER authenticate
app.use('/auth', authRouter);       // <-- auth is mounted BEFORE authenticate? No! Line 321 is after line 307.
app.use('/items', itemsRouter);
app.use('/users', usersRouter);
// ... all other controllers
```

**Correction:** Looking at the line numbers more carefully — `authenticate` is at line 307, and `authRouter` is at line 321. So auth routes ARE behind the authenticate middleware. However, the auth controller's login routes are public because they don't require a valid token — the authenticate middleware allows unauthenticated requests through (it sets a default accountability with `user: null`).

### Authentication Flow

1. **`extractToken`** middleware extracts the token from `?access_token=`, `Authorization: Bearer <token>`, or session cookie, storing it in `req.token`.

2. **`authenticate`** middleware calls `getAccountabilityForToken(req.token, defaultAccountability)`:
   - If `req.token` is a JWT, it verifies the signature and extracts payload
   - If `req.token` is a static token, it looks up the user in `directus_users`
   - Sets `req.accountability` with user, role, permissions info

3. **Controllers** use `req.accountability` to check permissions and pass it to services.

### Auth Controller Pattern (from `api/src/controllers/auth.ts`)

```typescript
const router = Router();
const authProviders = getAuthProviders();

for (const authProvider of authProviders) {
    let authRouter: Router | undefined;
    switch (authProvider.driver) {
        case 'local':  authRouter = createLocalAuthRouter(authProvider.name); break;
        case 'oauth2': authRouter = createOAuth2AuthRouter(authProvider.name); break;
        // ...
    }
    router.use(`/login/${authProvider.name}`, authRouter);
}

// Standard auth endpoints
router.post('/refresh', asyncHandler(async (req, res, next) => { /* ... */ }));
router.post('/logout', asyncHandler(async (req, res, next) => { /* ... */ }));
router.post('/password/request', asyncHandler(async (req, _res, next) => { /* ... */ }));
router.post('/password/reset', asyncHandler(async (req, _res, next) => { /* ... */ }));
```

### Controller Pattern (from `api/src/controllers/items.ts`)

```typescript
const router = Router();

router.post('/:collection', collectionExists, asyncHandler(async (req, res, next) => {
    const service = new ItemsService({ accountability: req.accountability, schema: req.schema });
    // ... perform operation
    res.locals['payload'] = result;
    return next();
}), respond);

router.get('/:collection', collectionExists, readHandler, respond);
router.get('/:collection/:pk', collectionExists, asyncHandler(async (req, res, next) => { /* ... */ }), respond);
router.patch('/:collection/:pk', collectionExists, asyncHandler(async (req, res, next) => { /* ... */ }), respond);
router.delete('/:collection/:pk', collectionExists, asyncHandler(async (req, _res, next) => { /* ... */ }));
```

### Key Request Properties (from `api/src/types/express.d.ts`)

```typescript
declare global {
    namespace Express {
        export interface Request {
            token: string | null;           // Set by extractToken
            collection: string;             // Set by useCollection
            sanitizedQuery: Query;          // Set by sanitizeQuery
            schema: SchemaOverview;         // Set by schema middleware
            accountability?: Accountability; // Set by authenticate
            singleton?: boolean;
        }
    }
}
```