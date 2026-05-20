I now have comprehensive data. Here is the architecture analysis.

---

## 1. PROJECT SUMMARY

RustDesk is an open-source remote desktop application written primarily in **Rust** (backend) and **Dart/Flutter** (cross-platform UI). It has 928 files total: ~580 Rust classes, ~123 Dart files. The Rust backend handles networking, encoding, input simulation, screen capture, and service management. The Flutter frontend provides desktop and mobile UIs. The project also includes C++ (Windows-specific), platform-specific code (macOS, Linux, Android), and a plugin framework.

## 2. ARCHITECTURE

RustDesk follows a **layered architecture with a client-server split**, connected via an **IPC bridge** between Rust and Flutter.

```
[Flutter UI Layer]  -- Dart pages, widgets, models
       |
[FFI Bridge]        -- flutter_ffi.rs (Rust) <-> FFI (Dart)
       |
[Rust Core Layer]   -- client.rs, server.rs, rendezvous_mediator.rs
       |
[Service Layer]     -- audio_service, display_service, input_service,
    |                  clipboard_service, printer_service, terminal_service
[IPC Layer]         -- ipc.rs (inter-process communication)
       |
[Platform Layer]    -- platform/ (Windows, Linux, macOS, Android specifics)
```

**Key layers and their responsibilities:**

- **Flutter UI** (`flutter/lib/`): Pages (desktop/mobile), widgets, models (state management via `ChangeNotifier`/`Obx`), plugin UI manager. Organized by platform: `desktop/pages/`, `mobile/pages/`, `common/widgets/`.
- **FFI Bridge** (`src/flutter_ffi.rs`): ~1396 signatures — the main Rust-to-Flutter interface. Exposes `session_start`, `session_login`, `session_send2fa`, `start_global_event_stream`, etc. Uses `StreamSink` for event streaming.
- **Rust Core** (`src/`): `client.rs` (outgoing connections), `server.rs` (incoming connections), `rendezvous_mediator.rs` (NAT traversal, rendezvous server), `core_main.rs` (entry point, CLI parsing).
- **Service Layer** (`src/server/`): Each service (`audio_service`, `display_service`, `input_service`, `clipboard_service`, `printer_service`, `terminal_service`) implements a common `Service` trait with `name()`, `on_subscribe()`, `on_unsubscribe()`, `send()`, `init()`, `run()`.
- **IPC Layer** (`src/ipc.rs`): Defines `Data` enum with ~60+ variants for all inter-process messages (keyboard, mouse, clipboard, config, plugin, etc.). Used for communication between service process and UI process.
- **Plugin System** (`src/plugin/`, `flutter/lib/plugin/`): Dynamic plugin loading via shared libraries. Rust side handles IPC and native callbacks; Flutter side handles UI registration and event routing.

**Dependency flow:** Flutter → FFI → Rust Core → Services/IPC → Platform. Data flows upward via event streams.

## 3. RELATED FILES

| File | Purpose | Relevance |
|------|---------|-----------|
| `src/lib.rs` | Rust crate root — re-exports all modules | Shows module organization and conditional compilation |
| `src/server.rs` | Server-side connection handler — accepts incoming connections, manages services | Core of the "server" (host) side architecture |
| `src/client.rs` | Client-side connection handler — initiates outgoing connections | Core of the "client" (viewer) side architecture |
| `src/flutter_ffi.rs` | FFI bridge — exposes Rust functions to Flutter | Main integration point between Rust and Flutter |
| `src/server/service.rs` | `Service` trait and `ServiceInner` — base for all services | Defines the service abstraction pattern |
| `src/server/connection.rs` | Per-connection state machine — handles auth, encryption, message routing | Core connection lifecycle |
| `src/server/audio_service.rs` | Audio capture and streaming service | Example of a service implementation |
| `src/server/display_service.rs` | Display/screen capture service | Example of a service implementation |
| `src/server/input_service.rs` | Input simulation service (keyboard/mouse) | Example of a service implementation |
| `src/ipc.rs` | IPC message definitions and transport | Defines all inter-process communication |
| `src/rendezvous_mediator.rs` | NAT traversal, rendezvous server communication | Network layer |
| `src/core_main.rs` | Application entry point — CLI parsing, service startup | Orchestration |
| `flutter/lib/main.dart` | Flutter app entry — multi-window support, platform init | Flutter app bootstrap |
| `flutter/lib/common.dart` | Shared Flutter widgets, themes, constants | UI foundation |
| `flutter/lib/models/model.dart` | `FfiModel`, `PeerInfo`, connection state models | Flutter state management |
| `flutter/lib/plugin/handlers.dart` | Plugin event handlers (native callbacks) | Plugin system integration |
| `flutter/lib/plugin/manager.dart` | Plugin lifecycle management (install, list, events) | Plugin system |

