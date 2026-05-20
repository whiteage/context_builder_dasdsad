Now I have all the information needed. Let me compile the comprehensive context document.

---

## Project Summary

**Monica** is a personal relationship manager (PRM/CRM) built with **Laravel 12** (PHP 8.3+) and **Vue 3** (Inertia.js). It has **2,094 files** (1,656 PHP, 254 Vue, 40 JSON, 15 YAML). The architecture follows a **Domain-driven Laravel** pattern with services, controllers, view helpers, and models organized under `app/Domains/`.

## Architecture

The project uses a **Domain-driven Laravel** architecture with clear separation:

- **`app/Models/`** — Eloquent models (User, UserNotificationChannel, UserNotificationSent, etc.)
- **`app/Domains/{Domain}/Services/`** — Business logic services extending `BaseService` implementing `ServiceInterface`
- **`app/Domains/{Domain}/Web/Controllers/`** — HTTP controllers (Inertia.js + JSON responses)
- **`app/Domains/{Domain}/Web/ViewHelpers/`** — View helpers that transform models into DTO arrays for Vue
- **`app/Domains/{Domain}/Jobs/`** — Queueable jobs
- **`app/Notifications/`** — Laravel Notification classes
- **`app/Mail/`** — Mailable classes
- **`resources/js/Pages/`** — Vue pages and partials
- **`routes/web.php`** — All web routes

The notification system lives under `app/Domains/Settings/ManageNotificationChannels/`.

## Key Files

### 1. `app/Models/UserNotificationChannel.php`
The core model for notification channels. Has constants `TYPE_EMAIL = 'email'` and `TYPE_TELEGRAM = 'telegram'`. Fields: `user_id`, `type`, `label`, `content`, `active`, `verified_at`, `preferred_time`, `verification_token`, `fails`. Relationships: `user()`, `userNotificationSent()`, `contactReminders()`.

### 2. `app/Models/UserNotificationSent.php`
Logs sent notifications. Belongs to `UserNotificationChannel`. Fields include `sent_at`, `subject_line`, `payload`, `error`.

### 3. `app/Notifications/ReminderTriggered.php`
The central notification class. Uses `via($notifiable)` to switch on `$this->channel->type` — returns `['mail']` for email, `['telegram']` for Telegram. Has `toMail()` and `toTelegram()` methods, each logging to `UserNotificationSent` before sending.

### 4. `app/Domains/Settings/ManageNotificationChannels/Services/CreateUserNotificationChannel.php`
Service to create a new notification channel. Extends `BaseService`, implements `ServiceInterface`. Pattern: `rules()`, `permissions()`, `execute(array $data)` → `validate()` → `create()` → `verifyChannel()`.

### 5. `app/Domains/Settings/ManageNotificationChannels/Services/SendTestTelegramNotification.php`
Service to send a test Telegram notification. Uses `Notification::route('telegram', ...)->notify(new ReminderTriggered(...))`.

### 6. `app/Domains/Settings/ManageNotificationChannels/Services/SendTestEmail.php`
Service to send a test email notification. Uses `Mail::to(...)->send(new TestEmailSent(...))`.

### 7. `app/Domains/Settings/ManageNotificationChannels/Web/Controllers/NotificationsController.php`
Main controller: `index()` renders Inertia page, `store()` creates channel, `destroy()` deletes it.

### 8. `app/Domains/Settings/ManageNotificationChannels/Web/Controllers/TelegramWebhookController.php`
Handles Telegram bot webhook. Receives `/start {verification_token}`, looks up channel, saves chat ID, activates channel, schedules reminders.

### 9. `app/Domains/Settings/ManageNotificationChannels/Web/ViewHelpers/NotificationsIndexViewHelper.php`
View helper with `data(User $user)`, `dtoEmail(UserNotificationChannel $channel)`, `dtoTelegram(UserNotificationChannel $channel)` — transforms models into arrays for Vue.

### 10. `app/Domains/Settings/ManageNotificationChannels/Services/ScheduleAllContactRemindersForNotificationChannel.php`
Schedules all contact reminders for a notification channel by inserting into `contact_reminder_scheduled` pivot table.

### 11. `app/Domains/Settings/ManageNotificationChannels/Services/ToggleUserNotificationChannel.php`
Toggles active/inactive state and (re)schedules or deletes scheduled reminders.

### 12. `app/Domains/Settings/ManageNotificationChannels/Jobs/SendVerificationEmailChannel.php`
Queueable job that sends verification email for email-type channels.

