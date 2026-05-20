Now I have all the information. Let me compile the full context document.

---

## 1. PROJECT SUMMARY

**Project:** Directus — an open-source headless CMS and backend-as-a-service.
**Tech Stack:** TypeScript (2792 files), Vue 3 (562 files), Express.js, Knex.js (SQL query builder), Joi validation.
**Scale:** ~4068 total files, 54 controllers, 139 services, 21 middleware files.
**Key Packages:** `@directus/errors` (error types), `@directus/types` (shared types), `@directus/validation` (Joi-based validation).

## 2. ARCHITECTURE

**Architecture Type:** Layered MVC with Service Layer pattern.

- **Controllers** (`api/src/controllers/`) — Express routers, handle HTTP request/response, delegate to services.
- **Services** (`api/src/services/`) — Business logic layer. `ItemsService` is the base CRUD service. `UsersService` extends `ItemsService` for user-specific logic.
- **Middleware** (`api/src/middleware/`) — Auth, error handling, rate limiting.
- **Auth Drivers** (`api/src/auth/drivers/`) — Authentication providers (local, OAuth2, LDAP, etc.).
- **Database** (`api/src/database/`) — Knex query builder, error translation (per-dialect).
- **Packages** (`packages/errors/`, `packages/types/`, `packages/validation/`) — Shared libraries.

**Key Flow for User Creation:**
1. `POST /users` → `api/src/controllers/users.ts` → `UsersService.createOne()` or `createMany()`
2. `POST /users/register` → `api/src/controllers/users.ts` → `UsersService.registerUser()` → `UsersService.createOne()`
3. `POST /users/invite` → `api/src/controllers/users.ts` → `UsersService.inviteUser()` → `UsersService.createOne()`
4. `UsersService.createOne()` → validates email → checks unique emails → checks password policy → calls `ItemsService.createOne()`
5. `ItemsService.createOne()` → runs in transaction → checks `opts.preMutationError` → inserts into DB → translates DB errors

## 3. RELATED FILES

| File | Path | Entity Type | Relevance |
|------|------|-------------|-----------|
| **Users Service** | `api/src/services/users.ts` | Service | **Primary file.** Contains `createOne()`, `createMany()`, `checkUniqueEmails()`, `registerUser()`, `inviteUser()`. The bug is here. |
| **Items Service** | `api/src/services/items.ts` | Service | Base CRUD service. Contains `createOne()` which checks `opts.preMutationError` and handles DB-level unique constraint errors. |
| **Users Controller** | `api/src/controllers/users.ts` | Controller | HTTP routes for user CRUD, register, invite. Calls UsersService. |
| **Auth Controller** | `api/src/controllers/auth.ts` | Controller | Login routes. Uses `AuthenticationService.login()` which queries `directus_users`. |
| **Authentication Service** | `api/src/services/authentication.ts` | Service | Login flow. Reads user by email, checks status, handles rate limiting. |
| **Local Auth Driver** | `api/src/auth/drivers/local.ts` | Auth Driver | Local login handler. Queries user by email (case-insensitive). |
| **Error Handler Middleware** | `api/src/middleware/error-handler.ts` | Middleware | Catches thrown errors and formats JSON response. |
| **RecordNotUniqueError** | `packages/errors/src/errors/record-not-unique.ts` | Error | Error type for duplicate values. Status 400. |
| **Error Codes** | `packages/errors/src/codes.ts` | Constants | Enum of all error codes including `RecordNotUnique`. |
| **DB Error Translator** | `api/src/database/errors/translate.ts` | Utility | Translates raw DB errors (e.g., Postgres unique violation) into Directus errors. |
| **Postgres Error Handler** | `api/src/database/errors/dialects/postgres.ts` | Utility | Extracts field/collection from Postgres unique violation errors. |
| **MutationOptions Type** | `packages/types/src/items.ts` | Type | Defines `preMutationError` field used to defer validation errors. |
| **Users Service Tests** | `api/src/services/users.test.ts` | Test | Tests for user creation, email uniqueness, invite, register flows. |

## 4. DEPENDENCY GRAPH

### File Dependencies

```
api/src/controllers/users.ts
  → api/src/services/users.ts
  → api/src/services/authentication.ts
  → api/src/services/meta.ts
  → api/src/services/tfa.ts

api/src/services/users.ts
  → api/src/services/items.ts (extends ItemsService)
  → api/src/services/mail/index.ts
  → api/src/services/settings.ts
  → api/src/database/index.ts
  → api/src/database/errors/translate.ts
  → packages/errors/src/errors/record-not-unique.ts
  → packages/types/src/items.ts (MutationOptions)
  → packages/validation/src/index.ts

api/src/services/items.ts
  → api/src/database/errors/translate.ts
  → api/src/database/run-ast/run-ast.ts
  → api/src/permissions/modules/process-payload/process-payload.ts
  → api/src/permissions/modules/validate-access/validate-access.ts
  → api/src/utils/transaction.ts
  → api/src/services/payload.ts
  → packages/errors/src/codes.ts
  → packages/types/src/items.ts
```

### Call Graph (User Creation Flow)

