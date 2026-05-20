Now I have all the context needed. Let me compile the full output.

---

### 1. PROJECT SUMMARY

**Project:** Strapi CMS — open-source headless CMS (Node.js/TypeScript monorepo)
**Scale:** 5,907 files, 3,605 TypeScript files, 824 JavaScript files
**Key package for this task:** `packages/core/content-type-builder` — the Content-Type Builder plugin
**Tech stack:** Koa (HTTP), TypeScript, Yup validation, Zod validation (v4), Lodash, Strapi plugin system

### 2. ARCHITECTURE

**Architecture type:** Plugin-based Modular Monolith with a layered backend pattern: **Routes → Middlewares → Controllers → Services**

The content-type-builder plugin follows the standard Strapi plugin structure:

| Layer | Directory | Purpose |
|-------|-----------|---------|
| **Routes** | `server/src/routes/` | Two route types: `admin` (admin panel API) and `content-api` (public API with Zod schemas) |
| **Controllers** | `server/src/controllers/` | Handle HTTP requests, validate input, call services, return responses |
| **Services** | `server/src/services/` | Business logic — CRUD operations on content types, components, schema |
| **Middlewares** | `server/src/middlewares/` | `isDevelopmentMode` — blocks mutations in production |
| **Validation** | `server/src/controllers/validation/` | Yup-based validation schemas for input payloads |

**Request flow:** Route → (optional middleware) → Controller → Service → Response

**Route types:**
- **Admin routes** (`routes/admin.ts`): `type: 'admin'`, use policy `admin::hasPermissions` with action `plugin::content-type-builder.read`
- **Content API routes** (`routes/content-api.ts`): `type: 'content-api'`, use Zod schemas for request/response validation, created via `createContentApiRoutesFactory`

### 3. RELATED FILES

| # | File | Entity Type | Purpose & Relevance |
|---|------|-------------|---------------------|
| 1 | `packages/core/content-type-builder/server/src/controllers/content-types.ts` | **Controller** | **Primary file to modify.** Contains `getContentTypes`, `getContentType`, `createContentType`, `updateContentType`, `deleteContentType`. Add the new `exportContentType` method here. |
| 2 | `packages/core/content-type-builder/server/src/services/content-types.ts` | **Service** | **Primary file to modify.** Contains `formatContentType`, `createContentType`, `editContentType`, `deleteContentType`. Add the new `exportContentTypeAsJson` service method here. |
| 3 | `packages/core/content-type-builder/server/src/routes/admin.ts` | **Route** | **Must modify.** Contains all admin route definitions. Add the new route entry for the export endpoint here. |
| 4 | `packages/core/content-type-builder/server/src/controllers/index.ts` | **Controller Index** | Exports all controllers. No change needed — `content-types` is already registered. |
| 5 | `packages/core/content-type-builder/server/src/services/index.ts` | **Service Index** | Exports all services. No change needed — `content-types` is already registered. |
| 6 | `packages/core/content-type-builder/server/src/utils/index.ts` | **Utility** | Contains `getService<T>(name)` helper used by controllers to access services. Already supports `'content-types'`. |
| 7 | `packages/core/content-type-builder/server/src/controllers/schema.ts` | **Controller** | Reference pattern — shows a controller factory pattern (`export default () => ({...})`) with `getSchema`, `updateSchema`, `getUpdateSchemaStatus`. |
| 8 | `packages/core/content-type-builder/server/src/routes/content-api.ts` | **Route (Content API)** | Reference pattern — shows Zod-based route definitions with `createContentApiRoutesFactory`. |
| 9 | `packages/core/content-type-builder/server/src/middlewares/is-development-mode.ts` | **Middleware** | Reference — blocks mutations in production. The export endpoint (read-only) should NOT use this middleware. |
| 10 | `packages/core/content-type-builder/server/src/controllers/validation/content-type.ts` | **Validation** | Reference — shows Yup validation patterns (`validateYupSchema`, `validateKind`). |

### 4. DEPENDENCY GRAPH

**Module-level dependencies (content-type-builder server):**

```
server/src/index.ts
  ├── config.ts
  ├── bootstrap.ts
  ├── register.ts
  ├── services/index.ts
  │   ├── services/content-types.ts  ← imports utils/attributes, services/schema-builder, services/constants
  │   ├── services/components.ts
  │   ├── services/component-categories.ts
  │   ├── services/builder.ts
  │   ├── services/api-handler.ts
  │   └── services/schema.ts
  ├── controllers/index.ts
  │   ├── controllers/content-types.ts  ← imports utils (getService), validation/content-type, services/content-types
  │   ├── controllers/components.ts
  │   ├── controllers/component-categories.ts
  │   ├── controllers/builder.ts
  │   └── controllers/schema.ts
  ├── routes/index.ts
  │   ├── routes/admin.ts  ← imports middlewares/is-development-mode
  │   └── routes/content-api.ts  ← imports @strapi/utils (createContentApiRoutesFactory), zod
  └── middlewares/index.ts
      └── middlewares/is-development-mode.ts
```

