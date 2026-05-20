Now I have a comprehensive picture. Let me compile the context document.

---

## Context Document: Authentication Controllers in nopCommerce

### Project Summary
**nopCommerce** is an open-source ASP.NET Core e-commerce platform. The codebase has ~6,275 files (3,502 C# source files, 947 Razor views, 296 JS files). It follows a **Layered Architecture** with a plugin system. The tech stack is ASP.NET Core MVC with Entity Framework (via FluentMigrator), and dependency injection throughout.

### Architecture
The project uses a **Layered Architecture** with these layers:

| Layer | Path | Responsibility |
|-------|------|----------------|
| **Presentation** | `Presentation/Nop.Web/` | MVC Controllers, Views, Models, Factories |
| **Presentation Framework** | `Presentation/Nop.Web.Framework/` | Base controllers, filters, infrastructure, validation |
| **Application/Services** | `Libraries/Nop.Services/` | Business logic, authentication, customer registration |
| **Domain/Core** | `Libraries/Nop.Core/` | Domain entities, settings, interfaces |
| **Data** | `Libraries/Nop.Data/` | Repositories, data providers, migrations |
| **Plugins** | `Plugins/` | Extensible modules (external auth, payments, shipping, etc.) |

**Controller hierarchy:**
- `Controller` (ASP.NET Core) → `BaseController` (framework) → `BasePublicController` (public store) / `BaseAdminController` (admin area) / `BasePluginController` (plugins)

### Key Files

#### Authentication Controllers

1. **`Presentation/Nop.Web/Areas/Admin/Controllers/AuthenticationController.cs`**
   - **Purpose**: Admin area controller for managing external authentication methods and multi-factor authentication methods (enable/disable, reorder).
   - **Base class**: `BaseAdminController`
   - **Key actions**: `ExternalMethods()`, `ExternalMethodUpdate()`, `MultiFactorMethods()`, `MultiFactorMethodUpdate()`

2. **`Presentation/Nop.Web/Controllers/CustomerController.cs`**
   - **Purpose**: Main customer-facing controller handling login, logout, registration, password recovery, account management, MFA configuration.
   - **Base class**: `BasePublicController`
   - **Key authentication actions**: `Login()`, `Logout()`, `Register()`, `PasswordRecovery()`, `MultiFactorVerification()`, `MultiFactorAuthentication()`

3. **`Plugins/Nop.Plugin.ExternalAuth.Facebook/Controllers/FacebookAuthenticationController.cs`**
   - **Purpose**: Facebook OAuth external authentication plugin controller.
   - **Base class**: `BasePluginController`
   - **Key actions**: `Configure()`, `Login()`, `LoginCallback()`, `DataDeletionStatusCheck()`

4. **`Plugins/Nop.Plugin.MultiFactorAuth.GoogleAuthenticator/Controllers/AuthenticationController.cs`**
   - **Purpose**: Google Authenticator MFA plugin controller.
   - **Base class**: `BasePluginController`
   - **Key actions**: `RegisterGoogleAuthenticator()`, `VerifyGoogleAuthenticator()`

#### Authentication Services

5. **`Libraries/Nop.Services/Authentication/IAuthenticationService.cs`**
   - Interface with `SignInAsync()`, `SignOutAsync()`, `GetAuthenticatedCustomerAsync()`

6. **`Libraries/Nop.Services/Authentication/CookieAuthenticationService.cs`**
   - Implementation using ASP.NET Core cookie authentication. Creates claims for username/email, signs in/out via `HttpContext.SignInAsync`/`SignOutAsync`.

7. **`Libraries/Nop.Services/Authentication/External/IExternalAuthenticationService.cs`**
   - Interface for external auth: `AuthenticateAsync()`, `GetExternalAuthenticationRecordByIdAsync()`, `AssociateExternalAccountWithUserAsync()`, etc.

8. **`Libraries/Nop.Services/Authentication/External/ExternalAuthenticationService.cs`**
   - Implementation handling external auth flow: checks for existing associations, registers new users, associates accounts.

9. **`Libraries/Nop.Services/Customers/ICustomerRegistrationService.cs`**
   - Interface with `ValidateCustomerAsync()`, `RegisterCustomerAsync()`, `SignInCustomerAsync()`, `ChangePasswordAsync()`

10. **`Libraries/Nop.Services/Authentication/AuthenticationMiddleware.cs`**
    - Middleware that processes authentication schemes and sets `HttpContext.User`.

11. **`Libraries/Nop.Services/Authentication/NopAuthenticationDefaults.cs`**
    - Constants: `AuthenticationScheme = "Authentication"`, `ClaimsIssuer = "nopCommerce"`, `LoginPath = "/login"`, etc.

#### Base Controllers

12. **`Presentation/Nop.Web.Framework/Controllers/BaseController.cs`**
    - Abstract base with attributes: `[HttpsRequirement]`, `[PublishModelEvents]`, `[SignOutFromExternalAuthentication]`, `[ValidatePassword]`, `[SaveIpAddress]`, `[SaveLastActivity]`, `[SaveLastVisitedPage]`, `[ForceMultiFactorAuthentication]`, `[AutoValidation]`

13. **`Presentation/Nop.Web/Controllers/BasePublicController.cs`**
    - Extends `BaseController` with: `[WwwRequirement]`, `[CheckLanguageSeoCode]`, `[CheckAccessPublicStore]`, `[CheckAccessClosedStore]`, `[CheckDiscountCoupon]`, `[CheckAffiliate]`

14. **`Presentation/Nop.Web/Areas/Admin/Controllers/BaseAdminController.cs`**
    - Extends `BaseController` with: `[Area(AreaNames.ADMIN)]`, `[AutoValidateAntiforgeryToken]`, `[ValidateIpAddress]`, `[AuthorizeAdmin]`, `[ValidateVendor]`, `[SaveSelectedTab]`, `[NotNullValidationMessage]`

15. **`Presentation/Nop.Web.Framework/Controllers/BasePluginController.cs`**
    - Extends `BaseController` with `[NotNullValidationMessage]`

16. **`Presentation/Nop.Web.Framework/Infrastructure/AuthenticationStartup.cs`**
    - Startup configuration registering `AddNopAuthentication()` and `UseNopAuthentication()` middleware.

### Key Symbols

#### Interfaces
- **`IAuthenticationService`** — `SignInAsync(Customer, bool)`, `SignOutAsync()`, `GetAuthenticatedCustomerAsync()`
- **`IExternalAuthenticationService`** — `AuthenticateAsync(ExternalAuthenticationParameters, string)`, CRUD for external auth records
- **`ICustomerRegistrationService`** — `ValidateCustomerAsync(string, string)`, `RegisterCustomerAsync(CustomerRegistrationRequest)`, `SignInCustomerAsync(Customer, string, bool)`, `ChangePasswordAsync(ChangePasswordRequest)`
- **`IAuthenticationPluginManager`** — Plugin management for external auth methods
- **`IMultiFactorAuthenticationPluginManager`** — Plugin management for MFA methods

#### Controllers
- **`AuthenticationController : BaseAdminController`** (Admin area)
  - Fields: `_externalAuthenticationSettings`, `_authenticationPluginManager`, `_eventPublisher`, `_externalAuthenticationMethodModelFactory`, `_multiFactorAuthenticationMethodModelFactory`, `_multiFactorAuthenticationPluginManager`, `_permissionService`, `_settingService`, `_multiFactorAuthenticationSettings`
  - Actions: `ExternalMethods()` (GET/POST), `ExternalMethodUpdate()` (POST), `MultiFactorMethods()` (GET/POST), `MultiFactorMethodUpdate()` (POST)

- **`CustomerController : BasePublicController`**
  - Fields: ~45 dependencies including `_authenticationService`, `_customerRegistrationService`, `_customerService`, `_externalAuthenticationService`, `_multiFactorAuthenticationPluginManager`, `_workContext`, `_storeContext`, etc.
  - Key actions: `Login()` (GET/POST), `Logout()`, `Register()` (GET/POST), `PasswordRecovery()` (GET/POST), `MultiFactorVerification()`, `MultiFactorAuthentication()` (GET/POST), `ChangePassword()`, `Info()`

- **`FacebookAuthenticationController : BasePluginController`**
  - Fields: `_facebookExternalAuthSettings`, `_authenticationPluginManager`, `_externalAuthenticationService`, `_localizationService`, `_notificationService`, `_optionsCache`, `_permissionService`, `_settingService`, `_storeContext`, `_workContext`
  - Actions: `Configure()` (GET/POST), `Login()`, `LoginCallback()`, `DataDeletionStatusCheck()`

- **`AuthenticationController : BasePluginController`** (Google Authenticator MFA)
  - Fields: `_customerSettings`, `_googleAuthenticatorService`, `_customerRegistrationService`, `_customerService`, `_localizationService`, `_notificationService`, `_workContext`
  - Actions: `RegisterGoogleAuthenticator()`, `VerifyGoogleAuthenticator()`

#### Key Models
- **`LoginModel`** — Username/Email, Password, RememberMe, CheckoutAsGuest
- **`RegisterModel`** — Full registration fields
- **`ExternalAuthenticationParameters`** — ProviderSystemName, AccessToken, Email, ExternalIdentifier, ExternalDisplayIdentifier, Claims
- **`ExternalAuthenticationRecord`** — CustomerId, Email, ExternalIdentifier, ProviderSystemName, OAuthAccessToken
- **`CustomerMultiFactorAuthenticationInfo`** — UserName, RememberMe, ReturnUrl (stored in session)
- **`MultiFactorAuthenticationProviderModel`** — View model for MFA provider configuration

### Dependencies

**Admin AuthenticationController** depends on:
- `Nop.Services.Authentication.External` → `IAuthenticationPluginManager`
- `Nop.Services.Authentication.MultiFactor` → `IMultiFactorAuthenticationPluginManager`
- `Nop.Services.Configuration` → `ISettingService`
- `Nop.Services.Security` → `IPermissionService`
- `Nop.Services.Plugins` → Plugin management
- `Nop.Web.Areas.Admin.Factories` → Model factories
- `Nop.Web.Framework.Mvc` → `NullJsonResult`
- `Nop.Web.Framework.Mvc.Filters` → `[CheckPermission]`

**CustomerController** depends on:
- `Nop.Services.Authentication` → `IAuthenticationService`
- `Nop.Services.Authentication.External` → `IExternalAuthenticationService`
- `Nop.Services.Authentication.MultiFactor` → `IMultiFactorAuthenticationPluginManager`
- `Nop.Services.Customers` → `ICustomerRegistrationService`, `ICustomerService`
- `Nop.Web.Factories` → `ICustomerModelFactory`
- `Nop.Web.Framework.Mvc.Filters` → `[CheckAccessClosedStore]`, `[CheckAccessPublicStore]`, `[ValidateCaptcha]`, `[ValidateHoneypot]`

**FacebookAuthenticationController** depends on:
- `Microsoft.AspNetCore.Authentication.Facebook` → Facebook auth scheme
- `Nop.Services.Authentication.External` → `IAuthenticationPluginManager`, `IExternalAuthenticationService`
- `Nop.Services.Configuration` → `ISettingService`
- `Nop.Web.Framework.Controllers` → `BasePluginController`

### Conventions

#### Naming Conventions
- **Classes**: PascalCase (`CustomerController`, `CookieAuthenticationService`)
- **Interfaces**: Prefix `I` (`IAuthenticationService`, `ICustomerRegistrationService`)
- **Fields**: `_camelCase` with underscore prefix (`_authenticationService`, _customerSettings)
- **Suffixes**: `Controller`, `Service`, `Model`, `Factory`, `Settings`, `Defaults`, `Plugin`, `Middleware`, `Startup`
- **Async methods**: `Async` suffix (`SignInAsync`, `GetAuthenticatedCustomerAsync`)
- **Namespaces**: Match folder structure (`Nop.Services.Authentication`, `Nop.Web.Controllers`)

#### Architectural Patterns
- **Repository Pattern**: `IRepository<T>` for data access
- **Service Pattern**: Business logic in service classes with interfaces
- **Factory Pattern**: Model factories (`ICustomerModelFactory`, `IExternalAuthenticationMethodModelFactory`) prepare view models
- **Plugin Pattern**: External auth and MFA are plugin-based via `IAuthenticationPluginManager` / `IMultiFactorAuthenticationPluginManager`
- **Event-driven**: `IEventPublisher` for domain events (`CustomerLoggedOutEvent`, `CustomerRegisteredEvent`, `CustomerActivatedEvent`)
- **DI via Constructor Injection**: All dependencies injected through constructor
- **Settings Pattern**: Settings classes (POCOs) injected directly (`CustomerSettings`, `ExternalAuthenticationSettings`)

#### Style Conventions
- **Async all the way**: All controller actions return `Task<IActionResult>`, all service methods are async
- **Error handling**: `ModelState.AddModelError()` for validation errors, `_notificationService` for user-facing messages
- **Validation**: `[ValidateCaptcha]`, `[ValidateHoneypot]` attributes; `ModelState.IsValid` checks
- **Authorization**: `[CheckPermission]` attribute for admin, `[AuthorizeAdmin]` for admin area, `Challenge()` for unauthenticated users
- **Filter attributes**: Heavy use of action filters (`[CheckAccessClosedStore]`, `[CheckAccessPublicStore]`, `[HttpsRequirement]`, `[ForceMultiFactorAuthentication]`)
- **View models**: Prepared via factory methods, not in controllers
- **Regions**: `#region Fields`, `#region Ctor`, `#region Methods`, `#region Utilities` for organization
- **`partial` keyword**: All controllers and services are `partial class` for extensibility

### Context for the Task

The authentication system in nopCommerce is distributed across:

1. **Admin AuthenticationController** — manages which external auth and MFA plugins are active. Uses `[CheckPermission]` for authorization. Updates settings via `ISettingService` and raises `PluginUpdatedEvent`.

2. **CustomerController** — the main user-facing auth controller. Login flow:
   - `Login()` GET shows form → POST validates via `ICustomerRegistrationService.ValidateCustomerAsync()`
   - On success: calls `ICustomerRegistrationService.SignInCustomerAsync()` which internally calls `IAuthenticationService.SignInAsync()`
   - On MFA required: stores `CustomerMultiFactorAuthenticationInfo` in session, redirects to `MultiFactorVerification()`
   - `Logout()` calls `IAuthenticationService.SignOutAsync()` and publishes `CustomerLoggedOutEvent`

3. **CookieAuthenticationService** — the concrete `IAuthenticationService`. Uses ASP.NET Core `HttpContext.SignInAsync` with `ClaimsIdentity`. Creates claims for username (`ClaimTypes.Name`) and email (`ClaimTypes.Email`). Caches authenticated customer.

4. **ExternalAuthenticationService** — handles OAuth/SSO flows. `AuthenticateAsync()` checks for existing associations, registers new users if needed, calls `ICustomerRegistrationService.SignInCustomerAsync()`.

5. **FacebookAuthenticationController** — example external auth plugin. Uses `Challenge()` with Facebook auth scheme, then `LoginCallback()` extracts claims and calls `IExternalAuthenticationService.AuthenticateAsync()`.

6. **Google Authenticator MFA Controller** — example MFA plugin. Uses TOTP validation via `GoogleAuthenticatorService.ValidateTwoFactorToken()`, then calls `ICustomerRegistrationService.SignInCustomerAsync()` on success.

**Key flow for adding a new authentication feature:**
- Create a controller extending `BasePluginController` (for plugins) or `BasePublicController` (for core)
- Inject services via constructor
- Use `IAuthenticationService.SignInAsync()` / `SignOutAsync()` for cookie auth
- Use `ICustomerRegistrationService.SignInCustomerAsync()` for login-after-validation
- Use `IExternalAuthenticationService.AuthenticateAsync()` for external/OAuth flows
- Use `[CheckPermission]` for admin authorization, `[CheckAccessPublicStore]` / `[CheckAccessClosedStore]` for public store access
- Use `_notificationService` for user messages, `_localizationService` for localized strings