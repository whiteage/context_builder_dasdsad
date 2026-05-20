I now have comprehensive information to produce the architecture analysis.

---

## Architecture Analysis: FPS Sample

### 1. PROJECT SUMMARY

**FPS Sample** is a first-person multiplayer shooter reference project by Unity Technologies (2018.3). It showcases Unity's HD Render Pipeline (HDRP), Entity-Component System (ECS) in hybrid mode, and a custom network transport layer. The project has **12,727 files** total — 1,513 C# source files, 199 HLSL shaders, 103 shader files, and 7,781 YAML (Unity asset meta/prefab/scene files). It targets Windows (client + server) and Linux (headless server only). The project is no longer actively maintained but serves as a learning resource.

### 2. ARCHITECTURE

**Architecture type: Hybrid ECS + GameObject (Mixed-Mode) with Client/Server split**

The architecture has four main layers:

| Layer | Path | Responsibility |
|---|---|---|
| **Game Loop** | `Assets/Scripts/Game/Main/` | Entry points: `Game.cs` (MonoBehaviour main loop), `ClientGameLoop`, `ServerGameLoop`, `PreviewGameLoop`. Each loop owns a `GameWorld` and orchestrates update order. |
| **Modules** | `Assets/Scripts/Game/Modules/` | Feature groupings (Character, Player, Projectile, HitCollision, Grenade, Effect, Item, Ragdoll, ReplicatedEntity, SpectatorCam). Each module has `*ModuleClient`, `*ModuleServer`, `*ModuleShared` variants. |
| **Systems** | `Assets/Scripts/Game/Systems/` | Cross-cutting systems (GameMode, Damage, DamageArea, Chat, Movable, PlayerCamera, Teleporter, etc.) |
| **Networking** | `Assets/Scripts/Networking/` | Custom transport layer: `NetworkClient`, `NetworkServer`, `NetworkConnection`, `NetworkEvent`, `NetworkSchema`, `BitInputStream/OutputStream`, delta compression, prediction. |
| **ECS Infrastructure** | `Assets/Scripts/ECS/` | `BaseComponentDataSystem` — generic base for ECS component systems with 1-4 component type parameters. |
| **Core/Utils** | `Assets/Scripts/Core/`, `Assets/Scripts/Utils/` | `GameDebug`, `CircularList`, `DebugDraw`, `ConversionUtility`, `BundledResource` management. |
| **Audio** | `Assets/Scripts/Audio/` | `SoundSystem`, `SoundBank`, `SoundDef`, `AmbientSoundEmitter`. |
| **Frontend** | `Assets/Scripts/Game/Frontend/` | `ClientFrontend` — UI/menu management. |

**Key architectural patterns:**
- **Client/Server split**: Every module has `*Client` and `*Server` variants. The `PreviewGameLoop` combines both for editor play mode.
- **GameLoop pattern**: `IGameLoop` interface. The `Game` class can swap game loops at runtime.
- **Module pattern**: Modules own a collection of ECS systems, grouped into update phases (Spawn, Despawn, AbilityRequest, MovementStart, MovementResolve, AbilityStart, AbilityResolve, Interpolate, LateUpdate).
- **ECS mixed-mode**: Systems extend `BaseComponentDataSystem<T1, T2, ...>` (generic on component types). Systems are manually updated (not auto-run) for precise update order control.
- **ReplicatedEntity pattern**: GameObjects with `ReplicatedEntity` component + `INetworkSerializable` components for data sync. ECS entities use `ReplicatedEntityFactory` ScriptableObjects.
- **ConfigVar system**: Console variables with `[ConfigVar]` attribute for runtime tuning.

### 3. RELATED FILES

