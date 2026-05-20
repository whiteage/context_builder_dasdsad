Now I have a comprehensive understanding of the contact management architecture. Let me compile the full context document.

---

## Project Summary

**Monica** is an open-source personal CRM (Customer Relationship Management) built with **Laravel** (PHP) and **Inertia.js** (Vue.js frontend). It helps users manage their personal relationships, contacts, and social interactions.

- **Tech Stack**: PHP 8.x (Laravel), Vue.js 3 (Inertia.js), MySQL/PostgreSQL, Laravel Scout (search), Laravel Jetstream (auth), CardDAV/CalDAV support
- **Scale**: 2,093 total files, 1,656 PHP files, 254 Vue files, 161 controllers, 534 services
- **Architecture**: Domain-Driven Design (DDD) with a modular structure under `app/Domains/`

---

## Architecture

### Architecture Type: **Domain-Driven Modular Monolith with Service Layer Pattern**

The application follows a **Domain-Driven Design** approach organized into bounded contexts (Domains). Each domain is self-contained with its own controllers, services, models, and view helpers.

### Layers (from top to bottom):

| Layer | Directory Pattern | Responsibility |
|---|---|---|
| **Routes** | `routes/web.php` | HTTP route definitions, middleware, authorization gates |
| **Controllers** | `app/Domains/{Domain}/Manage{Feature}/Web/Controllers/` | HTTP request handling, Inertia rendering, JSON responses |
| **ViewHelpers** | `app/Domains/{Domain}/Manage{Feature}/Web/ViewHelpers/` | Data transformation for Inertia/Vue frontend |
| **Services** | `app/Domains/{Domain}/Manage{Feature}/Services/` | Business logic, validation, persistence (CRUD operations) |
| **Models** | `app/Models/` | Eloquent models, relationships, scopes |
| **Base Infrastructure** | `app/Services/BaseService.php`, `app/Http/Controllers/Controller.php` | Shared base classes, permission system, validation |

### Key Domain: Contact

The Contact domain is at `app/Domains/Contact/` and is further subdivided into sub-domains (ManageContact, ManageNotes, ManageCalls, ManageGoals, etc.). Each sub-domain follows the same structure:

```
Manage{Feature}/
├── Services/
│   ├── Create{Entity}.php
│   ├── Update{Entity}.php
│   └── Destroy{Entity}.php
├── Web/
│   ├── Controllers/
│   │   └── {Feature}Controller.php
│   └── ViewHelpers/
│       └── {Feature}ViewHelper.php
```

---

## Key Files

### 1. `app/Domains/Contact/ManageContact/Web/Controllers/ContactController.php`
**Purpose**: Main contact CRUD controller — handles listing, creating, viewing, editing, updating, and deleting contacts.
**Relevance**: Central controller for contact management. Uses the Service pattern for all mutations.

### 2. `app/Domains/Contact/ManageContact/Services/CreateContact.php`
**Purpose**: Service class for creating a new contact. Validates input, creates the Contact model, updates timestamps, and creates a feed item.
**Relevance**: Primary example of the Service pattern — extends `BaseService`, implements `ServiceInterface`.

### 3. `app/Domains/Contact/ManageContact/Services/UpdateContact.php`
**Purpose**: Service class for updating an existing contact. Validates, updates fields, saves, and creates feed item.
**Relevance**: Shows the update pattern with permission validation (`contact_must_belong_to_vault`).

### 4. `app/Domains/Contact/ManageContact/Services/DestroyContact.php`
**Purpose**: Service class for deleting a contact. Checks `can_be_deleted`, destroys associated files, then deletes.
**Relevance**: Shows the destroy pattern with pre-deletion checks.

### 5. `app/Services/BaseService.php`
**Purpose**: Abstract base class for all services. Provides validation, permission checking, and helper methods (`valueOrNull`, `valueOrTrue`, `valueOrFalse`).
**Relevance**: Foundation of the entire service layer — all services extend this.

### 6. `app/Services/QueuableService.php`
**Purpose**: Extends `BaseService` to make services queueable (async jobs). Implements `ShouldQueue`.
**Relevance**: Used for services that need async execution (e.g., `DestroyContact` via `dispatchSync`).