### 13. `resources/js/Pages/Settings/Notifications/Partials/Telegram.vue`
Vue component for Telegram notification channel UI.

### 14. `resources/js/Pages/Settings/Notifications/Partials/Emails.vue`
Vue component for Email notification channel UI.

### 15. `routes/web.php` (lines 565-577)
Notification routes:
```
GET    /settings/notifications              → NotificationsController@index
POST   /settings/notifications              → NotificationsController@store
POST   /settings/notifications/telegram     → TelegramNotificationsController@store
GET    /settings/notifications/{id}/verify/{uuid} → NotificationsVerificationController@store
POST   /settings/notifications/{id}/test    → NotificationsTestController@store
PUT    /settings/notifications/{id}/toggle  → NotificationsToggleController@update
DELETE /settings/notifications/{id}         → NotificationsController@destroy
GET    /settings/notifications/{id}/logs    → NotificationsLogController@index
```

## Key Symbols

| Symbol | Type | File | Notes |
|--------|------|------|-------|
| `UserNotificationChannel` | Model | `app/Models/UserNotificationChannel.php` | Constants: `TYPE_EMAIL`, `TYPE_TELEGRAM` |
| `UserNotificationSent` | Model | `app/Models/UserNotificationSent.php` | Logs sent notifications |
| `ReminderTriggered` | Notification | `app/Notifications/ReminderTriggered.php` | Central notification, dispatches via `via()` switch |
| `BaseService` | Abstract | `app/Services/BaseService.php` | Base class with `rules()`, `permissions()`, `validateRules()`, permission checks |
| `ServiceInterface` | Interface | `app/Interfaces/ServiceInterface.php` | Contract for services |
| `CreateUserNotificationChannel` | Service | `app/Domains/.../Services/CreateUserNotificationChannel.php` | Creates channel, sends verification |
| `SendTestTelegramNotification` | Service | `app/Domains/.../Services/SendTestTelegramNotification.php` | Sends test Telegram via `ReminderTriggered` |
| `SendTestEmail` | Service | `app/Domains/.../Services/SendTestEmail.php` | Sends test email via `TestEmailSent` mailable |
| `NotificationsIndexViewHelper` | ViewHelper | `app/Domains/.../Web/ViewHelpers/NotificationsIndexViewHelper.php` | DTOs: `dtoEmail()`, `dtoTelegram()` |
| `TelegramWebhookController` | Controller | `app/Domains/.../Web/Controllers/TelegramWebhookController.php` | Handles `/start {token}` webhook |
| `SendVerificationEmailChannel` | Job | `app/Domains/.../Jobs/SendVerificationEmailChannel.php` | Queueable verification email |

## Dependencies

### Module-level
- `app/Domains/Settings/ManageNotificationChannels/` depends on:
  - `app/Models/` (UserNotificationChannel, UserNotificationSent)
  - `app/Services/BaseService.php`
  - `app/Interfaces/ServiceInterface.php`
  - `app/Notifications/ReminderTriggered.php`
  - `app/Mail/TestEmailSent.php`, `app/Mail/UserNotificationChannelEmailCreated.php`
  - `NotificationChannels\Telegram\TelegramMessage` (composer package `laravel-notification-channels/telegram`)

### File-level (key examples)
- `ReminderTriggered.php` imports: `UserNotificationChannel`, `UserNotificationSent`, `Carbon`, `MailMessage`, `Notification`, `TelegramMessage`
- `SendTestTelegramNotification.php` imports: `ServiceInterface`, `UserNotificationChannel`, `ReminderTriggered`, `BaseService`, `Notification` facade
- `CreateUserNotificationChannel.php` imports: `SendVerificationEmailChannel` (Job), `ServiceInterface`, `UserNotificationChannel`, `BaseService`, `Str`

## Conventions

### Naming Conventions
- **PascalCase** for all classes (e.g., `CreateUserNotificationChannel`, `ReminderTriggered`, `NotificationsIndexViewHelper`)
- **camelCase** for methods and properties (e.g., `execute()`, `validate()`, `verifyChannel()`)
- **snake_case** for database columns and route params (e.g., `user_notification_channel_id`, `verified_at`)
- **Suffix `Service`** for business logic services (e.g., `CreateUserNotificationChannel`, `SendTestTelegramNotification`)
- **Suffix `Controller`** for HTTP controllers (e.g., `NotificationsController`, `TelegramWebhookController`)
- **Suffix `ViewHelper`** for view helpers (e.g., `NotificationsIndexViewHelper`)
- **Suffix `Job`** for queueable jobs (e.g., `SendVerificationEmailChannel`)
- **No prefix `I`** for interfaces — `ServiceInterface` uses suffix `Interface`
- **Constants** are `UPPER_SNAKE_CASE` (e.g., `TYPE_EMAIL`, `TYPE_TELEGRAM`)

