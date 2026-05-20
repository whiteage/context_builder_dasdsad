Now I have a complete picture. Let me compile the comprehensive context document.

---

## Project Summary

**Project:** Directus — an open-source headless CMS and backend-as-a-service.
**Tech Stack:** TypeScript (2796 files), Vue.js (562 files), Express.js, WebSocket (ws), JWT (jsonwebtoken), Knex.js (database), Zod (validation).
**Scale:** 4074 total files, with the API layer (`api/src/`) being the primary focus for this task.

## Architecture

**Type:** Layered Architecture with middleware pipeline pattern.

The API (`api/src/`) follows this request flow:

1. **Express App Setup** (`api/src/app.ts`) — configures middleware pipeline
2. **Middleware Layer** (`api/src/middleware/`) — request processing pipeline:
   - `extractToken` — extracts token from query param, Authorization header, or session cookie → stores in `req.token`
   - `authenticate` — verifies JWT or static token → sets `req.accountability`
   - `schema` — loads schema → sets `req.schema`
   - `sanitizeQuery` — sanitizes query params → sets `req.sanitizedQuery`
   - `requestCounter` — counts requests
   - `cache` — caching layer
3. **Controllers** (`api/src/controllers/`) — route handlers
4. **Services** (`api/src/services/`) — business logic
5. **Permissions** (`api/src/permissions/`) — access control

**WebSocket** (`api/src/websocket/`) has its own parallel authentication via `authenticateConnection()` which also calls `getAccountabilityForToken()`.

## Key Files

### 1. `api/src/middleware/authenticate.ts` — **THE PRIMARY FILE TO REFACTOR**
The authenticate middleware. Currently handles JWT tokens and static user tokens. Needs to be extended to support API keys.

### 2. `api/src/middleware/authenticate.test.ts` — **TEST FILE FOR THE MIDDLEWARE**
Comprehensive tests for the authenticate middleware. Must be updated with API key test cases.

### 3. `api/src/middleware/extract-token.ts` — **TOKEN EXTRACTION MIDDLEWARE**
Extracts tokens from query params (`access_token`), Authorization header (`Bearer`), or session cookie. Stores in `req.token`. May need to be extended to also extract API keys.

### 4. `api/src/middleware/extract-token.test.ts` — **TESTS FOR TOKEN EXTRACTION**
Tests for the extract-token middleware.

### 5. `api/src/utils/get-accountability-for-token.ts` — **CORE AUTHENTICATION LOGIC**
The function that resolves a token to an `Accountability` object. Currently handles:
- **JWT tokens** (detected via `isDirectusJWT()`): verifies the JWT, extracts user/role/session from payload
- **Static user tokens** (non-JWT strings): looks up `directus_users.token` in the database

This is where API key resolution logic would be added.

### 6. `api/src/utils/is-directus-jwt.ts` — **JWT DETECTION**
Checks if a string is a Directus-issued JWT by decoding and checking `iss === 'directus'`.

### 7. `api/src/utils/jwt.ts` — **JWT VERIFICATION**
`verifyJWT()` and `verifyAccessJWT()` — verify JWT tokens with the secret.

### 8. `api/src/utils/verify-session-jwt.ts` — **SESSION VERIFICATION**
Verifies that a session token exists in `directus_sessions` table.

### 9. `api/src/utils/get-secret.ts` — **SECRET RETRIEVAL**
Returns the `SECRET` env variable or generates a random one.

### 10. `api/src/app.ts` — **EXPRESS APP SETUP**
The main Express app. Imports and uses `authenticate` and `extractToken` middleware. This is where the middleware pipeline is defined.

### 11. `api/src/websocket/authenticate.ts` — **WEBSOCKET AUTHENTICATION**
Parallel authentication for WebSocket connections. Also calls `getAccountabilityForToken()`.

### 12. `api/src/websocket/authenticate.test.ts` — **WEBSOCKET AUTH TESTS**

### 13. `api/src/websocket/controllers/base.ts` — **WEBSOCKET CONTROLLER BASE**
Uses `authenticateConnection` from the websocket authenticate module.

### 14. `api/src/services/authentication.ts` — **AUTHENTICATION SERVICE**
The `AuthenticationService` class handles login, token generation, refresh. Uses `getSecret()` and `jwt.sign()`.

### 15. `api/src/permissions/utils/create-default-accountability.ts` — **DEFAULT ACCOUNTABILITY**
Creates a default `Accountability` object with null user/role, false admin/app.