### 7. `app/Models/Contact.php`
**Purpose**: Eloquent model for contacts. Extends `VCardResource`, uses `HasUuids`, `Searchable`, `SoftDeletes`.
**Relevance**: Core data model with relationships to vault, gender, pronoun, template, notes, calls, goals, etc.

### 8. `app/Domains/Contact/ManageContact/Web/ViewHelpers/ContactShowViewHelper.php`
**Purpose**: Transforms contact data for the show page view. Builds template pages, modules, and contact information sections.
**Relevance**: Shows the ViewHelper pattern — static `data()` methods that return arrays for Inertia.

### 9. `app/Domains/Contact/ManageContact/Web/ViewHelpers/ContactIndexViewHelper.php`
**Purpose**: Transforms contact list data for the index page. Handles labels, sorting options, and contact cards.
**Relevance**: Shows how list data is prepared for the frontend.

### 10. `routes/web.php`
**Purpose**: All web routes including contact routes (lines 239-393).
**Relevance**: Shows the routing structure — vault-scoped, with middleware gates like `can:contact-owner,vault,contact`.

---

## Key Symbols

### Classes

| Class | File | Base/Interface | Purpose |
|---|---|---|---|
| `ContactController` | `app/Domains/Contact/ManageContact/Web/Controllers/ContactController.php` | extends `App\Http\Controllers\Controller` | CRUD for contacts |
| `CreateContact` | `app/Domains/Contact/ManageContact/Services/CreateContact.php` | extends `BaseService`, implements `ServiceInterface` | Create contact business logic |
| `UpdateContact` | `app/Domains/Contact/ManageContact/Services/UpdateContact.php` | extends `BaseService`, implements `ServiceInterface` | Update contact business logic |
| `DestroyContact` | `app/Domains/Contact/ManageContact/Services/DestroyContact.php` | extends `BaseService`, implements `ServiceInterface` | Delete contact business logic |
| `BaseService` | `app/Services/BaseService.php` | abstract class | Permission system, validation, helpers |
| `QueuableService` | `app/Services/QueuableService.php` | extends `BaseService`, implements `ShouldQueue` | Async service execution |
| `ServiceInterface` | `app/Interfaces/ServiceInterface.php` | interface | Contract: `rules()`, `permissions()` |
| `Contact` | `app/Models/Contact.php` | extends `VCardResource` | Eloquent model |
| `Vault` | `app/Models/Vault.php` | Eloquent model | Vault (container for contacts) |
| `Controller` (base) | `app/Http/Controllers/Controller.php` | extends `Illuminate\Routing\Controller` | Base controller with traits |

### Key Methods

**`BaseService::validateRules(array $data): bool`** — Validates input data against `$this->rules()` and checks all declared permissions with their dependencies.

**`BaseService::valueOrNull($data, $index)`** — Returns `null` if the index is empty in the data array, otherwise returns the value.

**`CreateContact::execute(array $data): Contact`** — Orchestrates validation, creation, timestamp update, and feed item creation.

**`ContactController::store(Request $request, string $vaultId)`** — Builds data array from request, calls `(new CreateContact)->execute($data)`, returns JSON with redirect URL.

---

## Dependencies

### Module-Level Dependencies

The project uses a **Domain-Driven** structure where each domain is self-contained:

```
app/Domains/Contact/  ← Contact domain (controllers, services, models)
app/Domains/Vault/    ← Vault domain (vault management, search)
app/Domains/Settings/ ← Settings domain
app/Services/         ← BaseService, QueuableService (shared infrastructure)
app/Models/           ← All Eloquent models
app/Http/Controllers/ ← Base Controller
```

### File-Level Dependencies

**ContactController** depends on:
- `CreateContact`, `UpdateContact`, `DestroyContact`, `UpdateContactView` (services)
- `ContactIndexViewHelper`, `ContactCreateViewHelper`, `ContactEditViewHelper`, `ContactShowViewHelper` (view helpers)
- `VaultIndexViewHelper` (from Vault domain)
- `Contact`, `User`, `Vault` (models)
- `Illuminate\Http\Request`, `Illuminate\Support\Facades\Auth`, `Inertia\Inertia`

**CreateContact** depends on:
- `BaseService` (parent)
- `ServiceInterface` (interface)
- `Contact`, `ContactFeedItem` (models)
- `Carbon\Carbon`

**BaseService** depends on:
- `Account`, `Contact`, `Group`, `User`, `Vault` (models)
- `NotEnoughPermissionException`
- `Illuminate\Support\Facades\Validator`

