Now I have all the information needed. Let me compile the comprehensive context document.

---

## Project Summary

**Directus** — an open-source headless CMS and backend-as-a-service. The project is a TypeScript monorepo with 4,074 files (2,796 TypeScript source files, 562 Vue files). The API layer (`api/src`) contains Express.js middleware, controllers, services, and utilities. The `packages/errors` directory contains a custom error framework.

## Architecture

**Layered Express.js architecture** with middleware pipeline:

1. **Security/Infrastructure middleware** (helmet, CORS, pressure limiter, rate limiter)
2. **Request parsing middleware** (JSON body parser, cookie-parser, `extractToken`)
3. **Authentication middleware** (`authenticate`) — verifies JWT or static tokens
4. **Schema/Query middleware** (schema loading, sanitizeQuery, cache)
5. **Route controllers** (auth, items, files, users, etc.)
6. **Not-found handler** → **Error handler** (last in chain)

Middleware registration order in `api/src/app.ts`:
```
cookieParser → extractToken → rateLimiter → authenticate → schema → sanitizeQuery → cache → routes → notFoundHandler → errorHandler
```

## Key Files

### 1. `api/src/middleware/authenticate.ts` — **THE CRASH SITE**
The authenticate middleware. Calls `getAccountabilityForToken(req.token, defaultAccountability)` inside a try/catch. Catches `InvalidCredentials` and `InvalidToken` errors to clear session cookies, then **re-throws** them. The handler is wrapped with `asyncHandler`.

### 2. `api/src/middleware/extract-token.ts` — **TOKEN EXTRACTION**
Extracts token from query param, Authorization header, or session cookie. Stores in `req.token`. Throws `InvalidPayloadError` (400) if multiple auth methods used.

### 3. `api/src/utils/jwt.ts` — **JWT VERIFICATION (CRASH POINT)**
Contains `verifyJWT()` and `verifyAccessJWT()`. `verifyJWT` calls `jwt.verify()` from `jsonwebtoken`. Catches `jwt.TokenExpiredError` → throws `TokenExpiredError` (401). Catches `jwt.JsonWebTokenError` → throws `InvalidTokenError` (403). **Any other error** → throws `ServiceUnavailableError`.