## 4. DEPENDENCY GRAPH

**Module-level dependencies (from `src/lib.rs`):**

```
lib.rs
  ├── keyboard
  ├── platform (conditional: not android/ios)
  ├── server (conditional: not ios)
  ├── client
  ├── lan
  ├── rendezvous_mediator (conditional: not ios)
  ├── common
  ├── ipc (conditional: not ios)
  ├── ui (conditional: not android/ios/cli/flutter)
  ├── flutter (conditional: flutter feature)
  ├── flutter_ffi (conditional: flutter feature)
  ├── plugin
  ├── clipboard
  ├── clipboard_file
  ├── port_forward
  ├── privacy_mode
  ├── virtual_display_manager
  ├── auth_2fa
  ├── naming
  ├── service
  ├── tray
  ├── updater
  ├── custom_server
  ├── hbbs_http
  ├── kcp_stream
  └── lang
```

**Server module dependencies (`src/server/`):**

```
server.rs
  ├── connection.rs (per-connection state machine)
  ├── service.rs (Service trait)
  ├── audio_service.rs (implements Service)
  ├── display_service.rs (implements Service)
  ├── input_service.rs (implements Service)
  ├── clipboard_service.rs (implements Service)
  ├── printer_service.rs (implements Service)
  ├── terminal_service.rs (implements Service)
  ├── video_service.rs
  ├── video_qos.rs
  ├── rdp_input.rs
  ├── uinput.rs
  ├── wayland.rs
  ├── dbus.rs
  ├── login_failure_check.rs
  ├── portable_service.rs
  └── terminal_helper.rs
```

**Flutter module dependencies:**

```
main.dart
  ├── common.dart (themes, widgets, FFI bindings)
  ├── consts.dart
  ├── desktop/pages/ (desktop_home_page, remote_page, server_page, etc.)
  ├── mobile/pages/ (connection_page, remote_page, server_page, etc.)
  ├── models/ (model.dart, state_model.dart, server_model.dart, etc.)
  ├── plugin/ (handlers.dart, manager.dart, model.dart, event.dart)
  └── utils/ (event_loop, http_service, multi_window_manager, etc.)
```

**Call graph (key flow):**

```
Flutter main.dart
  → initEnv() → gFFI.initialize() [FFI to Rust]
  → runMainApp() → startService() [Rust server start]
  
Remote connection flow:
  RemotePage.initState()
    → session_start() [FFI to flutter_ffi.rs]
      → client::start() [src/client.rs]
        → rendezvous_mediator [NAT traversal]
        → io_loop [src/client/io_loop.rs]
          → handle_msg_from_peer()
          → handle_msg_from_ui()

Server (host) flow:
  server::accept_connection() [src/server.rs]
    → connection::start() [src/server/connection.rs]
      → services (audio, display, input, clipboard)
```

## 5. CONVENTIONS

**Naming conventions (from sample_signatures):**

