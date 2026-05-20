I now have a comprehensive understanding of the architecture. Here is the analysis:

---

## Architecture Analysis: Monica PRM

### 1. PROJECT SUMMARY

**Monica** is an open-source Personal Relationship Management (PRM) web application built with **Laravel 11** (PHP) backend and **Vue 3 + Inertia.js** frontend. It has 2,091 files (1,656 PHP, 254 Vue, 40 JSON, 15 YAML), 1,409 classes, and 4,879 methods. It uses MySQL/PostgreSQL, Redis, Laravel Scout (Meilisearch/Algolia), and supports CardDAV/CalDAV sync.

### 2. ARCHITECTURE

**Type: Domain-Driven Modular Monolith with Clean Architecture layers**

The project is organized into **bounded contexts** (Domains) with strict internal layering. Each domain is self-contained with its own Services, Controllers, ViewHelpers, and (optionally) DAV/DavClient sub-modules.

#### Top-Level Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    Vue SPA (Inertia.js)                      │
│  resources/js/Pages/  resources/js/Components/              │
│  resources/js/Layouts/  resources/js/Shared/                │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP (Inertia)
┌──────────────────────▼──────────────────────────────────────┐
│  routes/web.php  routes/api.php                             │
│  app/Http/Middleware/  app/Http/Controllers/Controller.php  │
│  app/Policies/  app/Exceptions/                             │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Contact      │  │ Vault        │  │ Settings     │      │
│  │ Domain       │  │ Domain       │  │ Domain       │      │
│  │              │  │              │  │              │      │
│  │ ManageAvatar │  │ ManageVault  │  │ ManageUsers  │      │
│  │ ManageCalls  │  │ ManageJournls│  │ ManageGenders│      │
│  │ ManageTasks  │  │ ManageFiles  │  │ ManageTemplts│      │
│  │ ManageNotes  │  │ ManageCalendr│  │ ManageCurrncy│      │
│  │ ... (20+)    │  │ ... (15+)    │  │ ... (25+)    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
├─────────────────────────────────────────────────────────────┤
│  app/Models/  (69 Eloquent models)                          │
│  app/Services/BaseService.php  QueuableService.php          │
│  app/Interfaces/ServiceInterface.php                        │
│  app/Helpers/  app/Traits/  app/Logging/                    │
├─────────────────────────────────────────────────────────────┤
│  database/migrations/  database/factories/  database/seeders│
│  config/  lang/  storage/                                   │
└─────────────────────────────────────────────────────────────┘
```

#### Domain Internal Structure (each Manage* module)

Every `Manage*` module follows a consistent 3-layer pattern:

```
ManageXxx/
├── Services/          # Business logic (extends BaseService, implements ServiceInterface)
│   ├── CreateXxx.php
│   ├── UpdateXxx.php
│   ├── DestroyXxx.php
│   └── ...
├── Web/
│   ├── Controllers/   # HTTP handlers (extends Controller)
│   ├── ViewHelpers/   # Data transformers (static methods, no base class)
│   └── (optional) Api/Controllers/
├── Dav/               # CardDAV/CalDAV export/import (optional)
├── DavClient/         # Remote DAV sync (optional)
└── Jobs/              # Queueable jobs (optional)
```

#### Dependency Flow

```
Browser ──HTTP──> routes/web.php ──> Controller ──> Service ──> Model ──> DB
                          │              │              │
                          │              ├──> ViewHelper (transforms data for Vue)
                          │              └──> Inertia render (sends to Vue SPA)
                          │
                          └──> Middleware (auth, locale, Inertia)