```
POST /users (controller)
  → UsersService.createOne(data, opts)
    → validateEmail(data.email)
    → checkUniqueEmails([data.email])        ← Application-level check
    → checkPasswordPolicy([data.password])
    → ItemsService.createOne(data, opts)     ← super.createOne()
      → transaction() starts
        → emitter.emitFilter()               ← hooks
        → processPayload()                   ← permissions
        → if (opts.preMutationError) throw   ← throws deferred error
        → trx.insert() into DB
        → catch (err) → translateDatabaseError(err)  ← DB-level check
          → if RecordNotUnique → throw
        → processO2M, activity, revisions
      → transaction() commits/rolls back
```

### Module Graph

```
controllers → services → database
                       → permissions
                       → utils
services → items (base) → database
                        → permissions
                        → utils
                        → packages (errors, types, validation)
```

## 5. CONVENTIONS

### Naming Conventions
1. **Service classes** end with `Service`: `UsersService`, `ItemsService`, `AuthenticationService`, `SettingsService`, `MailService`
2. **Controller files** are named by resource: `users.ts`, `auth.ts`, `collections.ts`
3. **Error classes** use PascalCase with `Error` suffix: `RecordNotUniqueError`, `InvalidPayloadError`, `ForbiddenError`
4. **Error codes** are UPPER_SNAKE_CASE strings: `'RECORD_NOT_UNIQUE'`, `'INVALID_PAYLOAD'`
5. **Interfaces** use PascalCase with no prefix: `MutationOptions`, `AbstractServiceOptions`, `PrimaryKey`
6. **Private methods** use camelCase: `checkUniqueEmails()`, `checkPasswordPolicy()`, `validateEmail()`
7. **Override methods** use `override async`: `override async createOne()`, `override async createMany()`
8. **Environment variables** are accessed via `env['UPPER_SNAKE_CASE']` pattern
9. **Database columns** use snake_case: `directus_users`, `auth_password_policy`, `tfa_secret`
10. **Error extensions** use `{ collection, field, value }` pattern

### Architectural Patterns
- **Service Layer Pattern**: `UsersService` extends `ItemsService` (base CRUD) and adds domain-specific validation
- **Deferred Error Pattern**: Validation errors are caught and stored in `opts.preMutationError`, then thrown inside the transaction in `ItemsService.createOne()` (line 188-189)
- **Transaction Wrapping**: All mutations wrapped in `transaction(this.knex, async (trx) => {...})`
- **Error Translation**: Raw DB errors are translated via `translateDatabaseError()` per-dialect
- **Case-Insensitive Email**: Emails are lowercased before comparison: `whereRaw('LOWER(??) = ?', ['email', email.toLowerCase()])`

### Style Conventions
- **Async/await** used throughout
- **Error handling**: `try/catch` with specific error types from `@directus/errors`
- **Validation**: Joi schemas for input validation at controller level, custom validation in services
- **Constructor pattern**: `constructor(options: AbstractServiceOptions)` with `super(collection, options)`

## 6. SIMILAR IMPLEMENTATIONS

| Class | File | Why Similar |
|-------|------|-------------|
| **ItemsService** | `api/src/services/items.ts` | Base class for `UsersService`. Contains `createOne()` with `preMutationError` check and DB error translation. |
| **AuthenticationService** | `api/src/services/authentication.ts` | Also queries `directus_users` table. Uses `getUserByEmail` pattern. Has rate limiting logic. |
| **SettingsService** | `api/src/services/settings.ts` | Extends `ItemsService` like `UsersService`. Uses same `preMutationError` pattern. |
| **ActivityService** | `api/src/services/activity.ts` | Extends `ItemsService`. Used within transactions for audit logging. |
| **MailService** | `api/src/services/mail/index.ts` | Used by `UsersService` for invite/registration emails. |

## 7. TASK CONTEXT

### The Bug: Crash when creating user with duplicate email

**Root Cause:** There are **two layers of duplicate email checking**, and the interaction between them causes a crash:

1. **Application-level check** (`UsersService.checkUniqueEmails` at line 50-81): Queries the DB for existing emails. If found, throws `RecordNotUniqueError`. This error is **caught** in `UsersService.createOne()` (line 200-202) and stored in `opts.preMutationError`.

2. **DB-level check** (`ItemsService.createOne` at line 267-278): After the `preMutationError` is thrown (line 188-189), the transaction rolls back. But if the application-level check **misses** the duplicate (e.g., due to a race condition or case-sensitivity issue), the DB insert fails with a unique constraint violation, which is caught and translated by `translateDatabaseError()`.

**The crash scenario:** When `checkUniqueEmails` correctly detects a duplicate, it throws `RecordNotUniqueError`. This is caught and stored as `opts.preMutationError`. Then `super.createOne()` is called, which enters a transaction. Inside the transaction, `opts.preMutationError` is thrown (line 188-189). The transaction rolls back. The error propagates up to the controller.

