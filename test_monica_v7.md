I now have comprehensive data. Here is the architecture analysis.

---

## Monica Architecture Analysis

### 1. PROJECT SUMMARY

Monica is an open-source Personal Relationship Management (PRM) web application built with **Laravel 11 (PHP)** backend and **Vue 3 + Inertia.js** frontend. It has 2,091 files (1,656 PHP, 254 Vue, 40 JSON, 15 YAML), 1,409 classes, and 4,879 methods. It uses MySQL/PostgreSQL, supports CardDAV/CalDAV sync, and is licensed under AGPLv3.

### 2. ARCHITECTURE

**Type: Domain-Driven Modular Monolith with Clean Architecture layers**

The codebase is organized into **bounded contexts (Domains)** under `app/Domains/`, each containing a full vertical slice. The architecture has 5 distinct layers:

```
app/
  Domains/          -- Bounded contexts (Contact, Settings, Vault)
    {Domain}/
      Dav/          -- CardDAV/CalDAV integration (protocol layer)
      DavClient/    -- External DAV client sync
      Jobs/         -- Queue jobs
      Services/     -- Business logic (CRUD operations)
      Web/
        Controllers/ -- HTTP request handlers (Inertia)
        ViewHelpers/ -- Data transformers for Vue pages
  Http/
    Controllers/    -- Base controller + API controllers
    Middleware/      -- Auth, DAV, Inertia middleware
    Requests/       -- Form request validation
    Resources/      -- API resource transformers
  Models/           -- Eloquent models (Account, Contact, Vault, User, etc.)
  Services/         -- BaseService, QueuableService (abstract base classes)
  Interfaces/       -- ServiceInterface contract
  Actions/          -- Fortify/Jetstream auth actions
  Helpers/          -- Utility helpers (Date, Avatar, ContactCard, etc.)
  Providers/        -- Service providers
  Exceptions/       -- Custom exceptions
  Traits/           -- Shared traits (HasUuids, DAVFormat)
```

**Domain structure** (each is a bounded context):
- `app/Domains/Contact/` -- Contact management (sub-domains: ManageContact, ManageCalls, ManageNotes, ManageGoals, ManageRelationships, ManageReminders, ManageTasks, ManageGroups, ManageLifeEvents, ManageLoans, ManagePets, ManagePhotos, ManageDocuments, ManageLabels, ManageAvatar, ManagePronouns, ManageReligion, ManageJobInformation, ManageContactAddresses, ManageContactInformation, ManageContactImportantDates, ManageMoodTrackingEvents, ManageQuickFacts, ManageContactFeed, Dav, DavClient)
- `app/Domains/Settings/` -- Settings (sub-domains: ManageSettings, ManageUsers, ManageCurrencies, ManageTemplates, ManagePostTemplates, ManageAddressTypes, ManageCallReasons, ManageContactInformationTypes, ManageGiftStates, ManageRelationshipTypes, ManageGroupTypes, ManageLifeEventCategories, ManageMoodTracking, ManageGenders, ManagePronouns, ManageReligion, ManageGiftOccasions, ManageNotes, ManageReminders, ManageContactImportantDateTypes, ManageQuickFactsTemplate, ManageStorage, ManageUserPreferences, CancelAccount, CreateAccount)
- `app/Domains/Vault/` -- Vault management (sub-domains: ManageVault, ManageReports, ManageCalendar, ManageJournals, ManageCompanies, ManageTasks, ManageFiles, ManageSearch, ManageLifeMetrics)

**Dependency flow**: Controllers -> Services -> Models. Controllers never call Models directly — they always go through Services. ViewHelpers transform data for Inertia pages.

**Frontend**: Vue 3 SPA via Inertia.js (no API calls from frontend — all data flows through Inertia server-side rendering). Pages mirror the domain structure under `resources/js/Pages/`.

### 3. RELATED FILES (Key architectural files)

| File | Path | Entity Type | Role |
|------|------|-------------|------|
| BaseService | `app/Services/BaseService.php` | Service (abstract) | Base class for all domain services. Provides `rules()`, `permissions()`, `validateRules()`, and permission validation methods. |
| QueuableService | `app/Services/QueuableService.php` | Service (abstract) | Extends BaseService for queueable jobs. Has `handle()` that calls `execute()`. |
| ServiceInterface | `app/Interfaces/ServiceInterface.php` | Interface | Contract requiring `rules(): array` and `permissions(): array`. |
| Controller (base) | `app/Http/Controllers/Controller.php` | Controller (abstract) | Base controller using AuthorizesRequests, DispatchesJobs, ValidatesRequests. |
| ContactController | `app/Domains/Contact/ManageContact/Web/Controllers/ContactController.php` | Controller | Full CRUD for contacts. Calls Services, renders Inertia pages. |
| CreateContact | `app/Domains/Contact/ManageContact/Services/CreateContact.php` | Service | Example domain service: extends BaseService, implements ServiceInterface. |
| ContactIndexViewHelper | `app/Domains/Contact/ManageContact/Web/ViewHelpers/ContactIndexViewHelper.php` | ViewHelper (composable) | Transforms model data into arrays for Vue pages. |
| VaultIndexViewHelper | `app/Domains/Vault/ManageVault/Web/ViewHelpers/VaultIndexViewHelper.php` | ViewHelper (composable) | Provides layout data (navigation, permissions) for all vault pages. |
| Vault (model) | `app/Models/Vault.php` | Model | Eloquent model with relationships to contacts, users, labels, etc. |
| Contact (model) | `app/Models/Contact.php` | Model | Eloquent model with searchable trait, relationships to vault, gender, etc. |
| web.php (routes) | `routes/web.php` | Routes | 743 lines of route definitions mapping URLs to domain controllers. |
| app.js | `resources/js/app.js` | Vue entry | Inertia app setup with SSR, i18n, Ziggy routing. |

