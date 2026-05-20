Now I have a comprehensive understanding of the project. Let me compile the full architecture analysis.

---

## Project Summary

**Monica** is a **Personal Relationship Manager (PRM)** — an open-source CRM for managing personal relationships. It's built with **Laravel 12** (PHP 8.3+) on the backend and **Vue 3 + Inertia.js** on the frontend. The project has **2,093 files** (1,656 PHP, 254 Vue, 40 JSON, 15 YAML, 7 JS). It uses **MySQL/PostgreSQL** as the database, **Meilisearch/Typesense** for full-text search, and supports **CardDAV/CalDAV** synchronization for contact/calendar interoperability.

---

## Architecture

### Architecture Type: **Domain-Driven Modular Monolith with Service Layer**

The project follows a **Domain-Driven Design (DDD)** approach organized into bounded contexts (Domains), with a clear **Service Layer** pattern and **Inertia.js** for server-driven SPA rendering.

### Layers and Responsibilities

| Layer | Location | Responsibility |
|-------|----------|---------------|
| **Domain Modules** | `app/Domains/{Domain}/{Feature}/` | Bounded contexts — each domain is self-contained |
| **Controllers** | `app/Domains/*/Web/Controllers/` | HTTP request handling, delegates to Services |
| **Services** | `app/Domains/*/Services/` | Business logic, validation, permissions, persistence |
| **ViewHelpers** | `app/Domains/*/Web/ViewHelpers/` | Transform data for Vue frontend (DTO-like) |
| **Models** | `app/Models/` | Eloquent models, relationships, scopes |
| **Helpers** | `app/Helpers/` | Stateless utility classes |
| **Policies** | `app/Policies/` | Authorization gates |
| **Vue Pages** | `resources/js/Pages/` | Inertia.js page components |
| **Vue Components** | `resources/js/Components/` | Reusable UI components |
| **Vue Layouts** | `resources/js/Layouts/` | Layout wrappers |
| **API** | `routes/api.php` | REST API (Sanctum auth) |
| **Web Routes** | `routes/web.php` | Web routes (743 lines) |
| **DAV** | `app/Domains/Contact/Dav/` | CardDAV/CalDAV server implementation |
| **DAV Client** | `app/Domains/Contact/DavClient/` | External address book sync |

### Domain Structure (Bounded Contexts)

The `app/Domains/` directory contains the following top-level domains:

1. **Contact** — The core domain. Manages contacts, relationships, notes, calls, goals, tasks, loans, pets, photos, documents, reminders, labels, life events, mood tracking, groups, addresses, etc.
2. **Vault** — Vault management (data isolation containers), dashboard, journals, reports, calendar, companies, settings.
3. **Settings** — Account-level settings: personalization (templates, modules, genders, pronouns, relationship types, currencies, etc.), user management, preferences, notifications, storage, cancellation.

Each domain is further organized by feature (e.g., `ManageContact`, `ManageNotes`, `ManageCalls`), and each feature has its own `Services/`, `Web/Controllers/`, and `Web/ViewHelpers/` subdirectories.

---

## Key Files

### 1. `app/Http/Controllers/Controller.php`
**Purpose**: Base controller for all web controllers. Extends Laravel's base controller with `AuthorizesRequests`, `DispatchesJobs`, `ValidatesRequests`.
**Relevance**: Foundation of the controller layer.

### 2. `app/Services/BaseService.php`
**Purpose**: Abstract base class for all services. Provides validation, permission checking, and common utilities. All business logic services extend this.
**Relevance**: Core of the service layer pattern.

### 3. `app/Interfaces/ServiceInterface.php`
**Purpose**: Interface that all services implement. Defines `rules()` and `permissions()` methods.
**Relevance**: Enforces the service contract.

### 4. `app/Models/Contact.php`
**Purpose**: Core Eloquent model for contacts. Extends `VCardResource` (DAV support). Uses UUIDs, soft deletes, searchable via Scout.
**Relevance**: Central entity in the system.

### 5. `app/Models/Vault.php`
**Purpose**: Data isolation container. Contacts belong to vaults. Has permission levels (view=300, edit=200, manage=100) and types (personal, family, community).
**Relevance**: Core organizational unit.

### 6. `app/Models/Account.php`
**Purpose**: Top-level tenant. Has many users, vaults, templates, modules, genders, pronouns, etc.
**Relevance**: Multi-tenancy root.