| File | Entity Type | Purpose & Relevance |
|---|---|---|
| `Assets/Scripts/Game/Main/Game.cs` | System (main loop) | Entry point MonoBehaviour. Defines `Game.Update`, `Game.FixedUpdate`, `Game.LateUpdate`. Manages game loop switching, input, audio, console. |
| `Assets/Scripts/Game/Main/ClientGameLoop.cs` | System | Client-side game loop. Creates `ClientGameWorld` with all client modules. Orchestrates update order: HandleTime → HandleCommandReset → UpdateControlledEntityFlags → HandleProjectileRequests → HandleSpawns → HandleSpawning → HandleControlledEntityChanged. |
| `Assets/Scripts/Game/Main/ServerGameLoop.cs` | System | Server-side game loop. Creates `ServerGameWorld` with all server modules. Orchestrates `ServerTickUpdate`: HandleClientCommands → HandleSpawnRequests → HandleRequests → Update → HandleSpawns → HandleSpawning. |
| `Assets/Scripts/ECS/BaseComponentDataSystem.cs` | System (base class) | Generic base for all ECS systems. Provides `OnCreateManager` (builds component group from type params), `OnUpdate` (iterates entities, calls abstract `Update`). Supports 1-4 component type parameters + `ExtraComponentRequirements`. |
| `Assets/Scripts/Game/Entity/GameWorld.cs` | Entity (world manager) | Wraps Unity ECS `World` + `EntityManager`. Manages spawning (`SpawnInternal`), despawning (`RequestDespawn`/`ProcessDespawns`), scene entity registration. |
| `Assets/Scripts/Game/Modules/Character/CharacterModuleClient.cs` | Module (client) | Client character module. Creates spawn/despawn systems, ability request/movement/ability systems in ordered groups. Demonstrates the module pattern with `Interpolate()`, `UpdatePresentation()`, `LateUpdate()`, `CameraUpdate()` phases. |
| `Assets/Scripts/Game/Modules/Character/CharacterModuleServer.cs` | Module (server) | Server character module. Handles `CharacterSpawnRequest`, `CharacterDespawnRequest`, damage processing. Shows the server-side module pattern. |
| `Assets/Scripts/Game/Modules/Character/CharacterModuleShared.cs` | Module (shared) | Base class for character modules. Defines `SystemCollection` groups: `m_HandleSpawnSystems`, `m_HandleDespawnSystems`, `m_AbilityRequestUpdateSystems`, `m_MovementStartSystems`, `m_MovementResolveSystems`, `m_AbilityStartSystems`, `m_AbilityResolveSystems`. |
| `Assets/Scripts/Networking/NetworkServer.cs` | System | Custom network server. Manages connections, entity snapshots, command processing, event queuing. Uses `NetworkSchema` for data definition. |
| `Assets/Scripts/Networking/NetworkClient.cs` | System | Custom network client. Manages connection, command queuing, snapshot consumption, event processing. |
| `Assets/Scripts/Game/Frontend/ClientFrontend.cs` | System | UI frontend. Manages menu panels, chat, scoreboard. Runs as an ECS system (`ClientFrontendUpdate`). |
| `Assets/Scripts/Game/Modules/Character/CharacterSystemShared.cs` | System | Shared character systems: `HandleCharacterSpawn`, `HandleCharacterDespawn`, `UpdateTeleportation`, `UpdateCharPresentationState`, `GroundTest`. |

### 4. DEPENDENCY GRAPH

**Module-level dependencies (top-level directories):**

```
Game.Main (Game.cs, ClientGameLoop, ServerGameLoop)
  ├── Game.Entity (GameWorld)
  ├── Game.Modules.* (Character, Player, Projectile, etc.)
  ├── Game.Systems.* (GameMode, Damage, Chat, etc.)
  ├── Game.Frontend (ClientFrontend)
  ├── Networking (NetworkClient, NetworkServer)
  ├── ECS (BaseComponentDataSystem)
  ├── Audio (SoundSystem)
  └── Utils (BundledResource, DebugDraw, etc.)
```

**File-level dependency chains (key paths):**

- `Game.cs` → creates `IGameLoop` instances → `ClientGameLoop`/`ServerGameLoop` → create `GameWorld` + modules
- `ClientGameLoop` → `ClientGameWorld` → `CharacterModuleClient(world, resourceSystem)`, `ProjectileModuleClient(world, resourceSystem)`, etc.
- `ServerGameLoop` → `ServerGameWorld` → `CharacterModuleServer(world, resourceSystem)`, `ProjectileModuleServer(world, resourceSystem)`, etc.
- `CharacterModuleClient` → `CharacterModuleShared` (base) → `BaseComponentDataSystem` (ECS base)
- `NetworkServer` → `NetworkConnection`, `NetworkEvent`, `NetworkSchema`, `BitOutputStream`
- `NetworkClient` → `NetworkConnection`, `NetworkEvent`, `NetworkSchema`, `BitInputStream`

**Call graph (update flow):**

```
Game.Update()
  → ClientGameLoop.Update(frameDuration)
    → HandleTime()
    → ResolveReferenceFromLocalPlayerToPlayer()
    → HandleCommandReset()
    → UpdateControlledEntityFlags()
    → HandleProjectileRequests()
    → CharacterModuleClient.Update() [AbilityRequest → MovementStart → MovementResolve → AbilityStart → AbilityResolve]
    → HandleSpawns() / HandleSpawning()
    → CharacterModuleClient.Interpolate()
    → CharacterModuleClient.UpdatePresentation()
    → CharacterModuleClient.LateUpdate()
    → CharacterModuleClient.CameraUpdate()
```

### 5. CONVENTIONS