1. **PascalCase for all types** — classes, enums, traits: `FfiModel`, `PeerInfo`, `ServerModel`, `GestureState`, `DesktopTabType`, `SvcStatus`
2. **`_` prefix for private classes** in Dart: `_RemotePageState`, `_DesktopSettingPageState`, `_FileManagerPageState`, `_CmControlPanel`, `_Tab`
3. **`Service` suffix for service implementations**: `audio_service`, `clipboard_service`, `display_service`, `input_service`, `printer_service`, `terminal_service` (Rust modules)
4. **`Model` suffix for state models** in Dart: `FfiModel`, `ServerModel`, `ChatModel`, `FileModel`, `InputModel`, `StateModel`, `PeerModel`
5. **`Page` suffix for page widgets** in Dart: `RemotePage`, `ServerPage`, `DesktopHomePage`, `FileManagerPage`, `PortForwardPage`
6. **`_service` snake_case for Rust service modules**: `audio_service.rs`, `clipboard_service.rs`, `display_service.rs`, `input_service.rs`
7. **`_model` suffix for Dart model files**: `state_model.dart`, `server_model.dart`, `peer_model.dart`, `chat_model.dart`
8. **`_page` suffix for Dart page files**: `remote_page.dart`, `server_page.dart`, `desktop_home_page.dart`
9. **`_widget` suffix for Dart widget files**: `tabbar_widget.dart`, `popup_menu.dart`, `peer_card.dart`
10. **`k` prefix for constants**: `kOptionVerificationMethod`, `kOptionApproveMode`, `kWindowBorderWidth`, `kAppTypeMain`
11. **`NAME` constant for service names**: `NAME.to_owned()` pattern in `audio_service`, `clipboard_service`, `display_service`, `input_service`
12. **`ffi` prefix for FFI model references**: `gFFI`, `_ffi.ffiModel`, `_ffi.sessionId`

**Architectural patterns:**

- **Service trait pattern**: All services implement `Service` trait with `name()`, `on_subscribe()`, `on_unsubscribe()`, `send()`, `init()`, `run()` — found in `src/server/service.rs`
- **Publisher-Subscriber**: Services use `ServiceInner` with `subscribe`/`unsubscribe` pattern for connection management
- **IPC enum pattern**: All IPC messages are variants of a single `Data` enum in `src/ipc.rs` (~60+ variants)
- **FFI bridge pattern**: `flutter_ffi.rs` exposes `pub fn` functions that are called from Dart via `flutter_rust_bridge`
- **State management**: Flutter uses `ChangeNotifier` + `Obx` (GetX reactive) for state — `ServerModel` extends `ChangeNotifier`
- **Multi-window**: Flutter supports separate windows for remote, file transfer, terminal, port forwarding via `runMultiWindow()`
- **Conditional compilation**: Heavy use of `#[cfg(...)]` for platform-specific code (android, ios, windows, linux, macos)

**Style conventions:**

- **Async Rust**: `async fn` throughout, `tokio::spawn` for concurrency
- **Error handling**: `allow_err!` macro, `Result` returns, `msgbox()` for user-facing errors
- **Dart**: `override` annotations, `Key? key` parameter pattern, `const` constructors where possible
- **Plugin system**: Native callbacks via `Pointer<Void>` function pointers, JSON serialization for event data

## 6. SIMILAR IMPLEMENTATIONS

| Class | File | Similarity |
|-------|------|------------|
| `AudioService` | `src/server/audio_service.rs` | Implements `Service` trait — same pattern as `DisplayService`, `InputService`, `ClipboardService`, `PrinterService` |
| `DisplayService` | `src/server/display_service.rs` | Implements `Service` trait — same `new(NAME.to_owned())`, `run(&svc.clone())` pattern |
| `InputService` | `src/server/input_service.rs` | Implements `Service` trait — same subscription pattern, `new_cursor()`, `new_pos()` factory methods |
| `ClipboardService` | `src/server/clipboard_service.rs` | Implements `Service` trait — same `run(sp: EmptyExtraFieldService)` pattern |
| `ServerModel` | `flutter/lib/models/server_model.dart` | Extends `ChangeNotifier` — same pattern as `FfiModel`, `ChatModel`, `FileModel`, `PeerModel` |
| `RemotePage` | `flutter/lib/desktop/pages/remote_page.dart` | `StatefulWidget` with `_RemotePageState` — same pattern as `ServerPage`, `FileManagerPage`, `PortForwardPage` |