### 7. `app/Models/User.php`
**Purpose**: Authenticatable user. Extends Laravel's `Authenticatable` with 2FA, WebAuthn, API tokens (Sanctum), email verification.
**Relevance**: User management and auth.

### 8. `app/Domains/Contact/ManageContact/Services/CreateContact.php`
**Purpose**: Service for creating contacts. Implements `ServiceInterface`, extends `BaseService`. Validates input, checks permissions, creates contact, updates dates, creates feed item.
**Relevance**: Exemplar of the service pattern.

### 9. `app/Domains/Contact/ManageContact/Web/Controllers/ContactController.php`
**Purpose**: Web controller for contact CRUD. Uses Inertia to render Vue pages. Delegates to Services and ViewHelpers.
**Relevance**: Exemplar of the controller pattern.

### 10. `app/Domains/Contact/ManageContact/Web/ViewHelpers/ContactShowViewHelper.php`
**Purpose**: Transforms contact data for the Vue frontend. Aggregates data from many module ViewHelpers.
**Relevance**: Exemplar of the ViewHelper pattern (DTO layer).

### 11. `app/Domains/Contact/Dav/VCardResource.php`
**Purpose**: Abstract base model for DAV-syncable resources. Extends Eloquent Model, implements `IDavResource`.
**Relevance**: Foundation for CardDAV/CalDAV sync.

### 12. `app/Services/QueuableService.php`
**Purpose**: Extends `BaseService` with queue support. Makes services dispatchable as jobs.
**Relevance**: Async processing pattern.

### 13. `app/Models/Module.php`
**Purpose**: Defines contact module types (notes, avatar, calls, pets, goals, addresses, etc.). Used for template-based contact page customization.
**Relevance**: Template/module system.

### 14. `app/Models/ContactFeedItem.php`
**Purpose**: Activity feed for contacts. Records all actions (created, updated, destroyed) on contact-related entities.
**Relevance**: Audit/activity tracking.

### 15. `app/Helpers/VaultHelper.php`
**Purpose**: Utility for checking user permissions in vaults. Uses array cache for performance.
**Relevance**: Authorization helper.

### 16. `app/Policies/VaultPolicy.php`
**Purpose**: Laravel policy for vault authorization. Delegates to Gates for vault-viewer, vault-editor, vault-manager checks.
**Relevance**: Authorization layer.

### 17. `routes/web.php`
**Purpose**: All web routes (743 lines). Maps URLs to domain controllers.
**Relevance**: Route definitions.

### 18. `routes/api.php`
**Purpose**: API routes. Currently minimal — user and vault resources.
**Relevance**: API surface.

### 19. `composer.json`
**Purpose**: Dependencies. Key packages: Laravel 12, Inertia.js, Jetstream, Fortify, Sanctum, Scout, Socialite, Sabre/DAV, WebAuthn, Sentry, Telescope.
**Relevance**: Technology stack.

### 20. `resources/js/Pages/Vault/Contact/Show.vue`
**Purpose**: Vue page for displaying a contact. Receives data from `ContactShowViewHelper`.
**Relevance**: Frontend rendering.

---

## Key Symbols

### Classes

| Class | Namespace | Base/Implements | Purpose |
|-------|-----------|-----------------|---------|
| `Controller` | `App\Http\Controllers` | `Illuminate\Routing\Controller` | Base web controller |
| `BaseService` | `App\Services` | (abstract) | Base service with validation + permissions |
| `QueuableService` | `App\Services` | `BaseService`, `ShouldQueue` | Queueable service |
| `ServiceInterface` | `App\Interfaces` | (interface) | Service contract: `rules()`, `permissions()` |
| `Contact` | `App\Models` | `VCardResource` | Core contact model |
| `Vault` | `App\Models` | `Model` | Data isolation container |
| `Account` | `App\Models` | `Model` | Multi-tenant root |
| `User` | `App\Models` | `Authenticatable` | Authenticated user |
| `Module` | `App\Models` | `Model` | Contact module type definitions |
| `ContactFeedItem` | `App\Models` | `Model` | Activity feed entries |
| `VCardResource` | `App\Domains\Contact\Dav` | `Model`, `IDavResource` | DAV-syncable model base |
| `VaultPolicy` | `App\Policies` | (policy) | Vault authorization |
| `VaultHelper` | `App\Helpers` | (static) | Permission checking utility |
| `ContactShowViewHelper` | `App\Domains\Contact\ManageContact\Web\ViewHelpers` | (static) | Contact page data transformer |
| `CreateContact` | `App\Domains\Contact\ManageContact\Services` | `BaseService`, `ServiceInterface` | Contact creation service |
| `UpdateContact` | `App\Domains\Contact\ManageContact\Services` | `BaseService`, `ServiceInterface` | Contact update service |
| `ImportVCard` | `App\Domains\Contact\Dav\Services` | `BaseService`, `ServiceInterface` | VCard import service |