**Naming conventions (from sample_signatures):**
1. **PascalCase** for all classes, structs, methods, properties.
2. **`I` prefix for interfaces**: `ISoundSystem`, `INetworkDriver`, `IConverter`, `IGameLoop`.
3. **`*System` suffix for ECS systems**: `HandleCharacterSpawn`, `GroundTest`, `UpdateTeleportation`, `HandleDamage`, `HandleClientProjectileRequests`, `HandleHitCollisionDespawning`.
4. **`*ModuleClient` / `*ModuleServer` / `*ModuleShared` suffix for modules**: `CharacterModuleClient`, `CharacterModuleServer`, `CharacterModuleShared`, `PlayerModuleClient`, `ProjectileModuleClient`.
5. **`*Data` suffix for ECS component data structs**: `CharacterPredictedData`, `CharacterInterpolatedData`, `HealthStateData`, `HitCollisionOwnerData`.
6. **`*Component` suffix for ECS component types**: `UserCommandComponent`, `CharacterReplicated`, `ReplicatedComponent`.
7. **`*Request` suffix for spawn/despawn request components**: `CharacterSpawnRequest`, `CharacterDespawnRequest`.
8. **`*Settings` suffix for ScriptableObject configs**: `CharacterModuleSettings`, `PlayerModuleSettings`, `ProjectileModuleSettings`.
9. **`*Registry` suffix for asset registries**: `HeroTypeRegistry`, `CharacterTypeRegistry`, `ReplicatedEntityRegistry`.
10. **`*Definition` suffix for ScriptableObject type definitions**: `CharacterTypeDefinition`, `HeroTypeAsset`.
11. **`*Factory` suffix for entity factories**: `GrenadeEntityFactory`, `ProjectileEntityFactory`, `ClientProjectileFactory`.
12. **`m_` prefix for private member fields**: `m_GameWorld`, `m_NetworkClient`, `m_HandleSpawnSystems`, `m_DespawnRequests`.
13. **`*GameLoop` suffix for game loop implementations**: `ClientGameLoop`, `ServerGameLoop`, `PreviewGameLoop`.
14. **`*Event` suffix for event types**: `NetworkEvent`, `CharacterEvents`, `GameNetworkEvents`.

**Architectural patterns:**
- **Module pattern**: Each feature is a module with `*ModuleClient`/`*ModuleServer`/`*ModuleShared` classes. Modules own `SystemCollection` groups for ordered system execution.
- **ECS Component System pattern**: Systems extend `BaseComponentDataSystem<T1, T2, ...>` (generic on component types). Systems are manually updated via `Update()` calls.
- **Client/Server split**: Every module has separate client and server implementations. Shared logic in `*ModuleShared`.
- **ConfigVar pattern**: Console variables declared as `static ConfigVar` fields with `[ConfigVar(Name, DefaultValue, Description, Flags)]` attribute.
- **BundledResource pattern**: Assets loaded via `BundledResourceManager` using GUID-based `GetSingleAssetResource()`.

**Style conventions:**
- Manual ECS system updates (not auto-run) for precise update order control.
- `BeginSample`/`EndSample` profiling markers around update methods.
- `Assert` for debug validation throughout.
- `ConfigVar` for all tunable parameters (tickrate, FOV, mouse sensitivity, debug flags).

### 6. SIMILAR IMPLEMENTATIONS

| Class | File | Why Similar |
|---|---|---|
| `CharacterModuleClient` | `Assets/Scripts/Game/Modules/Character/CharacterModuleClient.cs` | Module pattern — client variant. Same pattern as `PlayerModuleClient`, `ProjectileModuleClient`, `EffectModuleClient`, `ReplicatedEntityModuleClient`, `SpectatorCamModuleClient`. |
| `CharacterModuleServer` | `Assets/Scripts/Game/Modules/Character/CharacterModuleServer.cs` | Module pattern — server variant. Same pattern as `PlayerModuleServer`, `ProjectileModuleServer`, `ReplicatedEntityModuleServer`, `SpectatorCamModuleServer`. |
| `CharacterModuleShared` | `Assets/Scripts/Game/Modules/Character/CharacterModuleShared.cs` | Module pattern — shared base. Defines `SystemCollection` groups. Same pattern used implicitly by all modules. |
| `HandleCharacterSpawn` | `Assets/Scripts/Game/Modules/Character/CharacterSystemShared.cs` | ECS system extending `BaseComponentDataSystem`. Same pattern as `HandleCharacterDespawn`, `UpdateTeleportation`, `UpdateCharPresentationState`, `GroundTest`, `HandleDamage`, `HandleClientProjectileRequests`, `HandleHitCollisionDespawning`. |
| `ClientGameLoop` | `Assets/Scripts/Game/Main/ClientGameLoop.cs` | Game loop pattern. Same pattern as `ServerGameLoop`, `PreviewGameLoop`, `ThinClientGameLoop`. |

### 7. TASK CONTEXT

This is a **Unity FPS multiplayer sample** using **hybrid ECS + GameObject architecture** with a **client/server split**. The project is built on Unity 2018.3 with HDRP, custom networking, and ECS in mixed-mode.