**But there's a subtle issue in `createMany`:** `UsersService.createMany()` (line 218-253) validates all emails upfront, then creates a **new `ItemsService` instance** (line 246) and calls `itemsService.createMany(data, opts)`. The `ItemsService.createMany()` iterates over each item and calls `service.createOne()` for each. Since `service` is an `ItemsService` (not `UsersService`), it does NOT re-validate emails. The `preMutationError` is set once and will be thrown on the **first** item's `createOne` call. This means if you create 2 users with the same email in a batch, the first one fails with `preMutationError`, but the transaction rolls back all changes.

**The actual crash:** The issue is that `checkUniqueEmails` in `createOne` catches the error and sets `preMutationError`, but then the code **continues execution** — it sets `userIntegrityCheckFlags` and calls `super.createOne()`. Inside `super.createOne()`, the `preMutationError` is thrown inside a transaction. If the error is not a `DirectusError` (e.g., if `checkUniqueEmails` throws something unexpected), or if the error handling in the controller doesn't properly catch it, it can crash.

**Key files to fix:**
- `api/src/services/users.ts` — `createOne()` (line 190-213), `checkUniqueEmails()` (line 50-81), `createMany()` (line 218-253)
- `api/src/controllers/users.ts` — POST `/` handler (line 28-65) — the `try/catch` only handles `ForbiddenError`, not `RecordNotUniqueError`

**What to be careful about:**
- The `preMutationError` pattern defers errors but the controller's `try/catch` (line 54-60) only catches `ForbiddenError` — other errors will propagate as unhandled
- Race conditions: two concurrent requests with the same email could both pass `checkUniqueEmails` (since neither has inserted yet), then one succeeds and the other gets a DB-level unique violation
- The DB-level error translation in `translateDatabaseError` produces a `RecordNotUniqueError` with different extensions format than the application-level one
- The `createMany` path bypasses `UsersService.createOne` and uses `ItemsService.createMany` directly, so per-item email validation is skipped

## 8. RELEVANT CODE SNIPPETS

### Snippet 1: UsersService.createOne — catches validation errors and defers them
**File:** `api/src/services/users.ts`, lines 190-213
```typescript
override async createOne(data: Partial<Item>, opts: MutationOptions = {}): Promise<PrimaryKey> {
    try {
        if ('email' in data && data['email'] !== undefined) {
            this.validateEmail(data['email']);
            await this.checkUniqueEmails([data['email']]);
        }
        if ('password' in data) {
            await this.checkPasswordPolicy([data['password']]);
        }
    } catch (err: any) {
        opts.preMutationError = err;  // Error is deferred, not thrown
    }
    // ... continues to set userIntegrityCheckFlags ...
    return await super.createOne(data, opts);
}
```

### Snippet 2: ItemsService.createOne — throws preMutationError inside transaction
**File:** `api/src/services/items.ts`, lines 188-190
```typescript
if (opts.preMutationError) {
    throw opts.preMutationError;  // Thrown inside transaction → rollback
}
```

### Snippet 3: checkUniqueEmails — application-level duplicate check
**File:** `api/src/services/users.ts`, lines 50-81
```typescript
private async checkUniqueEmails(emails: string[], excludeKey?: PrimaryKey): Promise<void> {
    emails = emails.map((email) => email.toLowerCase());
    const duplicates = emails.filter((value, index, array) => array.indexOf(value) !== index);
    if (duplicates.length) {
        throw new RecordNotUniqueError({ collection: 'directus_users', field: 'email', value: '[' + String(duplicates) + ']' });
    }
    const query = this.knex.select('email').from('directus_users')
        .whereRaw(`LOWER(??) IN (${emails.map(() => '?')})`, ['email', ...emails]);
    if (excludeKey) { query.whereNot('id', excludeKey); }
    const results = await query;
    if (results.length) {
        throw new RecordNotUniqueError({ collection: 'directus_users', field: 'email', value: '[' + String(emails) + ']' });
    }
}
```

### Snippet 4: UsersController POST / — only catches ForbiddenError
**File:** `api/src/controllers/users.ts`, lines 28-65
```typescript
router.post('/', asyncHandler(async (req, res, next) => {
    const service = new UsersService({ accountability: req.accountability, schema: req.schema });
    const savedKeys: PrimaryKey[] = [];
    if (Array.isArray(req.body)) {
        const keys = await service.createMany(req.body);
        savedKeys.push(...keys);
    } else {
        const key = await service.createOne(req.body);
        savedKeys.push(key);
    }
    try {
        // ... read back created items ...
    } catch (error: any) {
        if (isDirectusError(error, ErrorCode.Forbidden)) {
            return next();  // Only ForbiddenError is handled!
        }
        throw error;  // RecordNotUniqueError propagates unhandled
    }
    return next();
}));
```

### Snippet 5: UsersService.createMany — bypasses UsersService.createOne
**File:** `api/src/services/users.ts`, lines 244-252
```typescript
// Use generic ItemsService to avoid calling `UserService.createOne` to avoid additional work of validating emails,
// as this requires one query per email if done in `createOne`
const itemsService = new ItemsService(this.collection, {
    schema: this.schema,
    accountability: this.accountability,
    knex: this.knex,
});
return await itemsService.createMany(data, opts);
```