### Architectural Patterns
- **Service Layer Pattern**: All business logic in Services extending `BaseService implements ServiceInterface`. Each service has `rules()`, `permissions()`, and `execute(array $data)`.
- **DTO Pattern via ViewHelpers**: View helpers have static `data()` and `dto*()` methods that return arrays for Inertia/Vue.
- **Laravel Notification System**: Single `ReminderTriggered` notification class handles multiple channels via `via()` switch.
- **Repository-less**: Direct Eloquent usage in services (no repository pattern).
- **Queueable Jobs**: Verification emails dispatched via `SendVerificationEmailChannel::dispatch(...)->onQueue('high')`.
- **Route-model binding**: Controllers receive IDs and use `findOrFail()`.

### Style Conventions
- **Async**: Jobs dispatched to queue (`onQueue('high')`)
- **Error handling**: `ValidationException` for validation errors, generic `Exception` for type mismatches
- **Validation**: `validateRules($this->data)` from `BaseService` + custom checks
- **Permissions**: Declared as array in `permissions()` method, validated by `BaseService`
- **Localization**: `trans()` helper used throughout
- **Type hints**: PHP 8 typed properties (`private array $data`, `private UserNotificationChannel $userNotificationChannel`)
- **Return types**: `: void`, `: array`, `: UserNotificationChannel`

## Similar Implementations

The notification system has two channel implementations that follow identical patterns:

1. **Email channel** — Files:
   - `SendTestEmail.php` (Service)
   - `TestEmailSent.php` (Mailable)
   - `UserNotificationChannelEmailCreated.php` (Mailable for verification)
   - `SendVerificationEmailChannel.php` (Job)
   - `Emails.vue` (Vue component)
   - `dtoEmail()` in `NotificationsIndexViewHelper.php`

2. **Telegram channel** — Files:
   - `SendTestTelegramNotification.php` (Service)
   - `TelegramWebhookController.php` (Webhook handler)
   - `TelegramNotificationsController.php` (Store controller)
   - `Telegram.vue` (Vue component)
   - `dtoTelegram()` in `NotificationsIndexViewHelper.php`

Both follow the same pattern: a Service to create the channel, a Service to send a test notification, a ViewHelper DTO, a Vue partial, and the central `ReminderTriggered` notification class handles the actual delivery.

## Context for the Task

### What you need to add SMS notification support

You need to add a new notification channel type (`TYPE_SMS = 'sms'`) following the exact patterns of the existing Email and Telegram channels. Here is the complete pattern:

### 1. Model — Add a new type constant

In `app/Models/UserNotificationChannel.php`, add:
```php
public const TYPE_SMS = 'sms';
```

### 2. Notification routing — Add SMS case to `ReminderTriggered`

In `app/Notifications/ReminderTriggered.php`, the `via()` method switches on channel type:
```php
public function via($notifiable)
{
    switch ($this->channel->type) {
        case UserNotificationChannel::TYPE_EMAIL:
            return ['mail'];
        case UserNotificationChannel::TYPE_TELEGRAM:
            return ['telegram'];
        // Add: case UserNotificationChannel::TYPE_SMS: return ['sms'];
    }
    return [];
}
```

Add a `toSms($notifiable)` method following the same pattern as `toTelegram()`:
```php
public function toSms($notifiable)
{
    UserNotificationSent::create([
        'user_notification_channel_id' => $this->channel->id,
        'sent_at' => Carbon::now(),
        'subject_line' => $this->content,
    ]);
    // Use an SMS notification channel package
}
```

### 3. Service — Create SMS channel (follow `CreateUserNotificationChannel`)

```php
class CreateUserNotificationChannel extends BaseService implements ServiceInterface
{
    public function rules(): array { /* account_id, author_id, label, type, content, preferred_time */ }
    public function permissions(): array { return ['author_must_belong_to_account']; }
    public function execute(array $data): UserNotificationChannel
    {
        $this->data = $data;
        $this->validate();
        $this->create();
        $this->verifyChannel(); // optional for SMS
        return $this->userNotificationChannel;
    }
}
```