### 16. `packages/types/src/accountability.ts` — **ACCOUNTABILITY TYPE**
```typescript
export type Accountability = {
    role: string | null;
    roles: string[];
    user: string | null;
    admin: boolean;
    app: boolean;
    share?: string;
    ip: string | null;
    userAgent?: string;
    origin?: string;
    session?: string;
};
```

### 17. `api/src/types/express.d.ts` — **EXPRESS TYPE EXTENSIONS**
Defines `req.token`, `req.accountability`, `req.collection`, `req.schema`, `req.sanitizedQuery` on the Express Request.

### 18. `packages/env/src/constants/directus-variables.ts` — **ENV VARIABLES REGISTRY**
List of all recognized environment variables. An `API_KEY` or similar variable would need to be added here.

## Key Symbols

### `handler` (exported function) — `api/src/middleware/authenticate.ts:17`
```typescript
export const handler = async (req: Request, res: Response, next: NextFunction) => { ... }
export default asyncHandler(handler);
```
The main authenticate middleware handler. Flow:
1. Creates default accountability with IP/user-agent/origin
2. Emits `authenticate` filter event — if modified by extensions, short-circuits
3. Calls `getAccountabilityForToken(req.token, defaultAccountability)` to resolve the token
4. On error, clears session cookie if session token is invalid
5. Sets `req.accountability` and calls `next()`

### `getAccountabilityForToken()` — `api/src/utils/get-accountability-for-token.ts:12`
```typescript
export async function getAccountabilityForToken(
    token?: string | null,
    accountability?: Accountability,
): Promise<Accountability>
```
Core token resolution logic:
- If token is a Directus JWT → verify JWT, extract user/role/session, fetch roles tree and global access
- If token is a static string (non-JWT) → look up `directus_users.token` in database
- If no token → return default accountability (anonymous)

### `extractToken` (default export) — `api/src/middleware/extract-token.ts:14`
```typescript
const extractToken: RequestHandler = (req, _res, next) => { ... }
```
Extracts token from (in order):
1. `access_token` query parameter
2. `Authorization: Bearer <token>` header
3. Session cookie (only if no other token found)

### `isDirectusJWT()` — `api/src/utils/is-directus-jwt.ts:7`
```typescript
export default function isDirectusJWT(string: string): boolean
```
Decodes JWT without verification and checks `payload.iss === 'directus'`.

### `verifyAccessJWT()` — `api/src/utils/jwt.ts:25`
```typescript
export function verifyAccessJWT(token: string, secret: string): DirectusTokenPayload
```
Verifies JWT with secret, checks for required fields (role, app_access, admin_access).

### `verifySessionJWT()` — `api/src/utils/verify-session-jwt.ts:10`
```typescript
export async function verifySessionJWT(payload: DirectusTokenPayload): Promise<void>
```
Verifies session exists in `directus_sessions` table.

### `createDefaultAccountability()` — `api/src/permissions/utils/create-default-accountability.ts:3`
```typescript
export function createDefaultAccountability(overrides?: Partial<Accountability>): Accountability
```

### `authenticateConnection()` — `api/src/websocket/authenticate.ts:15`
```typescript
export async function authenticateConnection(
    message: BasicAuthMessage & Record<string, any>,
    accountabilityOverrides?: Partial<Accountability>,
): Promise<AuthenticationState>
```
WebSocket authentication. Also calls `getAccountabilityForToken()`.

### `DirectusTokenPayload` — `api/src/types/auth.ts:30`
```typescript
export type DirectusTokenPayload = {
    id?: string;
    role: string | null;
    app_access: boolean | number;
    admin_access: boolean | number;
    share?: string;
    session?: string;
    enforce_tfa?: boolean;
};
```

## Dependencies

### Module-level dependency flow:
```
app.ts
  ├── middleware/authenticate.ts
  │     ├── utils/get-accountability-for-token.ts
  │     │     ├── utils/is-directus-jwt.ts
  │     │     ├── utils/jwt.ts (verifyAccessJWT)
  │     │     ├── utils/verify-session-jwt.ts
  │     │     ├── utils/get-secret.ts
  │     │     ├── permissions/lib/fetch-roles-tree.ts
  │     │     ├── permissions/modules/fetch-global-access/fetch-global-access.ts
  │     │     └── permissions/utils/create-default-accountability.ts
  │     ├── permissions/utils/create-default-accountability.ts
  │     ├── utils/get-ip-from-req.ts
  │     ├── utils/async-handler.ts
  │     ├── emitter.ts
  │     └── constants.ts
  │
  ├── middleware/extract-token.ts
  │
  └── websocket/authenticate.ts
        └── utils/get-accountability-for-token.ts (same as above)
```