**File-level dependencies for key files:**

- `controllers/content-types.ts` imports: `lodash`, `koa` (Context), `koa-body`, `@strapi/types`, `../utils` (getService), `./validation/content-type` (validateContentTypeInput, validateUpdateContentTypeInput, validateKind), `../services/content-types` (isContentTypeVisible)
- `services/content-types.ts` imports: `lodash`, `lodash/fp`, `@strapi/utils` (contentTypes, errors), `@strapi/types`, `../utils/attributes`, `./schema-builder`, `./constants`
- `routes/admin.ts` imports: `../middlewares` (isDevelopmentMode)

**Call graph for a typical GET request:**
```
Route (GET /content-types/:uid)
  → isDevelopmentMode middleware (only for POST/PUT/DELETE)
  → admin::hasPermissions policy
  → content-types.getContentType(ctx)
    → getService('content-types')
    → contentTypeService.formatContentType(contentType)
    → ctx.send({ data })
```

### 5. CONVENTIONS

**Naming Conventions:**
1. **Controllers** are exported as named objects with methods named as HTTP action verbs: `getContentTypes`, `getContentType`, `createContentType`, `updateContentType`, `deleteContentType`
2. **Services** export named functions: `formatContentType`, `createContentType`, `editContentType`, `deleteContentType`, `isContentTypeVisible`
3. **Route handlers** use dot notation: `'content-types.getContentType'` (controllerName.methodName)
4. **Route paths** use kebab-case: `/content-types`, `/content-types/:uid`, `/reserved-names`, `/component-categories/:name`
5. **Route files** export `{ type: 'admin', routes: [...] }` or use `createContentApiRoutesFactory`
6. **Controller files** export `default { methodName(ctx) {...} }` (object literal) or `export default () => ({ methodName(ctx) {...} })` (factory function)
7. **Service files** export named constants: `export const formatContentType = ...`
8. **Validation files** export `validateXxxInput` functions using `validateYupSchema`
9. **UID params** use `:uid` in route paths
10. **Response format** always wraps data: `ctx.send({ data: ... })` or `ctx.send({ error: ... }, statusCode)`

**Architectural Patterns:**
- **Service access:** `getService('content-types')` via `strapi.plugin('content-type-builder').service(name)`
- **Validation:** Yup schemas wrapped with `validateYupSchema(schema)(data)` — throws on error
- **Error handling:** try/catch in controllers, returning `ctx.send({ error: message }, 400)`
- **Response format:** `ctx.send({ data: ... })` for success, `ctx.send({ error: ... }, statusCode)` for errors
- **Policy pattern:** `{ name: 'admin::hasPermissions', config: { actions: ['plugin::content-type-builder.read'] } }`
- **Development-only mutations:** POST/PUT/DELETE routes use `middlewares: [isDevelopmentMode]`; GET routes do not

**Style Conventions:**
- Async/await for all controller methods that do I/O
- `ctx.send()` from Koa for responses (not `ctx.body =`)
- `ctx.params` for route parameters, `ctx.query` for query string, `ctx.request.body` for POST/PUT body
- `_.has(strapi.contentTypes, uid)` to check existence before operations
- `strapi.contentTypes[uid]` to access content type definitions
- `setImmediate(() => strapi.reload())` after mutations to trigger server restart

### 6. SIMILAR IMPLEMENTATIONS

| Class/Pattern | File | Why Similar |
|---------------|------|-------------|
| `getContentType` (controller) | `controllers/content-types.ts` | **Direct pattern to follow** — reads a single content type by UID, formats it, returns `{ data }`. The export endpoint will be similar but return JSON blob instead of formatted schema. |
| `getContentTypes` (controller) | `controllers/content-types.ts` | **Direct pattern to follow** — lists all content types with optional `kind` filter. The export endpoint could reuse this filtering logic. |
| `getSchema` (controller) | `controllers/schema.ts` | **Similar read-only GET pattern** — calls `getService('schema').getSchema()`, returns `{ data: schema }`. No `isDevelopmentMode` middleware. |
| `formatContentType` (service) | `services/content-types.ts` | **Core formatting logic** — transforms raw content type into the API response shape. The export service will build on this. |
| `getComponent` (controller) | `controllers/components.ts` | **Same pattern as getContentType** — reads by UID, checks existence, formats, returns. |

### 7. TASK CONTEXT

**Goal:** Add a new REST API endpoint `GET /content-types/:uid/export` that exports a single content type definition as a downloadable JSON file.