### 4. DEPENDENCY GRAPH

**Module-level dependencies** (top-level `app/` directories):

```
app/Domains/  (bounded contexts)
  depends on: app/Models, app/Services, app/Interfaces, app/Helpers

app/Http/Controllers/
  depends on: app/Domains/*/Web/Controllers (domain controllers extend base Controller)

app/Http/Middleware/
  depends on: app/Models, app/Domains

app/Services/
  BaseService depends on: app/Models (Account, Vault, Contact)
  QueuableService extends BaseService

app/Models/
  depends on: nothing (Laravel Eloquent base classes)

app/Providers/
  depends on: app/Models, app/Domains (event listeners)
```

**File-level dependency chain** (typical request flow):

```
Route (web.php)
  -> Domain Controller (extends Controller)
    -> Domain Service (extends BaseService, implements ServiceInterface)
      -> Eloquent Models
    -> ViewHelper (static data() methods)
      -> Inertia render (passes data to Vue page)
```

**Call graph** (CreateContact as example):
```
ContactController::store()
  -> (new CreateContact)->execute($data)
    -> CreateContact::validate()  [calls BaseService::validateRules(), BaseService::permissions()]
    -> CreateContact::createContact()  [calls Model::create()]
    -> CreateContact::updateLastEditedDate()  [calls Vault->save()]
    -> CreateContact::createFeedItem()  [calls ContactFeedItem::create()]
```

### 5. CONVENTIONS

**Naming conventions** (from sample_signatures):
1. **Services**: `{Action}{Entity}` — e.g. `CreateContact`, `DestroyContact`, `UpdateCall`, `RemovePronoun`. All extend `BaseService` and implement `ServiceInterface`.
2. **Controllers**: `{Entity}Controller` or `{Module}{Entity}Controller` — e.g. `ContactController`, `ContactModuleCallController`, `PreferencesController`. All extend `Controller`.
3. **ViewHelpers**: `{Entity}{View}ViewHelper` — e.g. `ContactIndexViewHelper`, `VaultIndexViewHelper`, `UserPreferencesIndexViewHelper`. All static methods returning arrays.
4. **Interfaces**: `I` prefix — e.g. `IDavResource`, `IDAVBackend`, `ServiceInterface`.
5. **Models**: Singular PascalCase — `Contact`, `Vault`, `Account`, `Address`, `Call`.
6. **Factories**: `{Model}Factory` — e.g. `ContactFactory`, `AccountFactory`.
7. **Tests**: `{Action}{Entity}Test` — e.g. `CreatePostTemplateSectionTest`, `UpdateGiftStateTest`. Extend `TestCase`.
8. **Jobs**: `{Action}{Entity}` — e.g. `DeleteVCard`, `CleanSyncToken`, `SetupAccount`. Implement `ShouldQueue`.
9. **Migrations**: snake_case timestamps — `2022_05_16_184121_create_call_reasons_table.php`.
10. **DTOs**: `{Entity}Dto` — e.g. `ContactDto`, `ContactDeleteDto`.

**Architectural patterns**:
- **Service pattern**: Every domain operation is a single-action Service class with `rules()`, `permissions()`, `execute(array $data)`. Services are NOT injected — they are instantiated with `new` and called directly.
- **Permission system**: Services declare `permissions()` returning an array of permission strings (e.g. `'author_must_belong_to_account'`, `'vault_must_belong_to_account'`, `'contact_must_belong_to_vault'`). `BaseService::validate()` iterates these and calls corresponding validation methods.
- **ViewHelper pattern**: Static classes that transform Eloquent models + request context into plain arrays for Inertia pages. No dependency injection.
- **Inertia.js**: Server-rendered Vue SPA. Controllers call `Inertia::render()` with data from ViewHelpers.
- **UUIDs**: All models use UUID primary keys via `HasUuids` trait.

**Style conventions**:
- All Services accept `array $data` and validate via `$this->validateRules($data)`.
- Controllers use Laravel's `authorize()` for gate checks, then call Services.
- `valueOrNull()`, `valueOrTrue()`, `valueOrFalse()` helpers in BaseService for optional fields.
- Feed items created after mutations for activity tracking.
- All dates handled via Carbon, stored in UTC.