### Key Methods

- **`BaseService::validateRules(array $data): bool`** — Validates data against `rules()` and checks `permissions()` dependencies
- **`BaseService::account(): Account`** — Returns the author's account
- **`CreateContact::execute(array $data): Contact`** — Creates a contact with validation, permission checks, feed item creation
- **`ContactShowViewHelper::data(Contact $contact, User $user): array`** — Builds the full contact show page data
- **`VaultHelper::getPermission(User $user, Vault $vault): ?int`** — Gets user's permission level in a vault
- **`VaultPolicy::view(User $user, Vault $vault): bool`** — Checks vault view permission

---

## Dependencies

### Module-Level Dependencies

```
app/Domains/Contact/  ────>  app/Models/, app/Services/, app/Interfaces/, app/Helpers/
app/Domains/Vault/    ────>  app/Models/, app/Services/, app/Interfaces/, app/Helpers/
app/Domains/Settings/ ────>  app/Models/, app/Services/, app/Interfaces/, app/Helpers/
app/Http/Controllers/ ────>  app/Domains/*/Web/Controllers/
app/Http/Controllers/ ────>  app/Models/
app/Services/         ────>  app/Models/, app/Exceptions/
app/Models/           ────>  (Laravel Eloquent base)
```

### Key File Dependencies

**`ContactController.php` imports:**
- `CreateContact`, `UpdateContact`, `DestroyContact`, `UpdateContactView` (Services)
- `ContactCreateViewHelper`, `ContactEditViewHelper`, `ContactIndexViewHelper`, `ContactShowViewHelper` (ViewHelpers)
- `VaultIndexViewHelper` (from Vault domain)
- `PaginatorHelper`, `Contact`, `User`, `Vault`, `Request`, `Auth`, `Gate`, `Inertia`

**`CreateContact.php` imports:**
- `ServiceInterface`, `Contact`, `ContactFeedItem`, `BaseService`, `Carbon`

**`ContactShowViewHelper.php` imports:**
- 20+ module ViewHelpers from various Contact sub-domains
- `StorageHelper`, `Contact`, `Module`, `TemplatePage`, `User`, `VaultQuickFactsTemplate`

---

## Conventions

### Naming Conventions

| Convention | Evidence | Examples |
|------------|----------|----------|
| **PascalCase classes** | All sampled classes | `ContactController`, `CreateContact`, `ContactShowViewHelper` |
| **Suffix `Controller`** | 161 controller files | `ContactController`, `ModuleAvatarController`, `ContactModuleCallController` |
| **Suffix `Service`** | 534 service files | `CreateContact`, `UpdateContact`, `ImportVCard` (services are in `Services/` namespace) |
| **Suffix `ViewHelper`** | ViewHelpers | `ContactShowViewHelper`, `ContactIndexViewHelper`, `VaultIndexViewHelper` |
| **Suffix `Interface`** | Interfaces | `ServiceInterface`, `IDavResource`, `IDAVBackend` |
| **Prefix `I` for interfaces** | DAV interfaces | `IDavResource`, `IDAVBackend`, `ICalDAVBackend` |
| **Suffix `Policy`** | Policies | `VaultPolicy` |
| **Suffix `Trait`** | Traits | `DAVFormat`, `HasUuids`, `JsonRespondController` |
| **Suffix `Helper`** | Helpers | `VaultHelper`, `AvatarHelper`, `DateHelper`, `ContactCardHelper` |
| **Suffix `Job`** | Queue jobs | `UpdateVCard`, `PushVCard`, `SynchronizeAddressBooks` |
| **Suffix `Event`** | Events | `FileDeleted`, `TokenDeleteEvent` |
| **Suffix `Listener`** | Listeners | `LoginListener`, `DeleteFileInStorage` |
| **Suffix `Middleware`** | Middleware | `Authenticate`, `HandleInertiaRequests`, `EnsureSignupIsEnabled` |
| **Suffix `Provider`** | Service providers | `AppServiceProvider`, `DAVServiceProvider` |
| **Suffix `Factory`** | Factories | `ContactFactory`, `AccountFactory` |
| **Suffix `Test`** | Tests | `ContactControllerTest`, `CreateContactTest` |
| **`Module` prefix** | Module controllers | `ModuleAvatarController`, `ModuleCallsViewHelper` |
| **`Personalize` prefix** | Settings controllers | `PersonalizeAddressTypeController`, `PersonalizeCurrencyController` |
| **`Manage` prefix** | Domain feature directories | `ManageContact`, `ManageNotes`, `ManageCalls` |