## 7. TASK CONTEXT

RustDesk's architecture is a **layered client-server remote desktop** with a Rust backend and Flutter frontend. The key architectural insight is the **Service trait pattern** in `src/server/service.rs` — all server-side capabilities (audio, display, input, clipboard, printer, terminal) are implemented as pluggable services that subscribe to connections. The **IPC layer** (`src/ipc.rs`) is the backbone for all inter-process communication, using a single `Data` enum with ~60+ message variants. The **FFI bridge** (`src/flutter_ffi.rs`) exposes Rust functions to Flutter via `flutter_rust_bridge`, with `StreamSink` for event streaming.

For any task involving the server side, look at `src/server/service.rs` (the trait), `src/server/connection.rs` (connection lifecycle), and the specific service implementation. For the client side, look at `src/client.rs` and `src/client/io_loop.rs`. For Flutter integration, look at `src/flutter_ffi.rs` and the corresponding Dart models in `flutter/lib/models/`. The plugin system spans both `src/plugin/` (Rust) and `flutter/lib/plugin/` (Dart).

## 8. RELEVANT CODE SNIPPETS

**Service trait definition** (`src/server/service.rs`):
```rust
// Lines ~1-20: The Service trait that all services implement
fn name(&self) -> &str;
fn on_subscribe(&self, sub: ConnInner);
fn on_unsubscribe(&self, id: i32);
fn is_subed(&self, id: i32) -> bool;
fn join(&self);
fn get_option(&self, opt: &str) -> Option<String>;
fn set_option(&self, opt: &str, val: &str);
fn ok(&self) -> bool;
fn id(&self) -> i32;
fn send(&mut self, msg: Arc<Message>);
fn reset(&mut self);
fn init(&mut self);
```

**Service registration pattern** (`src/server.rs`):
```rust
// Lines ~15-30: Services are registered in the server
add_service(Box::new(audio_service::new()));
add_service(Box::new(display_service::new()));
add_service(Box::new(clipboard_service::new(clipboard_service::NAME.to_owned())));
add_service(Box::new(input_service::new_cursor()));
add_service(Box::new(input_service::new_pos()));
add_service(Box::new(printer_service::new(printer_service::NAME.to_owned())));
```

**IPC Data enum** (`src/ipc.rs`):
```rust
// Lines ~1-30: All IPC messages as enum variants
pub enum Data {
    SendConfirm(Vec<u8>),
    Sequence(String),
    KeyDown(enigo::Key), KeyUp(enigo::Key), KeyClick(enigo::Key),
    MoveTo(i32, i32), MoveRelative(i32, i32),
    Down(enigo::MouseButton), Up(enigo::MouseButton),
    Ping, Pong, AuthToken(String), AuthResult(bool),
    Config((String, Option<String>)),
    Plugin(Plugin),
    // ... ~60+ variants total
}
```

**FFI bridge pattern** (`src/flutter_ffi.rs`):
```rust
// Lines ~1-15: Functions exposed to Flutter via flutter_rust_bridge
pub fn session_start(events2ui: StreamSink<EventToUI>, session_id: SessionID, id: String) {
    session_start_(&session_id, &id, events2ui);
}
pub fn session_login(session_id: SessionID, os_username: String, os_password: ***, password: ***, remember: bool) {
    if let Some(session) = get_session_by_session_id(&session_id) {
        session.login(os_username, os_password, password, remember);
    }
}
```

**Flutter multi-window entry** (`flutter/lib/main.dart`):
```dart
// Lines ~30-50: Multi-window support
if (args.isNotEmpty && args.first == 'multi_window') {
    parse(args[1]); setWindowId(kWindowId!);
    switch (kWindowType) {
        case kAppTypeDesktopRemote: runMultiWindow(argument, kAppTypeDesktopRemote);
        case kAppTypeDesktopFileTransfer: runMultiWindow(argument, kAppTypeDesktopFileTransfer);
        case kAppTypeDesktopTerminal: runMultiWindow(argument, kAppTypeDesktopTerminal);
    }
}
```