### 4. `api/src/utils/is-directus-jwt.ts` — **JWT FORMAT CHECK**
Uses `jwt.decode()` (no verification) to check if `payload.iss === 'directus'`. Returns `false` on any exception (malformed token that can't even be decoded).

### 5. `api/src/utils/get-accountability-for-token.ts` — **TOKEN RESOLUTION**
Routes token to JWT verification or static token lookup. If `isDirectusJWT(token)` returns true, calls `verifyAccessJWT()`. Otherwise does a DB lookup for static tokens.

### 6. `api/src/middleware/error-handler.ts` — **ERROR RESPONSE**
Last middleware. Handles both Directus errors (structured) and unknown errors. For non-Directus errors in production, returns generic 500. Has its own `asyncErrorHandler` wrapper.

### 7. `api/src/utils/async-handler.ts` — **EXPRESS ASYNC WRAPPER**
Wraps async handlers: `Promise.resolve(fn(req, res, next)).catch(next)`. Passes rejected errors to Express's `next(err)`.

### 8. `packages/errors/src/create-error.ts` — **ERROR FACTORY**
Creates error classes with `name = 'DirectusError'`, `code`, `status`, `extensions`.

### 9. `packages/errors/src/is-directus-error.ts` — **ERROR TYPE GUARD**
Checks if value is `object`, not null, not array, has `name === 'DirectusError'`. Optionally checks `code`.

### 10. `api/src/app.ts` — **MIDDLEWARE REGISTRATION**
Lines 307: `app.use(authenticate)` — registers authenticate middleware after rate limiter, before routes.

## Key Symbols

### `handler` (authenticate.ts:17-62)
```typescript
export const handler = async (req: Request, res: Response, next: NextFunction) => {
    // Creates default accountability, emits 'authenticate' filter
    // Calls getAccountabilityForToken(req.token, defaultAccountability)
    // Catches InvalidCredentials/InvalidToken → clears session cookie → re-throws
}
export default asyncHandler(handler);
```

### `verifyJWT(token: string, secret: string)` (jwt.ts:5-23)
```typescript
export function verifyJWT(token: string, secret: string) {
    // jwt.verify(token, secret, { issuer: 'directus' })
    // Catches: jwt.TokenExpiredError → TokenExpiredError (401)
    // Catches: jwt.JsonWebTokenError → InvalidTokenError (403)
    // Catches: anything else → ServiceUnavailableError
}
```

### `verifyAccessJWT(token: string, secret: string)` (jwt.ts:25-33)
```typescript
export function verifyAccessJWT(token: string, secret: string) {
    const payload = verifyJWT(token, secret) as DirectusTokenPayload;
    // Validates role, app_access, admin_access exist
    // Throws InvalidTokenError if missing
}
```

### `isDirectusJWT(string: string): boolean` (is-directus-jwt.ts:7-15)
```typescript
export default function isDirectusJWT(string: string): boolean {
    // jwt.decode(string, { json: true }) — no verification
    // Returns false if payload?.iss !== 'directus'
    // Returns false on ANY exception (catch block)
}
```

### `getAccountabilityForToken(token?, accountability?)` (get-accountability-for-token.ts:12-69)
```typescript
export async function getAccountabilityForToken(token?, accountability?) {
    if (token) {
        if (isDirectusJWT(token)) {
            const payload = verifyAccessJWT(token, getSecret()); // <-- CRASH HERE
            // ... sets accountability from payload
        } else {
            // static token DB lookup
        }
    }
    return accountability;
}
```

### `asyncHandler` (async-handler.ts:3-4)
```typescript
const asyncHandler = (fn: RequestHandler) => (req, res, next) =>
    Promise.resolve(fn(req, res, next)).catch(next);
```

### Error classes
| Error | Code | Status | Thrown When |
|-------|------|--------|-------------|
| `InvalidTokenError` | `INVALID_TOKEN` | 403 | JWT malformed, wrong issuer, missing required claims |
| `TokenExpiredError` | `TOKEN_EXPIRED` | 401 | JWT expired |
| `InvalidCredentialsError` | `INVALID_CREDENTIALS` | 401 | Static token not found in DB |
| `InvalidPayloadError` | `INVALID_PAYLOAD` | 400 | Multiple auth methods used |
| `ServiceUnavailableError` | `SERVICE_UNAVAILABLE` | 503 | Unexpected JWT verification error |

## Dependencies

### Execution chain (middleware pipeline):
```
Request
  → extractToken (sets req.token)
  → authenticate (handler)
    → createDefaultAccountability
    → emitter.emitFilter('authenticate', ...)
    → getAccountabilityForToken(req.token, defaultAccountability)
      → isDirectusJWT(token)  [jwt.decode - no verify]
        → if true: verifyAccessJWT(token, getSecret())
          → verifyJWT(token, secret)
            → jwt.verify(token, secret, { issuer: 'directus' })
              → throws jwt.JsonWebTokenError on malformed
              → throws jwt.TokenExpiredError on expired
          → verifyAccessJWT validates payload shape
        → if false: static token DB lookup
      → returns accountability
    → req.accountability = ...
    → next()
  → [routes]
  → notFoundHandler
  → errorHandler
```

### Module dependencies:
- `authenticate.ts` imports: `@directus/env`, `@directus/errors`, `@directus/types`, `lodash-es`, `constants`, `database`, `emitter`, `permissions/utils`, `async-handler`, `get-accountability-for-token`, `get-ip-from-req`
- `get-accountability-for-token.ts` imports: `@directus/errors`, `@directus/types`, `database`, `fetch-roles-tree`, `fetch-global-access`, `create-default-accountability`, `get-secret`, `is-directus-jwt`, `jwt`, `verify-session-jwt`
- `jwt.ts` imports: `@directus/errors`, `jsonwebtoken`, `types`
- `error-handler.ts` imports: `@directus/errors`, `@directus/types`, `@directus/utils`, `@directus/utils/node`, `express`, `database`, `emitter`, `logger`

## Conventions

### Naming conventions
- **PascalCase** for classes, interfaces, types, exported functions (`DirectusTokenPayload`, `InvalidTokenError`, `verifyAccessJWT`)
- **camelCase** for variables, parameters, local functions (`defaultAccountability`, `customAccountability`)
- **Error classes** use suffix `Error` (`InvalidTokenError`, `TokenExpiredError`, `InvalidCredentialsError`)
- **Error codes** are `UPPER_SNAKE_CASE` strings in an enum (`ErrorCode.InvalidToken = 'INVALID_TOKEN'`)
- **Interfaces** use PascalCase with no prefix (`AuthDriverOptions`, `DirectusTokenPayload`)
- **File names** are kebab-case (`get-accountability-for-token.ts`, `is-directus-jwt.ts`)

### Architectural patterns
- **Middleware pipeline** pattern with Express.js — each middleware calls `next()` or throws
- **Error-as-values** pattern via `@directus/errors` — all errors are `DirectusError` instances with `code`, `status`, `extensions`
- **Async wrapper** pattern — `asyncHandler` wraps async handlers, passes rejections to `next(err)`
- **Dependency injection** via function imports (no DI container) — `getDatabase()`, `useEnv()`, `useLogger()` are module-level singletons
- **Emitter pattern** — `emitter.emitFilter()` for hooking into authentication flow

### Style conventions
- **Async/await** throughout — no raw promises or callbacks
- **Error handling**: try/catch blocks that re-throw typed errors; `isDirectusError()` type guard for checking error type
- **Validation**: `isDirectusJWT()` uses `jwt.decode()` (no signature verification) as a lightweight format check before calling `jwt.verify()`
- **TypeScript strict mode** — explicit type annotations on all function signatures

## Similar Implementations

No AST-based similar classes found (project may not be fully parsed). However, the pattern of `asyncHandler` wrapping is used consistently across all middleware files:
- `api/src/middleware/cache.ts`
- `api/src/middleware/graphql.ts`
- `api/src/middleware/sanitize-query.ts`

## Context for the Task

### The Bug: Crash in authenticate middleware when JWT is malformed

**Root cause analysis:**

When a malformed JWT token is presented, the execution chain is:

1. **`extractToken`** extracts the token from the request and sets `req.token`. No validation here — it just passes the raw string through.

2. **`authenticate` handler** calls `getAccountabilityForToken(req.token, defaultAccountability)` at line 49.

3. **`getAccountabilityForToken`** (line 24) calls `isDirectusJWT(token)` which uses `jwt.decode()` — this is a **non-verifying** decode. If the token is so malformed that `jwt.decode()` throws, `isDirectusJWT` catches it and returns `false`. This is safe.

4. **If `isDirectusJWT` returns `true`** (token has valid JWT structure with `iss: 'directus'`), it calls `verifyAccessJWT(token, getSecret())` at line 25.

5. **`verifyAccessJWT`** calls `verifyJWT(token, secret)` at line 26.

6. **`verifyJWT`** calls `jwt.verify(token, secret, { issuer: 'directus' })` at line 9. This is where the crash happens:
   - If the token is malformed (invalid base64, bad signature, wrong structure), `jsonwebtoken` throws a `JsonWebTokenError`
   - This is caught at line 15 and converted to `InvalidTokenError` (403)
   - **BUT** if `jsonwebtoken` throws something that is NOT a `TokenExpiredError` or `JsonWebTokenError` (e.g., a `SyntaxError` from a completely garbled string, or a `TypeError` from unexpected input), it falls through to line 18 and throws `ServiceUnavailableError` (503)

7. **Back in `authenticate` handler** (line 50-58): The catch block checks for `InvalidCredentials` or `InvalidToken` errors. If the error is `ServiceUnavailableError` (from the fallthrough in step 6), it is **NOT caught** by the condition at line 51, so the session cookie is NOT cleared, and the error is re-thrown at line 58.

8. **`asyncHandler`** catches the rejected promise and calls `next(err)`, passing it to Express's error handling pipeline.

9. **`errorHandler`** receives the error. If it's a `DirectusError` (which `ServiceUnavailableError` is), it formats it properly and returns a JSON response. **No crash should occur here** — the error handler handles all `DirectusError` instances.

**The actual crash scenario** is more likely this: if `isDirectusJWT` returns `false` (because `jwt.decode` throws or `iss !== 'directus'`), the code falls to the `else` branch at line 43, which does a **static token DB lookup**. If the malformed token happens to look like a non-JWT string, it queries `directus_users` with `token: <malformed_string>`. This won't crash — it just won't find a user and throws `InvalidCredentialsError`.

**The real crash risk** is in `isDirectusJWT` itself: if `jwt.decode()` throws something other than what's expected (e.g., a `TypeError` because the input is not a string), the catch block at line 12 returns `false`. This is safe.

**Most likely crash scenario**: If `req.token` is `undefined` or `null` (no token provided), `getAccountabilityForToken` skips the `if (token)` block entirely (line 23) and returns the default accountability. This is the normal unauthenticated flow and works fine.

**The actual bug** is likely in the **`extractToken` middleware**: if the Authorization header has a malformed format (e.g., `Bearer ` with nothing after, or just `Bearer` with no space), the `parts[1]` at line 37 could be `undefined`, and `req.token` gets set to `undefined`. Then in `getAccountabilityForToken`, `if (token)` is falsy, so it skips auth — this is actually safe.

**Key finding**: The most dangerous path is when a token passes `isDirectusJWT` (has valid JWT structure with `iss: 'directus'`) but fails `jwt.verify()` with an error that is neither `TokenExpiredError` nor `JsonWebTokenError`. In that case, `verifyJWT` throws `ServiceUnavailableError` (503), which is a valid `DirectusError` and will be handled by the error handler. **No crash should occur** — the error handling chain is complete.

**However**, there is a subtle issue: the `authenticate` handler's catch block (line 51) only checks for `InvalidCredentials` and `InvalidToken`, but `verifyJWT` can throw `TokenExpiredError` (401) which is **NOT** caught by the condition. If a token is expired, the catch block doesn't clear the session cookie and re-throws. This is a **minor bug** — expired tokens should also trigger cookie clearing.

### Key code snippets

**The authenticate handler's error handling gap** (authenticate.ts:48-59):
```typescript
try {
    req.accountability = await getAccountabilityForToken(req.token, defaultAccountability);
} catch (err) {
    if (isDirectusError(err, ErrorCode.InvalidCredentials) || isDirectusError(err, ErrorCode.InvalidToken)) {
        if (req.cookies[env['SESSION_COOKIE_NAME'] as string] === req.token) {
            res.clearCookie(env['SESSION_COOKIE_NAME'] as string, SESSION_COOKIE_OPTIONS);
        }
    }
    throw err;  // TokenExpiredError (401) is NOT caught — re-thrown without cookie clearing
}
```

**The JWT verification error mapping** (jwt.ts:5-23):
```typescript
export function verifyJWT(token: string, secret: string) {
    try {
        payload = jwt.verify(token, secret, { issuer: 'directus' });
    } catch (err) {
        if (err instanceof jwt.TokenExpiredError) {
            throw new TokenExpiredError();       // 401
        } else if (err instanceof jwt.JsonWebTokenError) {
            throw new InvalidTokenError();        // 403
        } else {
            throw new ServiceUnavailableError({ service: 'jwt', reason: `Couldn't verify token.` }); // 503
        }
    }
}
```

**The isDirectusJWT safety net** (is-directus-jwt.ts:7-15):
```typescript
export default function isDirectusJWT(string: string): boolean {
    try {
        const payload = jwt.decode(string, { json: true });
        if (payload?.iss !== 'directus') return false;
        return true;
    } catch {
        return false;  // Any decode failure → treat as non-JWT
    }
}
```