**Key architectural facts for any task:**
- **Entry point**: `Game.cs` (MonoBehaviour) runs the main loop. It delegates to an active `IGameLoop` (Client/Server/Preview).
- **GameWorld** wraps Unity ECS `World` + `EntityManager`. All game code operates through it.
- **Modules** are the primary organizational unit. Each feature (Character, Player, Projectile, etc.) has `*ModuleClient`, `*ModuleServer`, and optionally `*ModuleShared` classes.
- **Systems** extend `BaseComponentDataSystem<T1, T2, ...>` and are manually updated in a specific order defined by the module.
- **Networking** is custom: `NetworkServer`/`NetworkClient` with `NetworkSchema` for data definition, delta compression, and prediction.
- **ConfigVars** are used for all tunable parameters — declared as static fields with `[ConfigVar]` attribute.
- **BundledResourceManager** handles asset loading via GUIDs.
- **Update order** is critical: modules define phases (Spawn, Despawn, AbilityRequest, MovementStart, MovementResolve, AbilityStart, AbilityResolve, Interpolate, LateUpdate) and the game loop calls them in sequence.

### 8. RELEVANT CODE SNIPPETS

**Snippet 1: Game.cs — Main loop entry point (lines ~60-80)**
```csharp
// From Assets/Scripts/Game/Main/Game.cs
public void Update()
{
    // Update game loops
    foreach (var gameLoop in m_gameLoops)
    {
        gameLoop.Update();
    }
}
```
*Why relevant: Shows the Game class as the top-level orchestrator that delegates to active game loops.*

**Snippet 2: BaseComponentDataSystem — ECS system base class pattern (lines ~30-50)**
```csharp
// From Assets/Scripts/ECS/BaseComponentDataSystem.cs
protected override void OnCreateManager()
{
    OnCreateManager();
    var list = new List<ComponentType>();
    if(ExtraComponentRequirements != null)
        list.AddRange(ExtraComponentRequirements);
    list.AddRange(new ComponentType[] { typeof(T1) });
    list.Add(ComponentType.Subtractive<DespawningEntity>());
    m_Group = GetComponentGroup(list.ToArray());
}
```
*Why relevant: Shows the core ECS system pattern — generic on component types, builds component group automatically, excludes despawning entities.*

**Snippet 3: CharacterModuleClient — Module pattern showing update phases (lines ~40-60)**
```csharp
// From Assets/Scripts/Game/Modules/Character/CharacterModuleClient.cs
public CharacterModuleClient(GameWorld world, BundledResourceManager resourceSystem) : base(world)
{
    CreateHandleSpawnSystems(m_world, m_HandleSpawnSystems, resourceSystem, false);
    CreateHandleDespawnSystems(m_world, m_HandleDespawnSystems);
    CreateAbilityRequestSystems(m_world, m_AbilityRequestUpdateSystems);
    CreateMovementStartSystems(m_world, m_MovementStartSystems);
    CreateMovementResolveSystems(m_world, m_MovementResolveSystems);
    CreateAbilityStartSystems(m_world, m_AbilityStartSystems);
    CreateAbilityResolveSystems(m_world, m_AbilityResolveSystems);
}
```
*Why relevant: Shows the module pattern — systems are created in ordered groups (Spawn → Despawn → AbilityRequest → MovementStart → MovementResolve → AbilityStart → AbilityResolve).*

**Snippet 4: ClientGameLoop — Update orchestration (lines ~100-120)**
```csharp
// From Assets/Scripts/Game/Main/ClientGameLoop.cs
public void Update(float frameDuration)
{
    HandleTime(frameDuration);
    ResolveReferenceFromLocalPlayerToPlayer();
    HandleCommandReset();
    UpdateControlledEntityFlags();
    HandleProjectileRequests();
    // Update all modules in order
    m_CharacterModule.Update();
    HandleSpawns();
    HandleProjectileSpawn();
    HandleSpawning();
    // ...
}
```
*Why relevant: Shows the precise update order that the game loop enforces — critical for understanding execution flow.*

**Snippet 5: ConfigVar pattern — Tunable parameters (lines ~20-30)**
```csharp
// From Assets/Scripts/Game/Main/Game.cs
ConfigVar(Name = "server.tickrate", DefaultValue = "60", 
    Description = "Tickrate for server", Flags = ConfigVar.Flags.ServerInfo);
ConfigVar(Name = "config.fov", DefaultValue = "60", 
    Description = "Field of view", Flags = ConfigVar.Flags.Save);
ConfigVar(Name = "config.mousesensitivity", DefaultValue = "1.5", 
    Description = "Mouse sensitivity", Flags = ConfigVar.Flags.Save);
```
*Why relevant: Shows the ConfigVar attribute pattern used throughout the project for all tunable parameters.*