### Files that depend on the authenticate middleware:

1. **`api/src/app.ts`** — imports and uses `authenticate` (line 67, 307) and `extractToken` (line 71, 247)
2. **`api/src/middleware/authenticate.test.ts`** — imports `handler` from `./authenticate.js`
3. **`api/src/websocket/controllers/base.ts`** — imports `authenticateConnection` from `../authenticate.js` (line 19)
4. **`api/src/websocket/authenticate.ts`** — imports `getAccountabilityForToken` from `../utils/get-accountability-for-token.js`
5. **`api/src/websocket/authenticate.test.ts`** — imports `getAccountabilityForToken` and `authenticateConnection`
6. **`api/src/services/authentication.ts`** — uses `getSecret()` and `jwt` for token generation (related, not directly dependent)
7. **`api/src/controllers/auth.ts`** — uses `isDirectusJWT` and `verifyAccessJWT` for token verification in auth flows

### Files that depend on `getAccountabilityForToken`:
1. `api/src/middleware/authenticate.ts` (line 49)
2. `api/src/websocket/authenticate.ts` (line 66)
3. `api/src/middleware/authenticate.test.ts` (indirectly via handler)
4. `api/src/websocket/authenticate.test.ts` (directly mocked)

## Conventions

### Naming Conventions
- **PascalCase** for classes: `AuthenticationService`, `SocketController`, `WebSocketService`
- **camelCase** for functions and variables: `getAccountabilityForToken`, `extractToken`, `createDefaultAccountability`
- **kebab-case** for file names: `authenticate.ts`, `extract-token.ts`, `get-accountability-for-token.ts`
- **No prefix/suffix conventions** for interfaces (e.g., `Accountability` not `IAccountability`)
- **Suffix conventions**: `Service` for service classes (`AuthenticationService`), `Controller` for abstract classes (`SocketController`), `Error` for error classes (`InvalidCredentialsError`)
- **Type suffixes**: `Type` for type files (`auth.ts` → `DirectusTokenPayload`), `Options` for options interfaces (`AuthDriverOptions`)

### Architectural Patterns
- **Middleware Pipeline**: Express middleware chain in `app.ts` — `extractToken` → `authenticate` → `schema` → `sanitizeQuery` → `requestCounter` → `cache` → routes
- **Service Layer**: Business logic in `api/src/services/` classes with constructor taking `AbstractServiceOptions`
- **Dependency Injection**: Services receive `knex`, `schema`, `accountability` via constructor options
- **Emitter Pattern**: `emitter.emitFilter()` for extensibility (e.g., `authenticate` filter event allows extensions to override authentication)
- **Async Handler Wrapper**: All middleware wrapped with `asyncHandler` to catch promise rejections
- **Error Handling**: Custom error classes from `@directus/errors` (e.g., `InvalidCredentialsError`, `InvalidTokenError`, `TokenExpiredError`)

### Style Conventions
- **Async/await** throughout, no raw promises
- **Error handling**: try/catch with `isDirectusError()` type narrowing
- **Validation**: Zod schemas for WebSocket message validation
- **Environment config**: `useEnv()` from `@directus/env` for all configuration
- **Database access**: `getDatabase()` returns a Knex instance
- **Testing**: Vitest with `vi.mock()` for mocking, `vi.spyOn()` for spies

## Similar Implementations

### 1. `api/src/websocket/authenticate.ts` — `authenticateConnection()`
Parallel authentication for WebSocket connections. Uses the same `getAccountabilityForToken()` function. Would need the same API key support.

### 2. `api/src/services/authentication.ts` — `AuthenticationService`
Handles login, token generation, and refresh. Uses `getSecret()` and `jwt.sign()`. Related because API keys would be a different authentication method alongside JWT and static tokens.

## Context for the Task

### What needs to change

The task is to refactor the authenticate middleware to support **API keys** in addition to JWT tokens and static user tokens.

### Current authentication flow

```
Request → extractToken (extracts token from query/header/cookie → req.token)
        → authenticate (resolves req.token to req.accountability)
            → getAccountabilityForToken(token, defaultAccountability)
                → if isDirectusJWT(token): verify JWT, extract user/role
                → else: look up directus_users.token in database
                → if no token: return anonymous accountability
```