```

**Key rules:**
- **Controllers never contain business logic** — they validate HTTP input, call a Service, then render via Inertia
- **Services contain all business logic** — they extend `BaseService` which provides permission validation (author belongs to account, vault exists, user has vault permission level, contact belongs to vault)
- **ViewHelpers are static data transformers** — they take models and return arrays for Vue components
- **Domains never depend on each other** — Contact domain does not import Vault domain services
- **Cross-domain data** flows through shared Models (e.g., `Contact` belongs to `Vault` via Eloquent relationships)

#### Permission System

`BaseService` provides a declarative permission system via `permissions()` method returning an array of permission checks:
- `author_must_belong_to_account`
- `author_must_be_account_administrator`
- `vault_must_belong_to_account`
- `user_must_be_in_vault` (with levels: `PERMISSION_VIEW`, `PERMISSION_EDIT`, `PERMISSION_MANAGE`)
- `contact_must_belong_to_vault`
- `group_must_belong_to_vault`

#### Frontend Architecture

Vue SPA using Inertia.js (no API calls from frontend — all data is pre-rendered server-side and sent as props). Pages mirror the domain structure:
```
resources/js/Pages/
├── Vault/
│   ├── Index.vue
│   ├── Create.vue
│   ├── Edit.vue
│   ├── Dashboard/Index.vue
│   └── Contact/Index.vue, Show.vue, Create.vue, ...
├── Settings/
│   ├── Index.vue
│   ├── Personalize/...
│   └── Preferences/...
└── Auth/...
```

### 3. RELATED FILES (Key Architectural Files)

| File | Purpose | Role |
|------|---------|------|
| `app/Services/BaseService.php` | Abstract base for all services — provides validation, permission checking, and data access | **Core framework** |
| `app/Interfaces/ServiceInterface.php` | Interface requiring `rules()` and `permissions()` methods | **Contract** |
| `app/Services/QueuableService.php` | Extends BaseService for queueable jobs (implements `ShouldQueue`) | **Async pattern** |
| `app/Http/Controllers/Controller.php` | Base controller with AuthorizesRequests, DispatchesJobs, ValidatesRequests | **Base layer** |
| `app/Domains/Contact/ManageContact/Services/CreateContact.php` | Example service: creates a contact with full permission validation | **Domain service** |
| `app/Domains/Vault/ManageVault/Web/Controllers/VaultController.php` | Example controller: CRUD for vaults, uses Inertia rendering | **Web controller** |
| `app/Domains/Vault/ManageVault/Web/ViewHelpers/VaultIndexViewHelper.php` | Example ViewHelper: transforms vault data for Vue | **Data transformer** |
| `app/Models/Vault.php` | Core model with permission relationships | **Model** |
| `app/Policies/VaultPolicy.php` | Authorization policy for vault access | **Policy** |
| `bootstrap/app.php` | Application configuration (middleware, routing, exceptions) | **Config** |
| `routes/web.php` | All web routes (743 lines) | **Routing** |
| `resources/js/Layouts/AppLayout.vue` | Main Vue layout component | **Frontend shell** |

### 4. DEPENDENCY GRAPH

**Module-level dependencies** (top-level `app/` directories):

```
app/Domains/*  ───>  app/Models/*  ───>  (Laravel Eloquent)
       │
       ├──>  app/Services/BaseService.php
       ├──>  app/Interfaces/ServiceInterface.php
       └──>  app/Exceptions/* (NotEnoughPermissionException, etc.)

app/Http/Controllers/Controller.php  ───>  Laravel base controller
       │
       └──>  app/Domains/*/Web/Controllers/*  (domain controllers extend this)

app/Providers/*  ───>  config/*  ───>  Laravel service container
```

**File-level dependency example** (CreateContact service):

```
CreateContact.php
  extends BaseService
  implements ServiceInterface
  uses: Contact model, Vault model, User model
  called by: ContactController@store
```

**Call graph** (typical request flow):

```
Request ──> ContactController@store
  ──> authorize('vault-editor', $vault)     [Policy check]
  ──> (new CreateContact)->execute($data)   [Service call]
       ──> $this->validateRules($data)      [BaseService validation]
       ──> $this->validatePermissions()     [BaseService permission checks]
       ──> Contact::create(...)             [Model persistence]
       ──> updateLastEditedDate()           [Side effect]
  ──> return Inertia response               [Vue rendering]
```

### 5. CONVENTIONS

**Naming conventions** (from sample_signatures):
1. **Services**: `{Action}{Entity}` — `CreateContact`, `UpdateCall`, `DestroyGiftState`, `ToggleCurrency`, `RescheduleContactReminderForChannel`
2. **Controllers**: `{Entity}Controller` — `VaultController`, `ContactController`, `LoginController`, `ContactModuleCallController`
3. **ViewHelpers**: `{View}ViewHelper` — `VaultIndexViewHelper`, `ContactShowViewHelper`, `PersonalizeIndexViewHelper`
4. **Interfaces**: Prefix `I` — `IDavResource`, `IDAVBackend`, `ICalDAVBackend`, `ServiceInterface`
5. **Tests**: `{ServiceName}Test` — `CreateContactTaskTest`, `DestroyUserTest`, `ToggleCurrencyTest`
6. **Factories**: `{Model}Factory` — `JournalFactory`, `VaultQuickFactsTemplateFactory`, `AccountFactory`
7. **Exceptions**: `{Description}Exception` — `NotEnoughPermissionException`, `MaximumNumberOfUsersInVaultException`
8. **Traits**: PascalCase — `HasUuids`, `DAVFormat`, `JsonRespondController`
9. **DTOs**: `{Entity}Dto` — `ContactDto`, `ContactDeleteDto`
10. **Jobs**: `{Action}{Entity}` — `UpdateVCard`, `SynchronizeAddressBooks`, `PushVCard`

**Architectural patterns**:
- **Service Layer pattern**: All business logic in Services extending `BaseService` implementing `ServiceInterface`
- **Repository pattern**: Not used — Eloquent models are queried directly in Services
- **CQRS-lite**: Separate Create/Update/Destroy services per entity (no queries in services — queries are in ViewHelpers)
- **Inertia.js**: Server-rendered Vue SPA — no client-side API calls
- **Static ViewHelpers**: Data transformation via static methods, no dependency injection
- **Declarative permissions**: `permissions()` method returns array of permission strings validated by `BaseService`

**Style conventions**:
- All services have `rules()`, `permissions()`, and `execute(array $data)` methods
- Controllers use `authorize()` for policy checks before calling services
- ViewHelpers use `public static function data(...)` and `public static function layoutData(...)`
- All HTTP responses use Inertia (`inertia()->render()`) or JSON for AJAX
- Validation uses Laravel Validator inside `BaseService::validateRules()`

### 6. SIMILAR IMPLEMENTATIONS

| Class | File | Why Similar |
|-------|------|-------------|
| `CreateContact` | `app/Domains/Contact/ManageContact/Services/CreateContact.php` | Same pattern as all Create* services: extends BaseService, implements ServiceInterface, has rules()+permissions()+execute() |
| `UpdateCall` | `app/Domains/Contact/ManageCalls/Services/UpdateCall.php` | Same pattern as all Update* services |
| `DestroyGiftState` | `app/Domains/Settings/ManageGiftStates/Services/DestroyGiftState.php` | Same pattern as all Destroy* services |
| `ToggleCurrency` | `app/Domains/Settings/ManageCurrencies/Services/ToggleCurrency.php` | Same pattern as all Toggle* services |
| `VaultController` | `app/Domains/Vault/ManageVault/Web/Controllers/VaultController.php` | Same pattern as all domain controllers: extends Controller, uses Inertia render |
| `VaultIndexViewHelper` | `app/Domains/Vault/ManageVault/Web/ViewHelpers/VaultIndexViewHelper.php` | Same pattern as all ViewHelpers: static methods returning arrays |
| `ExportKind` | `app/Domains/Contact/ManageGroups/Dav/ExportKind.php` | Same pattern as all DAV exporters: extends Exporter, implements ExportVCardResource |

### 7. TASK CONTEXT

**Monica** is a Laravel 11 + Vue 3/Inertia.js PRM application organized as a **Domain-Driven Modular Monolith**. The key architectural insight is that every feature follows the same rigid pattern:

1. **Route** → **Controller** → **Service** → **Model** (with ViewHelper for data transformation)
2. Each domain (`Contact`, `Vault`, `Settings`) contains multiple `Manage*` modules
3. Each `Manage*` module has `Services/`, `Web/Controllers/`, and `Web/ViewHelpers/` subdirectories
4. All services extend `BaseService` which provides automatic validation and permission checking
5. All controllers extend `App\Http\Controllers\Controller` (which extends Laravel's base)
6. ViewHelpers are static classes that transform Eloquent models into arrays for Vue
7. The frontend is an Inertia.js SPA — pages receive pre-rendered data as props, no API calls
8. Permission levels: `view` (read-only), `edit` (can modify), `manage` (can administer vault)
9. DAV support (CardDAV/CalDAV) is embedded in the Contact domain for contact/calendar sync
10. Tests mirror the domain structure in `tests/Unit/Domains/` and `tests/Feature/`

When adding new features, follow the existing pattern: create a `ManageXxx` module under the appropriate domain with `Services/CreateXxx.php`, `Services/UpdateXxx.php`, `Services/DestroyXxx.php`, `Web/Controllers/XxxController.php`, and `Web/ViewHelpers/XxxViewHelper.php`.

### 8. RELEVANT CODE SNIPPETS

**Snippet 1: BaseService permission validation pattern** (`app/Services/BaseService.php`, lines 14-30)
```php
abstract class BaseService
{
    public User $author;
    public Vault $vault;
    public ?Contact $contact = null;

    abstract public function rules(): array;
    abstract public function permissions(): array;
    abstract public function execute(array $data);
}
```
*Why: Shows the base class that all services extend — the core of the architecture.*

**Snippet 2: Service permission declaration** (`app/Domains/Contact/ManageTasks/Services/CreateContactTask.php`)
```php
public function permissions(): array
{
    return [
        'author_must_belong_to_account',
        'vault_must_belong_to_account',
        'contact_must_belong_to_vault',
        'user_must_be_in_vault' => Vault::PERMISSION_EDIT,
    ];
}
```
*Why: Shows the declarative permission system — every service declares what permissions it needs.*

**Snippet 3: Controller calling a service** (`app/Domains/Vault/ManageVault/Web/Controllers/VaultController.php`, lines ~50-65)
```php
public function store(Request $request)
{
    $data = [
        'account_id' => Auth::user()->account_id,
        'author_id' => Auth::user()->id,
        'name' => $request->input('name'),
        'description' => $request->input('description'),
    ];
    $vault = (new CreateVault)->execute($data);
    return response()->json(['data' => route('vault.show', ['vault' => $vault])]);
}
```
*Why: Shows the thin controller pattern — validate input, call service, return response.*

**Snippet 4: ViewHelper data transformation** (`app/Domains/Vault/ManageVault/Web/ViewHelpers/VaultIndexViewHelper.php`)
```php
public static function data(User $user): array
{
    $vaults = $user->vaults()
        ->where('account_id', $user->account_id)
        ->with('contacts')
        ->get()
        ->sortByCollator('name');

    return [
        'vaults' => $vaults->map(fn (Vault $vault) => [
            'id' => $vault->id,
            'name' => $vault->name,
            'url' => route('vault.show', ['vault' => $vault]),
            'contacts_count' => $vault->contacts->count(),
        ]),
    ];
}
```
*Why: Shows the ViewHelper pattern — static methods that transform models into arrays for Vue.*

**Snippet 5: Inertia rendering in controller** (`app/Domains/Vault/ManageVault/Web/Controllers/VaultController.php`)
```php
public function show(Request $request, Vault $vault)
{
    return inertia()->render('Vault/Dashboard/Index', [
        'layoutData' => VaultIndexViewHelper::layoutData($vault),
        'data' => VaultDashboardViewHelper::data($vault, Auth::user()),
    ]);
}
```
*Why: Shows how controllers pass data to Vue via Inertia — layoutData for navigation, data for page content.*