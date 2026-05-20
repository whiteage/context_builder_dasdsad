Now I have a comprehensive understanding of the authentication system. Let me compile the full context document.

---

## 1. PROJECT SUMMARY

**nopCommerce** — open-source ASP.NET Core eCommerce platform (.NET 9). 6,351 files total (3,499 C#, 947 Razor, 296 JS). Uses a **Layered Architecture** with Plugins: `Nop.Core` (domain entities, settings), `Nop.Data` (repositories), `Nop.Services` (business logic), `Nop.Web` (presentation), `Nop.Web.Framework` (shared framework). Authentication is currently **cookie-only** with an external auth plugin system (Facebook OAuth example).

## 2. ARCHITECTURE

**Architecture type**: Layered + Plugin-based (Modular Monolith)

**Layers**:
- **Nop.Core** — Domain entities (`Customer`, `ExternalAuthenticationRecord`), settings (`ExternalAuthenticationSettings`, `CookieSettings`), enums (`CustomerLoginResults`)
- **Nop.Services** — Business logic: `IAuthenticationService` / `CookieAuthenticationService`, `IExternalAuthenticationService` / `ExternalAuthenticationService`, `ICustomerRegistrationService` / `CustomerRegistrationService`, `AuthenticationMiddleware`
- **Nop.Web.Framework** — Startup configuration: `ServiceCollectionExtensions.AddNopAuthentication()` (registers cookie schemes + discovers external auth plugins), `AuthenticationStartup`, `AuthorizationStartup`
- **Nop.Web** — Controllers (`CustomerController` with Login/Logout), Views (`Login.cshtml`), Model Factories (`CustomerModelFactory`, `ExternalAuthenticationModelFactory`)
- **Plugins** — `Nop.Plugin.ExternalAuth.Facebook` (the only external auth plugin)

**Current auth flow**:
1. `AddNopAuthentication()` in `ServiceCollectionExtensions.cs` registers **two cookie schemes**: `"Authentication"` (main) and `"ExternalAuthentication"` (external)
2. `AuthenticationMiddleware` runs on every request, tries to authenticate via the default scheme
3. `CookieAuthenticationService` implements `IAuthenticationService` — creates ClaimsIdentity with username/email claims, stores in cookie
4. External auth plugins implement `IExternalAuthenticationRegistrar.Configure(AuthenticationBuilder)` to register OAuth handlers (e.g., `AddFacebook()`)
5. `IExternalAuthenticationMethod` is a marker interface for plugins (returns a ViewComponent type for the login button)
6. `ExternalAuthenticationService` orchestrates the external auth flow (register new user, associate accounts, sign in)

## 3. RELATED FILES

### Core Authentication Interfaces & Implementation

| File | Path | Entity Type | Relevance |
|------|------|-------------|-----------|
| **IAuthenticationService.cs** | `src/Libraries/Nop.Services/Authentication/IAuthenticationService.cs` | service (interface) | **Central interface** — defines `SignInAsync`, `SignOutAsync`, `GetAuthenticatedCustomerAsync`. Must be abstracted to support multiple providers. |
| **CookieAuthenticationService.cs** | `src/Libraries/Nop.Services/Authentication/CookieAuthenticationService.cs` | service | **Current sole implementation** of `IAuthenticationService`. Uses ASP.NET Core cookie auth with ClaimsIdentity. Hard-coded to cookie scheme `"Authentication"`. |
| **AuthenticationMiddleware.cs** | `src/Libraries/Nop.Services/Authentication/AuthenticationMiddleware.cs` | service (middleware) | Runs on every request. Iterates request handler schemes, then authenticates via default scheme. Sets `context.User`. |
| **NopAuthenticationDefaults.cs** | `src/Libraries/Nop.Services/Authentication/NopAuthenticationDefaults.cs` | service (constants) | Defines scheme names (`"Authentication"`, `"ExternalAuthentication"`), claims issuer (`"nopCommerce"`), login path, etc. |

### External Authentication Plugin System

| File | Path | Entity Type | Relevance |
|------|------|-------------|-----------|
| **IExternalAuthenticationMethod.cs** | `src/Libraries/Nop.Services/Authentication/External/IExternalAuthenticationMethod.cs` | service (interface) | Plugin marker — returns a ViewComponent type for the login button UI. |
| **IExternalAuthenticationRegistrar.cs** | `src/Libraries/Nop.Services/Authentication/External/IExternalAuthenticationRegistrar.cs` | service (interface) | **Key abstraction** — plugins implement `Configure(AuthenticationBuilder)` to register OAuth handlers. |
| **IExternalAuthenticationService.cs** | `src/Libraries/Nop.Services/Authentication/External/IExternalAuthenticationService.cs` | service (interface) | Orchestrates external auth: `AuthenticateAsync`, `AssociateExternalAccountWithUserAsync`, etc. |
| **ExternalAuthenticationService.cs** | `src/Libraries/Nop.Services/Authentication/External/ExternalAuthenticationService.cs` | service | Implementation — handles new user registration, account association, sign-in via `IAuthenticationService`. |
| **ExternalAuthenticationParameters.cs** | `src/Libraries/Nop.Services/Authentication/External/ExternalAuthenticationParameters.cs` | dto | DTO carrying provider system name, external identifier, email, access token, claims. |
| **ExternalAuthenticationClaim.cs** | `src/Libraries/Nop.Services/Authentication/External/ExternalAuthenticationClaim.cs` | dto | Simple claim type/value pair. |
| **IAuthenticationPluginManager.cs** | `src/Libraries/Nop.Services/Authentication/External/IAuthenticationPluginManager.cs` | service (interface) | Loads active external auth plugins. |
| **AuthenticationPluginManager.cs** | `src/Libraries/Nop.Services/Authentication/External/AuthenticationPluginManager.cs` | service | Checks `ExternalAuthenticationSettings.ActiveAuthenticationMethodSystemNames`. |

### Facebook OAuth Plugin (Reference Implementation)

| File | Path | Entity Type | Relevance |
|------|------|-------------|-----------|
| **FacebookAuthenticationRegistrar.cs** | `src/Plugins/Nop.Plugin.ExternalAuth.Facebook/Infrastructure/FacebookAuthenticationRegistrar.cs` | handler | Implements `IExternalAuthenticationRegistrar` — calls `builder.AddFacebook()`. **Pattern to follow for new providers.** |
| **FacebookAuthenticationController.cs** | `src/Plugins/Nop.Plugin.ExternalAuth.Facebook/Controllers/FacebookAuthenticationController.cs` | controller | Login/LoadCallback actions. Uses `Challenge()` with `FacebookDefaults.AuthenticationScheme`, then calls `IExternalAuthenticationService.AuthenticateAsync()`. |
| **FacebookAuthenticationMethod.cs** | `src/Plugins/Nop.Plugin.ExternalAuth.Facebook/FacebookAuthenticationMethod.cs` | service | Implements `IExternalAuthenticationMethod` + `BasePlugin`. Returns `FacebookAuthenticationViewComponent`. |
| **FacebookAuthenticationDefaults.cs** | `src/Plugins/Nop.Plugin.ExternalAuth.Facebook/FacebookAuthenticationDefaults.cs` | service (constants) | Plugin system name `"ExternalAuth.Facebook"`, route names. |
| **FacebookExternalAuthSettings.cs** | `src/Plugins/Nop.Plugin.ExternalAuth.Facebook/FacebookExternalAuthSettings.cs` | entity (settings) | `ClientKeyIdentifier` and `ClientSecret`. |

### Customer Login Flow

| File | Path | Entity Type | Relevance |
|------|------|-------------|-----------|
| **CustomerController.cs** | `src/Presentation/Nop.Web/Controllers/CustomerController.cs` | controller | Login (GET/POST), Logout, MultiFactorVerification. Uses `IAuthenticationService` and `ICustomerRegistrationService`. |
| **CustomerRegistrationService.cs** | `src/Libraries/Nop.Services/Customers/CustomerRegistrationService.cs` | service | `SignInCustomerAsync()` calls `IAuthenticationService.SignInAsync()`. `ValidateCustomerAsync()` returns `CustomerLoginResults`. |
| **ICustomerRegistrationService.cs** | `src/Libraries/Nop.Services/Customers/ICustomerRegistrationService.cs` | service (interface) | Defines `ValidateCustomerAsync`, `SignInCustomerAsync`, `RegisterCustomerAsync`. |
| **LoginModel.cs** | `src/Presentation/Nop.Web/Models/Customer/LoginModel.cs` | dto | Login form model: Email/Username, Password, RememberMe. |
| **Login.cshtml** | `src/Presentation/Nop.Web/Views/Customer/Login.cshtml` | page (view) | Renders login form + external auth buttons via `ExternalMethodsViewComponent`. |
| **ExternalMethodsViewComponent.cs** | `src/Presentation/Nop.Web/Components/ExternalMethodsViewComponent.cs` | widget | Renders external auth method buttons. |
| **ExternalAuthenticationModelFactory.cs** | `src/Presentation/Nop.Web/Factories/ExternalAuthenticationModelFactory.cs` | factory | Loads active external auth plugins and returns their ViewComponent types. |
| **CustomerModelFactory.cs** | `src/Presentation/Nop.Web/Factories/CustomerModelFactory.cs` | factory | `PrepareLoginModelAsync()` prepares the login view model. |

### Configuration & Startup

| File | Path | Entity Type | Relevance |
|------|------|-------------|-----------|
| **ServiceCollectionExtensions.cs** | `src/Presentation/Nop.Web.Framework/Infrastructure/Extensions/ServiceCollectionExtensions.cs` | service (startup) | `AddNopAuthentication()` — registers cookie schemes, discovers `IExternalAuthenticationRegistrar` plugins. **Must be extended for JWT/Bearer.** |
| **ApplicationBuilderExtensions.cs** | `src/Presentation/Nop.Web.Framework/Infrastructure/Extensions/ApplicationBuilderExtensions.cs` | service (startup) | `UseNopAuthentication()` — adds `AuthenticationMiddleware` to pipeline. |
| **AuthenticationStartup.cs** | `src/Presentation/Nop.Web.Framework/Infrastructure/AuthenticationStartup.cs` | service (startup) | Calls `AddNopDataProtection()`, `AddNopAuthentication()`, `UseNopAuthentication()`. |
| **AuthorizationStartup.cs** | `src/Presentation/Nop.Web.Framework/Infrastructure/AuthorizationStartup.cs` | service (startup) | Adds `UseAuthorization()` middleware. |
| **NopStartup.cs** (Web.Framework) | `src/Presentation/Nop.Web.Framework/Infrastructure/NopStartup.cs` | service (startup) | Registers `IAuthenticationService → CookieAuthenticationService` (line 207), `IExternalAuthenticationService → ExternalAuthenticationService` (line 231). |
| **NopCookieDefaults.cs** | `src/Libraries/Nop.Core/Http/NopCookieDefaults.cs` | service (constants) | Cookie names: `.Nop.Authentication`, `.Nop.ExternalAuthentication`, etc. |

### Domain Entities

| File | Path | Entity Type | Relevance |
|------|------|-------------|-----------|
| **ExternalAuthenticationRecord.cs** | `src/Libraries/Nop.Core/Domain/Customers/ExternalAuthenticationRecord.cs` | entity | DB record linking external identity to customer. Fields: `CustomerId`, `ExternalIdentifier`, `OAuthToken`, `OAuthAccessToken`, `ProviderSystemName`. |
| **ExternalAuthenticationSettings.cs** | `src/Libraries/Nop.Core/Domain/Customers/ExternalAuthenticationSettings.cs` | entity (settings) | `ActiveAuthenticationMethodSystemNames` (list), `RequireEmailValidation`, `LogErrors`. |
| **CustomerLoginResults.cs** | `src/Libraries/Nop.Core/Domain/Customers/CustomerLoginResults.cs` | entity (enum) | `Successful`, `MultiFactorAuthenticationRequired`, `WrongPassword`, etc. |
| **CookieSettings.cs** | `src/Libraries/Nop.Core/Security/CookieSettings.cs` | entity (settings) | Cookie configuration. |

## 4. DEPENDENCY GRAPH

### Module-Level Dependencies

```
Nop.Web (Controllers, Views)
  └── Nop.Web.Framework (Startup, Extensions)
        └── Nop.Services (Business Logic)
              ├── Nop.Core (Domain, Settings)
              └── Nop.Data (Repository)
Plugins (e.g., ExternalAuth.Facebook)
  └── Nop.Services (IExternalAuthenticationRegistrar, IExternalAuthenticationMethod)
  └── Nop.Core (ISettings)
```

### File-Level Dependencies (Key Chain)

```
CustomerController.Login()
  → ICustomerRegistrationService.ValidateCustomerAsync()
  → ICustomerRegistrationService.SignInCustomerAsync()
      → IAuthenticationService.SignInAsync()  [CookieAuthenticationService]
          → HttpContext.SignInAsync("Authentication", ...)
      → IWorkContext.SetCurrentCustomerAsync()
      
FacebookAuthenticationController.Login()
  → Challenge(FacebookDefaults.AuthenticationScheme)
  
FacebookAuthenticationController.LoginCallback()
  → HttpContext.AuthenticateAsync(FacebookDefaults.AuthenticationScheme)
  → IExternalAuthenticationService.AuthenticateAsync()
      → IAuthenticationService.SignInAsync()  [CookieAuthenticationService]
      
AuthenticationMiddleware.InvokeAsync()
  → Schemes.GetRequestHandlerSchemesAsync()
  → context.AuthenticateAsync(defaultAuthenticate.Name)
  → context.User = result.Principal

AddNopAuthentication()
  → services.AddAuthentication() with cookie schemes
  → typeFinder.FindClassesOfType<IExternalAuthenticationRegistrar>()
  → instance.Configure(authenticationBuilder)  [e.g., AddFacebook()]
```

### Call Graph (Login Flow)

```
GET /login → CustomerController.Login(GET)
  → CustomerModelFactory.PrepareLoginModelAsync()
  → View(Login.cshtml)
      → ExternalMethodsViewComponent
          → ExternalAuthenticationModelFactory.PrepareExternalMethodsModelAsync()
              → AuthenticationPluginManager.LoadActivePluginsAsync()
              → For each: authenticationMethod.GetPublicViewComponent()

POST /login → CustomerController.Login(POST)
  → CustomerRegistrationService.ValidateCustomerAsync(usernameOrEmail, password)
  → If Successful:
      → CustomerRegistrationService.SignInCustomerAsync(customer, returnUrl, rememberMe)
          → ShoppingCartService.MigrateShoppingCartAsync()
          → WorkContext.SetCurrentCustomerAsync()
          → AuthenticationService.SignInAsync(customer, isPersist)
              → Creates ClaimsIdentity with username/email claims
              → HttpContext.SignInAsync("Authentication", principal, props)
          → EventPublisher.PublishAsync(CustomerLoggedinEvent)
```

## 5. CONVENTIONS

### Naming Conventions
1. **Interface prefix `I`**: `IAuthenticationService`, `IExternalAuthenticationMethod`, `IExternalAuthenticationRegistrar`, `IRepository<T>`
2. **Service suffix**: `CookieAuthenticationService`, `ExternalAuthenticationService`, `CustomerRegistrationService`
3. **Defaults suffix (static constants)**: `NopAuthenticationDefaults`, `FacebookAuthenticationDefaults`, `NopCookieDefaults`
4. **Settings suffix (ISettings)**: `ExternalAuthenticationSettings`, `FacebookExternalAuthSettings`, `CookieSettings`
5. **Model suffix (DTOs)**: `LoginModel`, `ExternalAuthenticationMethodModel`, `ConfigurationModel`
6. **Factory suffix**: `CustomerModelFactory`, `ExternalAuthenticationModelFactory`
7. **Controller suffix**: `CustomerController`, `FacebookAuthenticationController`, `AuthenticationController`
8. **ViewComponent suffix**: `ExternalMethodsViewComponent`, `FacebookAuthenticationViewComponent`
9. **Plugin naming**: `Nop.Plugin.{Category}.{Name}` — e.g., `Nop.Plugin.ExternalAuth.Facebook`
10. **System name pattern**: `"ExternalAuth.Facebook"` (Category.Provider)
11. **Async suffix**: All service methods return `Task<T>` and end with `Async`
12. **`partial` keyword**: All classes are `partial` — `public partial class CookieAuthenticationService`
13. **`record` for models**: `public partial record LoginModel : BaseNopModel`
14. **`enum` for results**: `CustomerLoginResults` with values `Successful = 1`, `WrongPassword = 3`, etc.

### Architectural Patterns
- **Plugin pattern**: External auth methods are plugins implementing `IExternalAuthenticationMethod` + `IExternalAuthenticationRegistrar`
- **Strategy pattern**: `IAuthenticationService` is the strategy interface, `CookieAuthenticationService` is the current implementation
- **Service pattern**: All business logic behind interfaces, registered in DI as scoped
- **Factory pattern**: `*ModelFactory` classes prepare view models for controllers
- **Event-driven**: `IEventPublisher` / `IConsumer<T>` for cross-cutting concerns (e.g., `CustomerLoggedinEvent`)
- **Repository pattern**: `IRepository<T>` for data access
- **Settings pattern**: `ISettings` interface, auto-registered and loaded per-store

### Style Conventions
- All methods are `virtual async Task`
- `ArgumentNullException.ThrowIfNull()` for null checks
- `EngineContext.Current.Resolve<T>()` for service location (used in startup/static contexts)
- `ThrowIfNull()` extension on parameters
- Namespace matches folder path: `Nop.Services.Authentication`, `Nop.Services.Authentication.External`
- File-scoped namespaces: `namespace Nop.Services.Authentication;`

## 6. SIMILAR IMPLEMENTATIONS

### Classes following the same patterns as `CookieAuthenticationService`:

1. **`ExternalAuthenticationService`** (`src/Libraries/Nop.Services/Authentication/External/ExternalAuthenticationService.cs`)
   - **Why similar**: Same layer (Nop.Services.Authentication), same pattern (service implementation behind interface), same dependency style (injects services via constructor), same `partial class` pattern. Both are consumed by `CustomerController`.

2. **`CustomerRegistrationService`** (`src/Libraries/Nop.Services/Customers/CustomerRegistrationService.cs`)
   - **Why similar**: Directly depends on `IAuthenticationService`. Implements `ICustomerRegistrationService`. Contains `SignInCustomerAsync()` which calls `IAuthenticationService.SignInAsync()`. Same constructor injection pattern.

3. **`FacebookAuthenticationMethod`** (`src/Plugins/Nop.Plugin.ExternalAuth.Facebook/FacebookAuthenticationMethod.cs`)
   - **Why similar**: Implements `IExternalAuthenticationMethod` (the plugin interface for external auth). Extends `BasePlugin`. Returns a ViewComponent type. This is the pattern any new OAuth provider would follow.

4. **`FacebookAuthenticationRegistrar`** (`src/Plugins/Nop.Plugin.ExternalAuth.Facebook/Infrastructure/FacebookAuthenticationRegistrar.cs`)
   - **Why similar**: Implements `IExternalAuthenticationRegistrar`. Calls `builder.AddFacebook()`. This is the pattern for registering OAuth middleware handlers.

5. **`GoogleAuthenticatorMethod`** (`src/Plugins/Nop.Plugin.MultiFactorAuth.GoogleAuthenticator/GoogleAuthenticatorMethod.cs`)
   - **Why similar**: Implements `IMultiFactorAuthenticationMethod` (parallel pattern to `IExternalAuthenticationMethod`). Same plugin architecture, same `BasePlugin` base class.

## 7. TASK CONTEXT

### What needs to be refactored

The current authentication system is **cookie-only**. `IAuthenticationService` has a single implementation (`CookieAuthenticationService`) that hard-codes cookie-based auth. To support multiple auth providers (OAuth, JWT, Cookie), the system needs:

### Key Design Decisions

1. **`IAuthenticationService` must become an abstraction** — Currently it's a single interface with one implementation. It should become a **provider abstraction** where different auth strategies can be plugged in.

2. **The `AuthenticationMiddleware` must be provider-aware** — Currently it authenticates via the default scheme only. It needs to detect which auth mechanism the request is using.

3. **The `AddNopAuthentication()` startup must register multiple schemes** — Currently registers only cookie schemes. Must also register JWT Bearer and potentially other schemes.

4. **The plugin system (`IExternalAuthenticationRegistrar`) is already extensible** — This pattern can be reused for auth providers. Each provider registers its own ASP.NET Core authentication scheme.

### Files to modify

| File | What to change |
|------|---------------|
| `IAuthenticationService.cs` | Refactor to support multiple providers — either make it a composite/strategy or add provider resolution |
| `CookieAuthenticationService.cs` | Keep as the cookie provider implementation |
| **New: `JwtAuthenticationService.cs`** | New implementation for JWT Bearer token auth |
| **New: `OAuthAuthenticationService.cs`** | New implementation for OAuth token-based auth |
| `AuthenticationMiddleware.cs` | Make provider-aware — detect auth type from request (cookie vs. Authorization header) |
| `NopAuthenticationDefaults.cs` | Add JWT scheme name, Bearer token constants |
| `ServiceCollectionExtensions.cs` | `AddNopAuthentication()` — register JWT Bearer scheme alongside cookies |
| `NopStartup.cs` (Web.Framework) | Register new auth service implementations |
| `CustomerController.cs` | May need to support token-based login responses (return JWT token instead of redirect) |
| `CustomerRegistrationService.cs` | `SignInCustomerAsync()` currently returns `IActionResult` (redirect). For API/JWT, needs to return token. |
| `NopCookieDefaults.cs` | May need JWT-related cookie/token constants |

### New files to create

| File | Purpose |
|------|---------|
| `src/Libraries/Nop.Services/Authentication/JwtAuthenticationService.cs` | Implements `IAuthenticationService` for JWT Bearer tokens |
| `src/Libraries/Nop.Services/Authentication/IJwtTokenProvider.cs` | Interface for JWT token generation/validation |
| `src/Libraries/Nop.Services/Authentication/JwtTokenProvider.cs` | JWT token generation/validation implementation |
| `src/Libraries/Nop.Core/Domain/Customers/JwtSettings.cs` | JWT configuration (issuer, audience, secret, expiry) |

### Abstraction Strategy

**Recommended approach: Strategy Pattern with Provider Resolution**

```
IAuthenticationService (abstraction)
├── CookieAuthenticationService (existing, refactored)
├── JwtAuthenticationService (new)
└── OAuthAuthenticationService (new)

AuthenticationMiddleware
  └── Resolves which IAuthenticationService to use based on request:
       - Has "Authorization: Bearer" header → JwtAuthenticationService
       - Has auth cookie → CookieAuthenticationService
       - Has "Authorization: OAuth" header → OAuthAuthenticationService
```

**Alternative: Composite Pattern**
```
IAuthenticationService
└── CompositeAuthenticationService
      ├── CookieAuthenticationService
      ├── JwtAuthenticationService
      └── OAuthAuthenticationService
      
CompositeAuthenticationService.SignInAsync():
  → Tries each provider until one succeeds
```

**Recommended: Use ASP.NET Core's built-in scheme system** — Each provider registers its own scheme (cookie, Bearer, etc.) and the middleware uses the scheme to authenticate. The `IAuthenticationService` becomes a **facade** that delegates to the correct scheme based on context.

### Critical constraints
- `CustomerRegistrationService.SignInCustomerAsync()` returns `IActionResult` (redirect) — this is **not suitable for API/JWT scenarios**. The refactoring must decouple the sign-in result from HTTP redirects.
- `ExternalAuthenticationService.AuthenticateAsync()` also returns `IActionResult` — same issue.
- The `IExternalAuthenticationRegistrar` pattern is already extensible and should be reused for new auth providers.
- All existing code uses `IAuthenticationService` — the interface signature must remain backward-compatible or all callers must be updated.

## 8. RELEVANT CODE SNIPPETS

### Snippet 1: Current `IAuthenticationService` interface — the central abstraction to refactor

**File**: `src/Libraries/Nop.Services/Authentication/IAuthenticationService.cs` (lines 8-31)
```csharp
public partial interface IAuthenticationService
{
    Task SignInAsync(Customer customer, bool isPersistent);
    Task SignOutAsync();
    Task<Customer> GetAuthenticatedCustomerAsync();
}
```
**Why relevant**: This is the **core interface** that must be extended/refactored. Currently only has 3 methods. For multi-provider support, it may need a way to specify which provider to use, or become a composite.

### Snippet 2: Current `CookieAuthenticationService.SignInAsync()` — hard-coded to cookie scheme

**File**: `src/Libraries/Nop.Services/Authentication/CookieAuthenticationService.cs` (lines 45-74)
```csharp
public virtual async Task SignInAsync(Customer customer, bool isPersistent)
{
    var claims = new List<Claim>();
    if (!string.IsNullOrEmpty(customer.Username))
        claims.Add(new Claim(ClaimTypes.Name, customer.Username, ClaimValueTypes.String, NopAuthenticationDefaults.ClaimsIssuer));
    if (!string.IsNullOrEmpty(customer.Email))
        claims.Add(new Claim(ClaimTypes.Email, customer.Email, ClaimValueTypes.Email, NopAuthenticationDefaults.ClaimsIssuer));
    var userIdentity = new ClaimsIdentity(claims, NopAuthenticationDefaults.AuthenticationScheme);
    var userPrincipal = new ClaimsPrincipal(userIdentity);
    var authenticationProperties = new AuthenticationProperties { IsPersistent = isPersistent, IssuedUtc = DateTime.UtcNow };
    await _httpContextAccessor.HttpContext.SignInAsync(NopAuthenticationDefaults.AuthenticationScheme, userPrincipal, authenticationProperties);
    _cachedCustomer = customer;
}
```
**Why relevant**: This is the **only implementation** of `SignInAsync`. It hard-codes `NopAuthenticationDefaults.AuthenticationScheme` ("Authentication") and uses `HttpContext.SignInAsync()` which is cookie-specific. A JWT implementation would generate a token instead.

### Snippet 3: `AddNopAuthentication()` — where auth schemes are registered

**File**: `src/Presentation/Nop.Web.Framework/Infrastructure/Extensions/ServiceCollectionExtensions.cs` (lines 255-295)
```csharp
public static void AddNopAuthentication(this IServiceCollection services)
{
    var authenticationBuilder = services.AddAuthentication(options =>
    {
        options.DefaultChallengeScheme = NopAuthenticationDefaults.AuthenticationScheme;
        options.DefaultScheme = NopAuthenticationDefaults.AuthenticationScheme;
        options.DefaultSignInScheme = NopAuthenticationDefaults.ExternalAuthenticationScheme;
    });
    authenticationBuilder.AddCookie(NopAuthenticationDefaults.AuthenticationScheme, options => { ... });
    authenticationBuilder.AddCookie(NopAuthenticationDefaults.ExternalAuthenticationScheme, options => { ... });
    var typeFinder = Singleton<ITypeFinder>.Instance;
    var externalAuthConfigurations = typeFinder.FindClassesOfType<IExternalAuthenticationRegistrar>();
    var externalAuthInstances = externalAuthConfigurations
        .Select(x => (IExternalAuthenticationRegistrar)Activator.CreateInstance(x));
    foreach (var instance in externalAuthInstances)
        instance.Configure(authenticationBuilder);
}
```
**Why relevant**: This is where **new auth schemes must be added** (e.g., `authenticationBuilder.AddJwtBearer()`). The `IExternalAuthenticationRegistrar` pattern is already extensible and can be reused.

### Snippet 4: `FacebookAuthenticationRegistrar` — the plugin pattern for OAuth registration

**File**: `src/Plugins/Nop.Plugin.ExternalAuth.Facebook/Infrastructure/FacebookAuthenticationRegistrar.cs` (lines 13-47)
```csharp
public class FacebookAuthenticationRegistrar : IExternalAuthenticationRegistrar
{
    public void Configure(AuthenticationBuilder builder)
    {
        builder.AddFacebook(FacebookDefaults.AuthenticationScheme, options =>
        {
            var settings = EngineContext.Current.Resolve<FacebookExternalAuthSettings>();
            options.AppId = string.IsNullOrEmpty(settings?.ClientKeyIdentifier) ? nameof(options.AppId) : settings.ClientKeyIdentifier;
            options.AppSecret = string.IsNullOrEmpty(settings?.ClientSecret) ? nameof(options.AppSecret) : settings.ClientSecret;
            options.SaveTokens = true;
            options.Events = new OAuthEvents
            {
                OnRemoteFailure = context =>
                {
                    context.HandleResponse();
                    var errorUrl = context.Properties.GetString(FacebookAuthenticationDefaults.ErrorCallback);
                    context.Response.Redirect(errorUrl);
                    return Task.FromResult(0);
                }
            };
        });
    }
}
```
**Why relevant**: This is the **reference pattern** for adding new OAuth providers (Google, GitHub, Microsoft, etc.). Each new provider would create a similar registrar class.

### Snippet 5: `CustomerRegistrationService.SignInCustomerAsync()` — ties auth to HTTP redirects

**File**: `src/Libraries/Nop.Services/Customers/CustomerRegistrationService.cs` (lines 422-454)
```csharp
public virtual async Task<IActionResult> SignInCustomerAsync(Customer customer, string returnUrl, bool isPersist = false)
{
    var currentCustomer = await _workContext.GetCurrentCustomerAsync();
    if (currentCustomer?.Id != customer.Id)
    {
        if (currentCustomer.AffiliateId != 0) { customer.AffiliateId = currentCustomer.AffiliateId; await _customerService.UpdateCustomerAsync(customer); }
        await _shoppingCartService.MigrateShoppingCartAsync(currentCustomer, customer, true);
        await _workContext.SetCurrentCustomerAsync(customer);
    }
    await _authenticationService.SignInAsync(customer, isPersist);
    // ... event publishing, activity log ...
    if (!string.IsNullOrEmpty(returnUrl) && _webHelper.CheckIsLocalUrl(returnUrl))
        return new RedirectResult(returnUrl);
    return new RedirectToRouteResult(NopRouteNames.General.HOMEPAGE, null);
}
```
**Why relevant**: This method returns `IActionResult` (HTTP redirect), which is **not suitable for JWT/API scenarios**. For token-based auth, this needs to return a token string instead. This is a key coupling point that must be broken during refactoring.