### What needs to be added

1. **API key detection**: A way to distinguish API keys from JWT tokens and static user tokens (e.g., a prefix like `pk_` or a separate header)
2. **API key resolution**: Look up the API key in a database table (likely `directus_users.api_key` or a new `directus_api_keys` table) and resolve to a user/role
3. **Extract-token enhancement**: Optionally support a separate header for API keys (e.g., `X-API-Key`)
4. **Env configuration**: Add env vars for API key support (e.g., `API_KEY_ENABLED`, `API_KEY_HEADER`)

### Key code snippets

**Current authenticate middleware** (`api/src/middleware/authenticate.ts`):
```typescript
export const handler = async (req: Request, res: Response, next: NextFunction) => {
    const env = useEnv();
    const defaultAccountability: Accountability = createDefaultAccountability({ ip: getIPFromReq(req) });
    // ... userAgent, origin setup ...
    const customAccountability = await emitter.emitFilter('authenticate', defaultAccountability, { req }, { database, schema: null, accountability: null });
    if (customAccountability && isEqual(customAccountability, defaultAccountability) === false) {
        req.accountability = customAccountability;
        return next();
    }
    try {
        req.accountability = await getAccountabilityForToken(req.token, defaultAccountability);
    } catch (err) {
        if (isDirectusError(err, ErrorCode.InvalidCredentials) || isDirectusError(err, ErrorCode.InvalidToken)) {
            if (req.cookies[env['SESSION_COOKIE_NAME'] as string] === req.token) {
                res.clearCookie(env['SESSION_COOKIE_NAME'] as string, SESSION_COOKIE_OPTIONS);
            }
        }
        throw err;
    }
    return next();
};
```

**Current token resolution** (`api/src/utils/get-accountability-for-token.ts`):
```typescript
export async function getAccountabilityForToken(token?: string | null, accountability?: Accountability): Promise<Accountability> {
    if (!accountability) accountability = createDefaultAccountability();
    const database = getDatabase();
    if (token) {
        if (isDirectusJWT(token)) {
            const payload = verifyAccessJWT(token, getSecret());
            // ... JWT handling ...
        } else {
            const user = await database.select('directus_users.id', 'directus_users.role')
                .from('directus_users').where({ 'directus_users.token': token, status: 'active' }).first();
            // ... static token handling ...
        }
    }
    return accountability;
}
```

**Current token extraction** (`api/src/middleware/extract-token.ts`):
```typescript
const extractToken: RequestHandler = (req, _res, next) => {
    let token: string | null = null;
    if (req.query && req.query['access_token']) token = req.query['access_token'] as string;
    if (req.headers && req.headers.authorization) {
        const parts = req.headers.authorization.split(' ');
        if (parts.length === 2 && parts[0]!.toLowerCase() === 'bearer') {
            if (token !== null) throw new InvalidPayloadError({ reason: '...' });
            token = parts[1]!;
        }
    }
    if (req.cookies && req.cookies[env['SESSION_COOKIE_NAME'] as string]) {
        if (token === null) token = req.cookies[env['SESSION_COOKIE_NAME'] as string];
    }
    req.token = token;
    next();
};
```

### Files to modify

| File | Change |
|------|--------|
| `api/src/middleware/authenticate.ts` | Add API key detection and handling in the handler |
| `api/src/middleware/authenticate.test.ts` | Add tests for API key authentication |
| `api/src/utils/get-accountability-for-token.ts` | Add API key resolution logic (look up API key in DB) |
| `api/src/middleware/extract-token.ts` | Optionally support `X-API-Key` header or API key prefix |
| `api/src/middleware/extract-token.test.ts` | Add tests for API key extraction |
| `packages/env/src/constants/directus-variables.ts` | Add API key env variables (e.g., `API_KEY_HEADER`) |

### Files that depend on the middleware (no changes needed but must be aware)

| File | Dependency |
|------|------------|
| `api/src/app.ts` | Uses `authenticate` and `extractToken` middleware |
| `api/src/websocket/authenticate.ts` | Uses `getAccountabilityForToken()` |
| `api/src/websocket/authenticate.test.ts` | Tests websocket auth |
| `api/src/websocket/controllers/base.ts` | Uses `authenticateConnection` |
| `api/src/services/authentication.ts` | Related — generates JWT tokens |
| `api/src/controllers/auth.ts` | Related — uses `isDirectusJWT` and `verifyAccessJWT` |