### Architectural Patterns

| Pattern | Evidence | Details |
|---------|----------|---------|
| **Service Layer** | `BaseService` + `ServiceInterface` | All business logic in services. Services have `rules()`, `permissions()`, `execute()` |
| **Permission System** | `BaseService::$permissionDependencies` | Hierarchical permissions: `author_must_belong_to_account` → `author_must_be_vault_editor` → `author_must_be_vault_manager` |
| **Validation** | `BaseService::validateRules()` | Services validate their own input data using Laravel validation rules |
| **ViewHelper (DTO)** | Static `data()` methods | ViewHelpers transform models into arrays for Inertia/Vue. No business logic. |
| **Inertia.js** | `Inertia::render()` in controllers | Server-driven SPA. Controllers return data + Vue component name. |
| **Repository-less** | Direct Eloquent in Services | No repository pattern — services use Eloquent models directly |
| **CQRS-lite** | Separate Create/Update/Destroy services | Each operation has its own service class |
| **Event-Driven** | `ContactFeedItem` creation in services | Services create feed items for activity tracking |
| **Queue Support** | `QueuableService` | Services can be dispatched as jobs for async processing |
| **DAV Server** | Sabre/DAV integration | Full CardDAV and CalDAV server implementation |
| **Multi-Tenancy** | `Account` → `Vault` hierarchy | Account has many vaults, vaults isolate contacts |
| **Template System** | `Template` + `TemplatePage` + `Module` | Contact pages are composed of configurable modules |
| **Policy + Gate** | `VaultPolicy` + `VaultHelper` | Authorization via Laravel policies and custom gates |

### Style Conventions

| Convention | Evidence |
|------------|----------|
| **Static methods on ViewHelpers** | All ViewHelpers use `public static function data(...)` |
| **Protected/private methods on Services** | Services use private methods for internal steps (`validate()`, `createContact()`, `createFeedItem()`) |
| **Type-hinted return types** | `execute(array $data): Contact`, `rules(): array` |
| **PHP 8 attributes** | `#[AllowDynamicProperties]`, `#[Override]` |
| **UUID primary keys** | `HasUuids` trait on all major models |
| **Soft deletes** | `SoftDeletes` trait on `Contact`, `VCardResource` |
| **Searchable** | `Searchable` trait + `#[SearchUsingFullText]` attributes on `Contact` |
| **Carbon dates** | `Carbon` for date manipulation |
| **Safe functions** | `use function Safe\preg_replace;` — uses `thecodingmachine/safe` |
| **Collection pipelines** | Heavy use of `->map()`, `->filter()`, `->sortByCollator()` on Eloquent collections |
| **Route model binding** | Controller methods receive `Vault $vault`, `Contact $contact` via implicit binding |

---

## Similar Implementations

### 1. Similar to `CreateContact` (Service pattern)

Services following the same `BaseService` + `ServiceInterface` pattern with `rules()`, `permissions()`, `execute()`:

| Class | File | Why Similar |
|-------|------|-------------|
| `UpdateContact` | `app/Domains/Contact/ManageContact/Services/UpdateContact.php` | Same domain, same pattern, same permission hierarchy |
| `DestroyContact` | `app/Domains/Contact/ManageContact/Services/DestroyContact.php` | Same domain, same pattern |
| `CreateAddress` | `app/Domains/Contact/ManageContactAddresses/Services/CreateAddress.php` | Same pattern, different sub-domain |
| `CreateNote` | `app/Domains/Contact/ManageNotes/Services/CreateNote.php` | Same pattern, different sub-domain |
| `CreateGoal` | `app/Domains/Contact/ManageGoals/Services/CreateGoal.php` | Same pattern, different sub-domain |
| `ImportVCard` | `app/Domains/Contact/Dav/Services/ImportVCard.php` | Same pattern, DAV sub-domain |

### 2. Similar to `ContactShowViewHelper` (ViewHelper pattern)

ViewHelpers following the static `data()` method pattern:

| Class | File | Why Similar |
|-------|------|-------------|
| `ContactIndexViewHelper` | `app/Domains/Contact/ManageContact/Web/ViewHelpers/ContactIndexViewHelper.php` | Same domain, list view |
| `ContactCreateViewHelper` | `app/Domains/Contact/ManageContact/Web/ViewHelpers/ContactCreateViewHelper.php` | Same domain, create form |
| `VaultIndexViewHelper` | `app/Domains/Vault/ManageVault/Web/ViewHelpers/VaultIndexViewHelper.php` | Different domain, same pattern |
| `SettingsIndexViewHelper` | `app/Domains/Settings/ManageSettings/Web/ViewHelpers/SettingsIndexViewHelper.php` | Different domain, same pattern |
| `ModuleNotesViewHelper` | `app/Domains/Contact/ManageNotes/Web/ViewHelpers/ModuleNotesViewHelper.php` | Module-level ViewHelper |

### 3. Similar to `ContactController` (Controller pattern)

Controllers following the Inertia + Service + ViewHelper pattern:

| Class | File | Why Similar |
|-------|------|-------------|
| `ContactModuleNoteController` | `app/Domains/Contact/ManageNotes/Web/Controllers/ContactModuleNoteController.php` | Same domain, module controller |
| `ContactModuleGoalController` | `app/Domains/Contact/ManageGoals/Web/Controllers/ContactModuleGoalController.php` | Same domain, module controller |
| `PersonalizeAddressTypeController` | `app/Domains/Settings/ManageAddressTypes/Web/Controllers/PersonalizeAddressTypeController.php` | Settings domain, same pattern |

---

## Context for the Task

### Project Identity
Monica is a **Personal Relationship Manager (PRM)** — an open-source web application for managing personal relationships. It's built with Laravel 12 + Vue 3 + Inertia.js.

### Core Data Model
```
Account (tenant)
  └── User (authenticatable, belongs to account)
  └── Vault (data isolation container)
        ├── Contact (core entity, belongs to vault)
        │     ├── Note, Call, Goal, Task, Loan, Pet, etc.
        │     ├── Address, ContactInformation
        │     ├── Reminder, ImportantDate
        │     ├── Label (many-to-many)
        │     ├── Photo, Document
        │     ├── LifeEvent, MoodTrackingEvent
        │     └── Relationship (to other contacts)
        ├── Group (collection of contacts)
        ├── Journal / Post
        └── Company
```

### Request Flow
```
Browser ──> Route (web.php) ──> Controller ──> Service (business logic)
                                                      │
                                                      ├── validateRules() [validation + permissions]
                                                      ├── execute() [business logic]
                                                      └── createFeedItem() [activity tracking]
                                                      │
                                                      ▼
                                              ViewHelper (data transform)
                                                      │
                                                      ▼
                                              Inertia::render() ──> Vue Page
```

### Key Code Snippets

**1. Service Pattern (CreateContact)**
```php
class CreateContact extends BaseService implements ServiceInterface
{
    public function rules(): array { /* validation rules */ }
    public function permissions(): array { /* permission requirements */ }
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

**2. Permission Dependency System (BaseService)**
```php
private static array $permissionDependencies = [
    'author_must_belong_to_account' => [],
    'author_must_be_vault_editor' => [
        'vault_must_belong_to_account',
        'author_must_belong_to_account',
    ],
    'author_must_be_vault_manager' => [
        'vault_must_belong_to_account',
        'author_must_belong_to_account',
    ],
];
```

**3. ViewHelper Pattern (ContactShowViewHelper)**
```php
class ContactShowViewHelper
{
    public static function data(Contact $contact, User $user): array
    {
        // Aggregates data from many module ViewHelpers
        return [
            'contact_name' => ModuleContactNameViewHelper::data($contact, $user),
            'contact_information' => self::getContactInformation(...),
            'modules' => self::modules($firstPage, $contact, $user),
            'url' => [ /* route URLs */ ],
        ];
    }
}
```

### Key Architectural Decisions
- **No Repository pattern** — Services use Eloquent models directly
- **No DTO classes** — ViewHelpers return plain arrays as DTOs
- **Static ViewHelpers** — All ViewHelper methods are static, no dependency injection
- **Service-per-operation** — Each CRUD operation has its own service class (CQRS-lite)
- **Hierarchical permissions** — Permissions have dependencies that are automatically checked
- **Activity feed** — Every meaningful action creates a `ContactFeedItem` for the activity timeline
- **Template-driven UI** — Contact pages are composed of configurable modules via templates
- **DAV-first** — Contact model extends `VCardResource` for native CardDAV support