### 6. SIMILAR IMPLEMENTATIONS

| Class | File | Why Similar |
|-------|------|-------------|
| `CreateContact` | `app/Domains/Contact/ManageContact/Services/CreateContact.php` | Extends BaseService, implements ServiceInterface. Pattern: rules() + permissions() + execute(). |
| `UpdateCall` | `app/Domains/Contact/ManageCalls/Services/UpdateCall.php` | Same pattern: BaseService + ServiceInterface. Same method signature (rules, permissions, execute). |
| `DestroyPostTemplate` | `app/Domains/Settings/ManagePostTemplates/Services/DestroyPostTemplate.php` | Same pattern: BaseService + ServiceInterface. Same three-method contract. |
| `RemovePronoun` | `app/Domains/Contact/ManagePronouns/Services/RemovePronoun.php` | Same pattern: BaseService + ServiceInterface. |
| `CreateModule` | `app/Domains/Settings/ManageTemplates/Services/CreateModule.php` | Same pattern: BaseService + ServiceInterface. |
| `SetupAccount` | `app/Domains/Settings/CreateAccount/Jobs/SetupAccount.php` | Extends QueuableService (which extends BaseService). Queueable variant of the same pattern. |

### 7. TASK CONTEXT

Monica is a **Domain-Driven Modular Monolith** with a strict **Service-per-operation** pattern. Every business operation (CreateContact, UpdateCall, DestroyPostTemplate) is a single class extending `BaseService` and implementing `ServiceInterface`. The three required methods are: `rules()` (validation rules array), `permissions()` (permission checks array), and `execute(array $data)` (the operation).

The frontend is **Vue 3 + Inertia.js** — no REST API calls from the frontend. Controllers render Inertia pages with data prepared by **ViewHelpers** (static classes that transform models into arrays). Routes are defined in `routes/web.php` and map to domain controllers under `app/Domains/{Domain}/Manage{SubDomain}/Web/Controllers/`.

Key architectural rules:
- Controllers never call Models directly — always through Services.
- Services are instantiated with `new`, not injected.
- ViewHelpers are static classes, not instantiated.
- All models use UUID primary keys.
- Permission validation is declarative via the `permissions()` array.
- Activity feed items are created after mutations.
- The `app/Domains/` directory contains all business logic organized by bounded context (Contact, Settings, Vault).

### 8. RELEVANT CODE SNIPPETS

**Snippet 1: ServiceInterface contract** (`app/Interfaces/ServiceInterface.php`, lines 5-16)
```php
interface ServiceInterface
{
    public function rules(): array;
    public function permissions(): array;
}
```
This is the core contract every domain service must implement. It enforces the two-declaration pattern (rules + permissions) that drives the entire service layer.

**Snippet 2: BaseService validation flow** (`app/Services/BaseService.php`, signatures)
```php
public function validateRules(array $data)  // calls $this->rules() then Validator::make()
public function validate()  // calls validateRules() then iterates $this->permissions()
```
Every service calls `$this->validate()` at the start of `execute()`. The permissions array drives automatic validation of account membership, vault membership, contact ownership, and permission levels.

**Snippet 3: Typical Service pattern** (`app/Domains/Contact/ManageContact/Services/CreateContact.php`, signatures)
```php
public function rules(): array  // returns validation rules array
public function permissions(): array  // returns ['author_must_belong_to_account', ...]
public function execute(array $data): Contact  // calls validate(), then business logic
```
Every service follows this exact three-method pattern. The `execute()` method always calls `$this->validate()` first, then performs the operation, then returns the result.

**Snippet 4: Controller calling a Service** (`app/Domains/Contact/ManageContact/Web/Controllers/ContactController.php`, store method)
```php
public function store(Request $request, string $vaultId)
{
    $contact = (new CreateContact())->execute([
        'account_id' => Auth::user()->account_id,
        'author_id' => Auth::user()->id,
        'vault_id' => $vaultId,
        'first_name' => $request->input('first_name'),
        // ...
    ]);
    return response()->json(['data' => route('contact.show', ['vault' => $vaultId, 'contact' => $contact])]);
}
```
Controllers instantiate Services with `new` and call `execute()` with a flat data array. No dependency injection for services.

**Snippet 5: ViewHelper data transformation** (`app/Domains/Contact/ManageContact/Web/ViewHelpers/ContactIndexViewHelper.php`, signatures)
```php
public static function data($contacts, Vault $vault, ?int $labelId, User $user): array
{
    return collect($contacts)->map(fn ($contact) => [
        'id' => $contact->id,
        'name' => $contact->name,
        'avatar' => $contact->avatar,
        'url' => ['show' => route('contact.show', ['vault' => $vault->id, 'contact' => $contact->id])],
    ])->toArray();
}
```
ViewHelpers are static classes that transform Eloquent models into plain arrays for Inertia pages. They use `route()` for URL generation and `trans()` for localization.