**What to build:**

1. **Service method** in `services/content-types.ts` — Add an `exportContentType(uid)` function that:
   - Takes a content type UID
   - Retrieves the content type schema from `strapi.contentTypes[uid]`
   - Uses `formatContentType()` to get the formatted schema
   - Returns the full content type definition as a JSON-serializable object (including all attributes, options, pluginOptions, etc.)

2. **Controller method** in `controllers/content-types.ts` — Add an `exportContentType(ctx)` method that:
   - Gets `uid` from `ctx.params`
   - Checks content type exists (`_.has(strapi.contentTypes, uid)`) — return 404 if not
   - Checks visibility (`isContentTypeVisible`) — return 404 if not visible
   - Calls `getService('content-types').exportContentType(uid)`
   - Sets response headers for JSON file download: `Content-Type: application/json`, `Content-Disposition: attachment; filename="<uid>.json"`
   - Returns the JSON data as the response body

3. **Route** in `routes/admin.ts` — Add a new route entry:
   - Method: `GET`
   - Path: `/content-types/:uid/export`
   - Handler: `'content-types.exportContentType'`
   - Config: policies `admin::hasPermissions` with action `plugin::content-type-builder.read`
   - **No** `isDevelopmentMode` middleware (this is a read-only operation)

**Patterns to follow:**
- Follow the exact same structure as `getContentType` controller method
- Use `ctx.send()` for response
- Use `getService('content-types')` to access the service
- Use `_.has(strapi.contentTypes, uid)` for existence check
- Use `isContentTypeVisible` for visibility check
- The route handler string format is `'content-types.exportContentType'` (controller name from `controllers/index.ts` + method name)

**What NOT to do:**
- Do NOT add `isDevelopmentMode` middleware (export is read-only)
- Do NOT modify `controllers/index.ts` or `services/index.ts` (content-types is already registered)
- Do NOT trigger `strapi.reload()` (no mutation occurs)
- Do NOT use Zod schemas for admin routes (only content-api routes use Zod)

### 8. RELEVANT CODE SNIPPETS

**Snippet 1 — Controller pattern (getContentType):**
```typescript
// packages/core/content-type-builder/server/src/controllers/content-types.ts (lines 63-79)
getContentType(ctx: Context) {
    const { uid } = ctx.params;

    const contentType = strapi.contentTypes[uid];

    if (!contentType) {
      return ctx.send({ error: 'contentType.notFound' }, 404);
    }

    if (!isContentTypeVisible(contentType)) {
      return ctx.send({ error: 'contentType.notFound' }, 404);
    }

    const contentTypeService = getService('content-types');

    ctx.send({ data: contentTypeService.formatContentType(contentType) });
  },
```

**Snippet 2 — Route definition pattern:**
```typescript
// packages/core/content-type-builder/server/src/routes/admin.ts (lines 32-44)
{
    method: 'GET',
    path: '/content-types/:uid',
    handler: 'content-types.getContentType',
    config: {
        policies: [
          {
            name: 'admin::hasPermissions',
            config: { actions: ['plugin::content-type-builder.read'] },
          },
        ],
    },
},
```

**Snippet 3 — Service formatContentType (the data shape to export):**
```typescript
// packages/core/content-type-builder/server/src/services/content-types.ts (lines 35-56)
export const formatContentType = (contentType: any) => {
  const { uid, kind, modelName, plugin, collectionName, info } = contentType;

  return {
    uid,
    plugin,
    apiID: modelName,
    schema: {
      ...contentTypesUtils.getOptions(contentType),
      displayName: info.displayName,
      singularName: info.singularName,
      pluralName: info.pluralName,
      description: _.get(info, 'description', ''),
      pluginOptions: contentType.pluginOptions,
      kind: kind || 'collectionType',
      collectionName,
      attributes: formatAttributes(contentType),
      visible: isContentTypeVisible(contentType),
      restrictRelationsTo: getRestrictRelationsTo(contentType),
    },
  };
};
```

**Snippet 4 — getService utility:**
```typescript
// packages/core/content-type-builder/server/src/utils/index.ts (lines 17-21)
export function getService<T extends keyof S>(
  name: T
): S[T] extends (...args: any[]) => any ? ReturnType<S[T]> : S[T] {
  return strapi.plugin('content-type-builder').service(name);
}
```

**Snippet 5 — Controller index (shows how handlers are referenced in routes):**
```typescript
// packages/core/content-type-builder/server/src/controllers/index.ts (lines 1-16)
import builder from './builder';
import componentCategories from './component-categories';
import components from './components';
import contentTypes from './content-types';
import schema from './schema';

const exportObject = {
  builder,
  'component-categories': componentCategories,
  components,
  'content-types': contentTypes,
  schema,
};

export default exportObject;
```