### Call Graph (Contact Creation Flow)

```
ContactController::store()
  → Gate::authorize('vault-editor')
  → (new CreateContact)->execute($data)
      → $this->validateRules($data)          [BaseService]
          → Validator::make()->validate()
          → $this->validatePermission()       [checks permissions]
      → $this->createContact()               [Contact::create()]
      → $this->updateLastEditedDate()        [saves timestamp]
      → $this->createFeedItem()              [ContactFeedItem::create()]
  → response()->json([...], 201)
```

---

## Conventions

### Naming Conventions

1. **PascalCase** for all classes: `CreateContact`, `ContactController`, `ContactShowViewHelper`
2. **camelCase** for methods: `execute()`, `validateRules()`, `valueOrNull()`
3. **snake_case** for database columns and array keys: `account_id`, `vault_id`, `first_name`, `last_updated_at`
4. **Interface prefix `I`**: `ServiceInterface` (though only one interface exists)
5. **Suffix conventions**:
   - `Controller` — HTTP controllers: `ContactController`, `ContactArchiveController`, `ContactFavoriteController`
   - `Service` — Business logic services: `CreateContact`, `UpdateContact`, `DestroyContact` (note: no "Service" suffix in the class name itself, but they live in a `Services/` directory)
   - `ViewHelper` — Data transformers for views: `ContactIndexViewHelper`, `ContactShowViewHelper`
   - `Controller` suffix for all HTTP controllers
6. **Directory naming**: `Manage{Feature}` for feature modules, `Web/Controllers/` and `Web/ViewHelpers/` for web layer

### Architectural Patterns

1. **Service Layer Pattern**: All business logic lives in Service classes that extend `BaseService` and implement `ServiceInterface`. Controllers are thin — they only extract request data, call services, and return responses.

2. **Permission System**: Each service declares a `permissions()` array with string identifiers like `'author_must_belong_to_account'`, `'vault_must_belong_to_account'`, `'author_must_be_vault_editor'`, `'contact_must_belong_to_vault'`. `BaseService::validateRules()` resolves these into actual validation checks.

3. **Validation Rules**: Each service declares a `rules()` method returning a Laravel validation array. All services require `account_id`, `vault_id`, `author_id` as UUIDs.

4. **CRUD per Feature**: Each feature (e.g., ManageContact, ManageNotes) has separate `Create`, `Update`, `Destroy` service classes. Read operations are handled directly in controllers or ViewHelpers.

5. **Inertia.js**: Controllers return `Inertia::render()` for pages and `response()->json()` for AJAX mutations. ViewHelpers prepare data arrays for the Vue frontend.

6. **Queuable Services**: `DestroyContact` uses `dispatchSync()` (via `QueuableService`), while `CreateContact` and `UpdateContact` are called synchronously with `(new Service)->execute()`.

### Style Conventions

1. **Async usage**: Services are synchronous by default. `QueuableService` extends `BaseService` with `ShouldQueue` for async jobs. `DestroyContact` uses `dispatchSync()` (synchronous dispatch).

2. **Error handling**: Services throw `ModelNotFoundException` for missing entities, `NotEnoughPermissionException` for permission failures, and generic `\Exception` for validation issues.

3. **Validation style**: Laravel Validator with `$this->rules()` arrays. Additional entity existence checks in private `validate()` methods.

4. **Data helpers**: `BaseService` provides `valueOrNull()`, `valueOrTrue()`, `valueOrFalse()` for safe array access with null defaults.

5. **Feed items**: Most mutating services create a `ContactFeedItem` to track activity on the contact.

6. **Timestamps**: Services manually update `last_updated_at` via `Carbon::now()` rather than relying on Eloquent's `$timestamps`.

---

## Similar Implementations

Since `find_similar` returned no results (likely due to AST parsing limitations), here are the patterns observed across the codebase:

### Pattern: CRUD Service Classes

Every feature module follows the same pattern with `Create{Entity}`, `Update{Entity}`, `Destroy{Entity}` services. Examples:

| Service | File | Similarity |
|---|---|---|
| `CreateContact` | `app/Domains/Contact/ManageContact/Services/CreateContact.php` | Canonical example |
| `UpdateContact` | `app/Domains/Contact/ManageContact/Services/UpdateContact.php` | Same pattern, adds `contact_must_belong_to_vault` permission |
| `DestroyContact` | `app/Domains/Contact/ManageContact/Services/DestroyContact.php` | Same pattern, uses `QueuableService` via `dispatchSync` |
| `ToggleArchiveContact` | `app/Domains/Contact/ManageContact/Services/ToggleArchiveContact.php` | Same pattern, toggles boolean |
| `ToggleFavoriteContact` | `app/Domains/Contact/ManageContact/Services/ToggleFavoriteContact.php` | Same pattern, toggles via pivot table |
| `CopyContactToAnotherVault` | `app/Domains/Contact/ManageContact/Services/CopyContactToAnotherVault.php` | Same pattern, cross-vault operation |
| `MoveContactToAnotherVault` | `app/Domains/Contact/ManageContact/Services/MoveContactToAnotherVault.php` | Same pattern, moves between vaults |

### Pattern: Controller → Service → Response

All controllers follow the same flow:
1. Extract data from `$request`
2. Call `(new ServiceClass)->execute($data)` or `ServiceClass::dispatchSync($data)`
3. Return `Inertia::render()` or `response()->json()`

---

## Context for the Task

### Summary for AI

The contact management system in Monica follows a **Domain-Driven Design** with a strict **Service Layer** pattern. The core contact CRUD is in `app/Domains/Contact/ManageContact/` with:

- **Controllers** (`Web/Controllers/`): Thin HTTP handlers that extract request data, call services, and return Inertia/JSON responses
- **Services** (`Services/`): Business logic classes extending `BaseService` with `rules()`, `permissions()`, and `execute()` methods
- **ViewHelpers** (`Web/ViewHelpers/`): Static classes with `data()` methods that transform models into arrays for the Vue frontend

All services share a common permission system in `BaseService::validateRules()` that checks:
1. Author belongs to the account
2. Vault belongs to the account
3. Contact belongs to the vault (if applicable)
4. User has the required vault permission level (viewer, editor, manager)

### Key Code Snippets

**1. Service Pattern (CreateContact)** — Every service follows this structure:
```php
class CreateContact extends BaseService implements ServiceInterface
{
    public function rules(): array { /* Laravel validation rules */ }
    public function permissions(): array { /* e.g. 'author_must_be_vault_editor' */ }
    public function execute(array $data): Contact
    {
        $this->data = $data;
        $this->validate();
        $this->createContact();
        $this->updateLastEditedDate();
        $this->createFeedItem();
        return $this->contact;
    }
}
```

**2. Controller Pattern** — Controllers are thin wrappers:
```php
public function store(Request $request, string $vaultId)
{
    Gate::authorize('vault-editor', $vaultId);
    $data = [
        'account_id' => Auth::user()->account_id,
        'author_id' => Auth::id(),
        'vault_id' => $vaultId,
        'first_name' => $request->input('first_name'),
        // ... more fields
    ];
    $contact = (new CreateContact)->execute($data);
    return response()->json([
        'data' => route('contact.show', ['vault' => $vaultId, 'contact' => $contact]),
    ], 201);
}
```

**3. BaseService Permission System** — Validates permissions with dependency resolution:
```php
public function validateRules(array $data): bool
{
    Validator::make($data, $this->rules())->validate();
    $permissions = collect($this->permissions());
    foreach (self::$permissionDependencies as $key => $values) {
        if ($permissions->contains($key)) {
            // Check dependencies exist, then validate
            $this->validatePermission($key, $data);
        }
    }
    return true;
}
```

### Routes Structure

All contact routes are nested under `vaults/{vault}/contacts/` with a `can:contact-owner,vault,contact` middleware on the contact-specific routes. The main routes are:

| Method | URI | Controller Method |
|---|---|---|
| GET | `vaults/{vault}/contacts` | `ContactController::index` |
| GET | `vaults/{vault}/contacts/create` | `ContactController::create` |
| POST | `vaults/{vault}/contacts` | `ContactController::store` |
| GET | `vaults/{vault}/contacts/{contact}` | `ContactController::show` |
| GET | `vaults/{vault}/contacts/{contact}/edit` | `ContactController::edit` |
| POST | `vaults/{vault}/contacts/{contact}` | `ContactController::update` |
| DELETE | `vaults/{vault}/contacts/{contact}` | `ContactController::destroy` |