### 4. Service — Send test SMS (follow `SendTestTelegramNotification`)

```php
class SendTestSmsNotification extends BaseService implements ServiceInterface
{
    public function execute(array $data): UserNotificationChannel
    {
        $this->validate();
        $this->send();
        return $this->userNotificationChannel;
    }
    private function send(): void
    {
        Notification::route('sms', $this->userNotificationChannel->content)
            ->notify((new ReminderTriggered($this->userNotificationChannel, $content, 'Test')));
    }
}
```

### 5. ViewHelper — Add `dtoSms()` method

In `NotificationsIndexViewHelper.php`, add a `dtoSms()` method following `dtoEmail()`/`dtoTelegram()` pattern, and include SMS in the `data()` method.

### 6. Controller — Add SMS routes

In `routes/web.php` under the notifications group:
```php
Route::post('sms', [SmsNotificationsController::class, 'store'])->name('sms.store');
```

### 7. Vue — Add `Sms.vue` partial

Follow the pattern in `Telegram.vue` — form to add phone number, display channel info, test/toggle/delete buttons.

### 8. Composer — Add SMS notification package

Add a package like `laravel-notification-channels/plivo` or `laravel-notification-channels/twilio` to `composer.json`.

### 9. Config — Add SMS credentials

Add SMS provider config in `config/services.php`:
```php
'sms' => [
    'from' => env('SMS_FROM'),
    // provider-specific keys
],
```

### Key code snippets showing the pattern

**The central notification dispatcher** (`app/Notifications/ReminderTriggered.php`):
```php
public function via($notifiable)
{
    switch ($this->channel->type) {
        case UserNotificationChannel::TYPE_EMAIL:
            return ['mail'];
        case UserNotificationChannel::TYPE_TELEGRAM:
            return ['telegram'];
    }
    return [];
}
```

**The test notification service pattern** (`app/Domains/Settings/ManageNotificationChannels/Services/SendTestTelegramNotification.php`):
```php
private function send(): void
{
    $content = trans('This is a test notification for :name', ['name' => $this->author->name]);
    Notification::route('telegram', $this->userNotificationChannel->content)
        ->notify((new ReminderTriggered($this->userNotificationChannel, $content, 'Test'))
            ->locale($this->userNotificationChannel->user->locale));
}
```

**The ViewHelper DTO pattern** (`app/Domains/Settings/ManageNotificationChannels/Web/ViewHelpers/NotificationsIndexViewHelper.php`):
```php
public static function dtoTelegram(UserNotificationChannel $channel): array
{
    return [
        'id' => $channel->id,
        'type' => $channel->type,
        'active' => $channel->active,
        'verified_at' => $channel->verified_at ? $channel->verified_at->format('Y-m-d H:i:s') : null,
        'preferred_time' => $channel->preferred_time->format('H:i'),
        'url' => [
            'send_test' => route('settings.notifications.test.store', ['notification' => $channel->id]),
            'toggle' => route('settings.notifications.toggle.update', ['notification' => $channel->id]),
            'logs' => route('settings.notifications.log.index', ['notification' => $channel->id]),
            'destroy' => route('settings.notifications.destroy', ['notification' => $channel->id]),
        ],
    ];
}
```

### Files you need to create/modify

**New files to create:**
1. `app/Domains/Settings/ManageNotificationChannels/Services/SendTestSmsNotification.php` — Test SMS service
2. `app/Domains/Settings/ManageNotificationChannels/Web/Controllers/SmsNotificationsController.php` — SMS controller
3. `resources/js/Pages/Settings/Notifications/Partials/Sms.vue` — Vue component

**Files to modify:**
1. `app/Models/UserNotificationChannel.php` — Add `TYPE_SMS = 'sms'` constant
2. `app/Notifications/ReminderTriggered.php` — Add `'sms'` case in `via()`, add `toSms()` method
3. `app/Domains/Settings/ManageNotificationChannels/Web/ViewHelpers/NotificationsIndexViewHelper.php` — Add `dtoSms()` and include in `data()`
4. `app/Domains/Settings/ManageNotificationChannels/Web/Controllers/NotificationsTestController.php` — Add SMS test case
5. `routes/web.php` — Add SMS route
6. `config/services.php` — Add SMS provider config
7. `composer.json` — Add SMS notification package dependency