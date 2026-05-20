Excellent! Now I have a comprehensive understanding of the project. Let me compile the full code review.

---

# CODE REVIEW: FPS Sample Project

## 1. PROJECT SUMMARY

**Project:** Unity FPS Sample — a multiplayer first-person shooter sample project by Unity Technologies.

**Tech Stack:**
- **Engine:** Unity 2018+ with High-Definition Render Pipeline (HDRP)
- **Language:** C# (1,513 files), HLSL (199 files), Shader (103 files)
- **ECS:** Unity ECS (Entity Component System) — early version (pre-Entities 1.0)
- **Networking:** Custom UDP-based transport layer (`com.unity.transport`), custom delta-compression
- **Rendering:** HDRP, Visual Effect Graph, Post-processing stack
- **Animation:** PlayableGraph API + Animator Controllers
- **Build System:** Asset Bundles for content, standalone player for code only

**Scale:** 12,727 total files (7,781 YAML/asset files, 1,513 C# source files)

**Game Modes:** Team Deathmatch, Assault (capture points)

---

## 2. ARCHITECTURE

### Architecture Type: **Hybrid ECS + Module-based Layered Architecture**

The project uses a **custom hybrid architecture** that blends Unity ECS with traditional MonoBehaviour/GameObject patterns. The documentation explicitly calls this "mixed-mode" ECS.

### Layers (top to bottom):

| Layer | Directory | Responsibility |
|-------|-----------|----------------|
| **Game Loop** | `Game/Main/` | `Game.cs` (MonoBehaviour), `ClientGameLoop`, `ServerGameLoop`, `PreviewGameLoop` — orchestrates all systems |
| **Frontend** | `Game/Frontend/` | UI menus, HUD, scoreboard, options |
| **Modules** | `Game/Modules/` | Feature modules: Character, Player, Projectile, Effect, Grenade, Item, ReplicatedEntity, Ragdoll, SpectatorCam, HitCollision, Presentation |
| **Systems** | `Game/Systems/` | Cross-cutting systems: GameMode, Damage, Chat, Movable, Teleporter, NamePlate, DestructibleProp, InputSystem |
| **Entity Layer** | `Game/Entity/` | `GameWorld` (world container), `SceneEntity` (scene tag) |
| **Networking** | `Networking/` | Custom transport: `NetworkServer`, `NetworkClient`, `NetworkConnection`, `NetworkSchema`, `NetworkPrediction`, delta compression |
| **ECS Base** | `ECS/` | `BaseComponentSystem`, `BaseComponentDataSystem`, init/deinit system templates |
| **Audio** | `Audio/` | `SoundSystem`, `ISoundSystem`, `SoundBank`, `SoundDef` |
| **Core/Utils** | `Core/`, `Utils/` | `GameDebug`, `ConfigVars`, `StateMachine`, `Interpolator`, tick buffers |

### Key Architectural Patterns:

1. **Module Pattern** — Each game feature (Character, Player, Projectile, etc.) is a "Module" with Server/Client/Shared variants. Modules own their systems and components.

2. **Game Loop Pattern** — `Game.cs` is the root MonoBehaviour. It delegates to an `IGameLoop` implementation (`ServerGameLoop`, `ClientGameLoop`, `PreviewGameLoop`). Only one game loop is active at a time.

3. **Server/Client Split** — Every module has `*ModuleServer` and `*ModuleClient` classes. The server owns authoritative state; the client handles prediction and presentation.

4. **ECS in Mixed Mode** — Systems extend `BaseComponentSystem` (for MonoBehaviour components) or `BaseComponentDataSystem` (for `IComponentData` structs). All systems are manually updated in a controlled order via `SystemCollection`.

5. **Replication via Interfaces** — Components implement `IReplicatedComponent`, `IPredictedComponent<T>`, or `IInterpolatedComponent<T>` to define network serialization.

6. **ConfigVar System** — Runtime-configurable variables with `[ConfigVar]` attribute, auto-injected from static fields.

---

## 3. RELATED FILES

### Core Architecture Files

| File | Path | Entity Type | Relevance |
|------|------|-------------|-----------|
| **Game.cs** | `Assets/Scripts/Game/Main/Game.cs` | Controller | Root MonoBehaviour, game loop manager, singleton pattern, ConfigVar definitions |
| **GameWorld.cs** | `Assets/Scripts/Game/Entity/GameWorld.cs` | Entity | Central world container, manages ECS world, spawn/despawn lifecycle |
| **BaseComponentDataSystem.cs** | `Assets/Scripts/ECS/BaseComponentDataSystem.cs` | System | Base classes for all ECS systems (1-5 type params), init/deinit patterns |
| **ClientGameLoop.cs** | `Assets/Scripts/Game/Main/ClientGameLoop.cs` | Controller | Client-side game loop, creates all client modules and systems |
| **ServerGameLoop.cs** | `Assets/Scripts/Game/Main/ServerGameLoop.cs` | Controller | Server-side game loop, creates all server modules and systems |

### Module Files

| File | Path | Entity Type | Relevance |
|------|------|-------------|-----------|
| **CharacterModuleShared.cs** | `Assets/Scripts/Game/Modules/Character/CharacterModuleShared.cs` | Module | Base class for character module, defines `SystemCollection` update phases |
| **CharacterModuleServer.cs** | `Assets/Scripts/Game/Modules/Character/CharacterModuleServer.cs` | Module | Server character logic, spawn/despawn handling |
| **CharacterModuleClient.cs** | `Assets/Scripts/Game/Modules/Character/CharacterModuleClient.cs` | Module | Client character logic, presentation updates |
| **ReplicatedEntity.cs** | `Assets/Scripts/Game/Modules/ReplicatedEntity/ReplicatedEntity.cs` | Entity | Base component for all network-replicated entities |
| **ReplicatedComponent.cs** | `Assets/Scripts/Game/Modules/ReplicatedEntity/ReplicatedComponent.cs` | DTO | Network serialization interfaces (`IReplicatedComponent`, `IPredictedComponent`, `IInterpolatedComponent`) |
| **ReplicatedEntityModuleServer.cs** | `Assets/Scripts/Game/Modules/ReplicatedEntity/ReplicatedEntityModuleServer.cs` | Module | Server-side replication management |
| **ReplicatedEntityModuleClient.cs** | `Assets/Scripts/Game/Modules/ReplicatedEntity/ReplicatedEntityModuleClient.cs` | Module | Client-side replication consumption |
| **HealthState.cs** | `Assets/Scripts/Game/Systems/Damage/HealthState.cs` | DTO | Health data component with serialization, damage application |
| **GameModeSystemServer.cs** | `Assets/Scripts/Game/Systems/GameMode/GameModeSystemServer.cs` | System | Server game mode logic, `IGameMode` interface |
| **GameModeSystemClient.cs** | `Assets/Scripts/Game/Systems/GameMode/GameModeSystemClient.cs` | System | Client game mode UI updates |
| **PresentationOwner.cs** | `Assets/Scripts/Game/Modules/Presentation/PresentationOwner.cs` | Entity | Presentation variation system for entity visuals |
| **AnimStateController.cs** | `Assets/Scripts/Game/Modules/Character/Animation/AnimStateController.cs` | Controller | PlayableGraph-based animation state controller |
| **CharacterAnimatorController.cs** | `Assets/Scripts/Game/Modules/Character/Animation/CharacterAnimatorController.cs` | Controller | Bridges ECS predicted state to AnimatorController parameters |

### Networking Files

| File | Path | Entity Type | Relevance |
|------|------|-------------|-----------|
| **NetworkSchema.cs** | `Assets/Scripts/Networking/NetworkSchema.cs` | DTO | Schema-based network serialization definition |
| **NetworkPrediction.cs** | `Assets/Scripts/Networking/NetworkPrediction.cs` | System | Client-side prediction from baselines |
| **NetworkServer.cs** | `Assets/Scripts/Networking/NetworkServer.cs` | Controller | Server network transport |
| **NetworkClient.cs** | `Assets/Scripts/Networking/NetworkClient.cs` | Controller | Client network transport |

### Utility Files

| File | Path | Entity Type | Relevance |
|------|------|-------------|-----------|
| **ConfigVars.cs** | `Assets/Scripts/Game/Core/ConfigVars.cs` | DTO | Runtime config variable system with attribute injection |
| **GameDebug.cs** | `Assets/Scripts/Core/GameDebug.cs` | Utility | Centralized logging with file output |
| **GameConfiguration.cs** | `Assets/Scripts/Game/Main/GameConfiguration.cs` | DTO | ScriptableObject for player movement tuning |

---

## 4. DEPENDENCY GRAPH

### Module-Level Dependencies

```
Game.cs (root MonoBehaviour)
  ├── IGameLoop (interface)
  │    ├── ClientGameLoop
  │    │    ├── CharacterModuleClient ──> CharacterModuleShared
  │    │    ├── PlayerModuleClient
  │    │    ├── ProjectileModuleClient
  │    │    ├── EffectModuleClient
  │    │    ├── ReplicatedEntityModuleClient ──> ReplicatedEntityCollection
  │    │    ├── GameModeSystemClient ──> GameMode (component)
  │    │    └── Presentation systems
  │    │
  │    ├── ServerGameLoop
  │    │    ├── CharacterModuleServer ──> CharacterModuleShared
  │    │    ├── PlayerModuleServer
  │    │    ├── ProjectileModuleServer
  │    │    ├── ReplicatedEntityModuleServer ──> NetworkServer
  │    │    ├── GameModeSystemServer ──> IGameMode
  │    │    ├── DamageAreaSystemServer
  │    │    └── TeleporterSystemServer
  │    │
  │    └── PreviewGameLoop (hybrid server+client)
  │
  ├── GameWorld ──> ECS World + EntityManager
  ├── SoundSystem ──> ISoundSystem
  ├── InputSystem
  ├── LevelManager
  └── ConfigVar system
```

### ECS Base Class Hierarchy

```
ComponentSystem (Unity ECS)
  └── BaseComponentSystem (custom)
       ├── BaseComponentSystem<T1>       (MonoBehaviour components)
       ├── BaseComponentSystem<T1,T2>
       ├── BaseComponentSystem<T1,T2,T3>
       ├── BaseComponentDataSystem<T1>   (IComponentData structs)
       ├── BaseComponentDataSystem<T1,T2>
       ├── BaseComponentDataSystem<T1,T2,T3>
       ├── BaseComponentDataSystem<T1,T2,T3,T4>
       ├── BaseComponentDataSystem<T1,T2,T3,T4,T5>
       ├── InitializeComponentSystem<T>       (one-shot init for MonoBehaviour)
       ├── InitializeComponentDataSystem<T,K> (one-shot init for IComponentData)
       ├── DeinitializeComponentSystem<T>     (one-shot deinit for MonoBehaviour)
       ├── DeinitializeComponentDataSystem<T> (one-shot deinit for IComponentData)
       ├── InitializeComponentGroupSystem<T,S>
       └── DeinitializeComponentGroupSystem<T>
```

### Network Serialization Interface Hierarchy

```
IReplicatedComponent (replicated to all clients)
  ├── ReplicatedEntityData
  ├── HealthStateData
  └── ...

IPredictedComponent<T> (replicated only to predicting client)
  └── CharacterPredictedData

IInterpolatedComponent<T> (replicated to non-predicting clients)
  └── CharacterInterpolatedData
```

---

## 5. CONVENTIONS

### Naming Conventions

1. **PascalCase for all public types** — classes, structs, interfaces, methods, properties. Examples: `GameWorld`, `HealthStateData`, `HandleCharacterSpawnRequests`, `OnUpdate`.

2. **`I` prefix for interfaces** — `ISoundSystem`, `IGameMode`, `IGameLoop`, `IReplicatedComponent`, `IPredictedComponent`, `IInterpolatedComponent`, `IEntityReferenceSerializer`, `IPredictedDataBase`, `IInterpolatedDataBase`, `IFieldValue<T>`.

3. **`*System` suffix for ECS systems** — `HandleCharacterSpawnRequests`, `CharacterLateUpdate`, `GameModeSystemServer`, `GameModeSystemClient`, `UpdatePresentationOwners`, `DestroyDespawning`, `SpinSystem`, `FanSystem`, `TwistSystem`, `TranslateScaleSystem`.

4. **`*Module*` suffix for module classes** — `CharacterModuleServer`, `CharacterModuleClient`, `CharacterModuleShared`, `PlayerModuleServer`, `PlayerModuleClient`, `ReplicatedEntityModuleServer`, `ReplicatedEntityModuleClient`, `EffectModuleClient`.

5. **`*Data` suffix for ECS component data structs** — `HealthStateData`, `ReplicatedEntityData`, `PresentationOwnerData`, `CharacterPredictedData`, `CharacterInterpolatedData`.

6. **`*Handler` suffix for animation/event handlers** — `ActionAnimationHandler`, `AimVerticalHandler`, `TickEventHandler`.

7. **`*Registry` suffix for asset registries** — `CharacterTypeRegistry`, `HeroTypeRegistry`, `ReplicatedEntityRegistry`, `PresentationRegistry`.

8. **`*Settings` suffix for ScriptableObject settings** — `CharacterModuleSettings`, `PlayerModuleSettings`, `GameModeSystemSettings`, `ProjectileModuleSettings`.

9. **`*Definition` suffix for type definitions** — `CharacterTypeDefinition`, `SkeletonDefinition`.

10. **`m_` prefix for private member fields** — `m_world`, `m_NetworkClient`, `m_GameWorld`, `m_EntityManager`, `m_settings`, `m_ResourceManager`.

11. **`k_` prefix for constants** — `k_UserConfigFilename`, `k_BootConfigFilename`.

12. **`s_` prefix for static fields** — `s_Worlds`, `s_charLocoStateHashes`, `s_actionStateHashes`, `s_actionTriggerHashes`, `s_resetHash`.

13. **`[ConfigVar]` attribute for runtime-configurable static fields** — Pattern: `[ConfigVar(Name = "server.tickrate", DefaultValue = "60", ...)] public static ConfigVar serverTickRate;`

14. **`[DisableAutoCreation]` on all custom systems** — Every system class is decorated with `[DisableAutoCreation]` to prevent Unity ECS from auto-updating them (they are manually updated).

### Architectural Patterns

1. **Constructor Injection** — Systems receive dependencies via constructor: `HandleCharacterSpawnRequests(GameWorld world, BundledResourceManager resourceManager, bool isServer)`.

2. **Manual System Update Order** — Systems are grouped into `SystemCollection` instances with named update phases: `m_HandleSpawnSystems`, `m_MovementStartSystems`, `m_MovementResolveSystems`, `m_AbilityStartSystems`, `m_AbilityResolveSystems`.

3. **Server/Client Split** — Every feature has `*Server` and `*Client` variants. Shared logic goes in `*Shared` base class.

4. **Request-Response via ECS** — Spawn/despawn/effect requests are sent as `IComponentData` structs (e.g., `CharacterSpawnRequest`, `SpatialEffectRequest`), processed by dedicated systems.

5. **Singleton Game class** — `Game.game` static property provides global access to the root game instance.

### Style Conventions

1. **`GameDebug.Log` instead of `Debug.Log`** — Custom logging wrapper that writes to both console and file.

2. **`Profiler.BeginSample`/`EndSample`** — Every system's `OnUpdate` is wrapped in profiler samples using `GetType().Name`.

3. **`EntityCommandBuffer` for structural changes** — Spawn/destroy operations use `PostUpdateCommands` to defer structural changes.

4. **`ComponentGroup` for queries** — Systems cache `ComponentGroup` in `OnCreateManager` for efficient entity iteration.

5. **`[NonSerialized]` on network-only fields** — Fields that are network-synced but not serialized by Unity are marked `[NonSerialized]`.

---

## 6. SIMILAR IMPLEMENTATIONS

### Module Pattern (Server/Client/Shared triad)

| Class | File | Similarity |
|-------|------|------------|
| **CharacterModuleServer** | `Assets/Scripts/Game/Modules/Character/CharacterModuleServer.cs` | Server variant of Character module |
| **CharacterModuleClient** | `Assets/Scripts/Game/Modules/Character/CharacterModuleClient.cs` | Client variant of Character module |
| **CharacterModuleShared** | `Assets/Scripts/Game/Modules/Character/CharacterModuleShared.cs` | Shared base with SystemCollection phases |
| **PlayerModuleServer** | `Assets/Scripts/Game/Modules/Player/PlayerModuleServer.cs` | Server variant of Player module |
| **PlayerModuleClient** | `Assets/Scripts/Game/Modules/Player/PlayerModuleClient.cs` | Client variant of Player module |
| **ReplicatedEntityModuleServer** | `Assets/Scripts/Game/Modules/ReplicatedEntity/ReplicatedEntityModuleServer.cs` | Server variant of ReplicatedEntity module |
| **ReplicatedEntityModuleClient** | `Assets/Scripts/Game/Modules/ReplicatedEntity/ReplicatedEntityModuleClient.cs` | Client variant of ReplicatedEntity module |

### ECS System Base Classes (generic type parameter variants)

| Class | File | Similarity |
|-------|------|------------|
| **BaseComponentSystem\<T1\>** | `Assets/Scripts/ECS/BaseComponentDataSystem.cs` | 1-component MonoBehaviour system |
| **BaseComponentSystem\<T1,T2\>** | `Assets/Scripts/ECS/BaseComponentDataSystem.cs` | 2-component MonoBehaviour system |
| **BaseComponentSystem\<T1,T2,T3\>** | `Assets/Scripts/ECS/BaseComponentDataSystem.cs` | 3-component MonoBehaviour system |
| **BaseComponentDataSystem\<T1\>** | `Assets/Scripts/ECS/BaseComponentDataSystem.cs` | 1-component IComponentData system |
| **BaseComponentDataSystem\<T1,T2\>** | `Assets/Scripts/ECS/BaseComponentDataSystem.cs` | 2-component IComponentData system |
| **BaseComponentDataSystem\<T1,T2,T3,T4,T5\>** | `Assets/Scripts/ECS/BaseComponentDataSystem.cs` | 5-component IComponentData system |

### Network Serialization Pattern

| Class | File | Similarity |
|-------|------|------------|
| **HealthStateData** | `Assets/Scripts/Game/Systems/Damage/HealthState.cs` | Implements `IReplicatedComponent` with Serialize/Deserialize |
| **ReplicatedEntityData** | `Assets/Scripts/Game/Modules/ReplicatedEntity/ReplicatedEntity.cs` | Implements `IReplicatedComponent` with Serialize/Deserialize |
| **PresentationOwnerData** | `Assets/Scripts/Game/Modules/Presentation/PresentationOwner.cs` | Implements `IComponentData` (not replicated directly) |

### Game Mode Pattern

| Class | File | Similarity |
|-------|------|------------|
| **GameModeSystemServer** | `Assets/Scripts/Game/Systems/GameMode/GameModeSystemServer.cs` | Server game mode, uses `IGameMode` interface |
| **GameModeSystemClient** | `Assets/Scripts/Game/Systems/GameMode/GameModeSystemClient.cs` | Client game mode, updates UI |
| **NullGameMode** | `Assets/Scripts/Game/Systems/GameMode/GameModeSystemServer.cs` | Null-object pattern implementation of `IGameMode` |

---

## 7. TASK CONTEXT

### What This Project Is

This is **Unity's FPS Sample** — a complete multiplayer FPS game built to demonstrate Unity's ECS, HDRP, networking, and animation systems. It is **not a framework or library** — it's a concrete game implementation intended as a reference.

### Key Systems and Their Relationships

1. **Game Loop System** — `Game.cs` is the entry point. It holds a list of `IGameLoop` instances. Only one is active at a time. Game loops are: `ClientGameLoop`, `ServerGameLoop`, `PreviewGameLoop`. Each game loop creates the appropriate modules and systems.

2. **Module System** — Features are organized into "modules" under `Assets/Scripts/Game/Modules/`. Each module has:
   - A `*ModuleShared` base class (optional) with `SystemCollection` instances for update phases
   - A `*ModuleServer` class (created by `ServerGameLoop`)
   - A `*ModuleClient` class (created by `ClientGameLoop`)
   - Modules own their ECS systems and register them in the correct update phase

3. **ECS System Hierarchy** — All custom systems extend from `BaseComponentSystem` (for MonoBehaviour components) or `BaseComponentDataSystem` (for `IComponentData` structs). These are generic with 1-5 type parameters. All systems are marked `[DisableAutoCreation]` and manually updated via `SystemCollection`.

4. **Network Replication** — Components implement `IReplicatedComponent` (all clients), `IPredictedComponent<T>` (predicting client only), or `IInterpolatedComponent<T>` (non-predicting clients). The `ReplicatedEntity` MonoBehaviour marks a GameObject for replication. The `ReplicatedEntityModuleServer`/`ReplicatedEntityModuleClient` handle the lifecycle.

5. **ConfigVar System** — Static fields with `[ConfigVar]` attribute are auto-discovered and can be changed at runtime via console. They support `Save` and `ServerInfo` flags.

### What to Be Careful About

1. **This is an early ECS version** — Uses `ComponentGroup` (not `EntityQuery`), `ComponentDataProxy<T>` (not `IBaker`), and `ScriptBehaviourManager` (not `SystemBase`). The ECS API is pre-Entities 1.0.

2. **Manual system update order is critical** — Systems are NOT auto-ordered. The order is defined by the order they're added to `SystemCollection` instances. The phases are: ControlledEntityChanged → HandleSpawn → HandleDespawn → AbilityRequest → MovementStart → MovementResolve → AbilityStart → AbilityResolve.

3. **Mixed-mode ECS** — Most entities are still MonoBehaviour-based with `GameObjectEntity` bridge components. Pure ECS (`IComponentData` structs) is used for network data and some simulation data.

4. **Asset Bundle workflow** — All content (prefabs, levels) is loaded from asset bundles at runtime. The standalone player contains only code and a bootstrapper scene. The `BundledResourceManager` handles loading.

5. **No DI container** — Dependencies are manually injected via constructors. The `GameWorld` is the central dependency passed to most systems.

6. **Singleton Game** — `Game.game` is a static singleton. Many systems access it directly for global state (e.g., `Game.game.clientFrontend`).

---

## 8. RELEVANT CODE SNIPPETS

### Snippet 1: Base ECS System Pattern (the core of all game systems)

**File:** `Assets/Scripts/ECS/BaseComponentDataSystem.cs` (lines 147-184)

```csharp
[DisableAutoCreation]
public abstract class BaseComponentDataSystem<T1> : BaseComponentSystem
    where T1 : struct,IComponentData
{
    ComponentGroup Group;
    protected ComponentType[] ExtraComponentRequirements;
    string name;
    
    public BaseComponentDataSystem(GameWorld world) : base(world) {}
    
    protected override void OnCreateManager()
    {
        base.OnCreateManager();
        name = GetType().Name;
        var list = new List<ComponentType>(6);
        if(ExtraComponentRequirements != null)      
            list.AddRange(ExtraComponentRequirements);
        list.AddRange(new ComponentType[] { typeof(T1) } );
        list.Add(ComponentType.Subtractive<DespawningEntity>());
        Group = GetComponentGroup(list.ToArray());
    }

    protected override void OnUpdate()
    {
        Profiler.BeginSample(name);
        var entityArray = Group.GetEntityArray();
        var dataArray = Group.GetComponentDataArray<T1>();
        for (var i = 0; i < entityArray.Length; i++)
            Update(entityArray[i], dataArray[i]);
        Profiler.EndSample();
    }
    
    protected abstract void Update(Entity entity,T1 data);
}
```

**Why relevant:** This is the foundational pattern for ALL game systems. Every system inherits from one of these generic base classes. Key conventions: `[DisableAutoCreation]`, `Profiler.BeginSample`, `ComponentGroup` queries, `Subtractive<DespawningEntity>()` to skip dying entities.

---

### Snippet 2: Module Pattern with SystemCollection Update Phases

**File:** `Assets/Scripts/Game/Modules/Character/CharacterModuleShared.cs` (lines 28-80)

```csharp
public abstract class CharacterModuleShared 
{
    protected GameWorld m_world;
    protected SystemCollection m_ControlledEntityChangedSystems = new SystemCollection();
    protected SystemCollection m_HandleSpawnSystems = new SystemCollection();
    protected SystemCollection m_HandleDespawnSystems = new SystemCollection();
    protected SystemCollection m_AbilityRequestUpdateSystems = new SystemCollection();
    protected SystemCollection m_MovementStartSystems = new SystemCollection();
    protected SystemCollection m_MovementResolveSystems = new SystemCollection();
    protected SystemCollection m_AbilityStartSystems = new SystemCollection();
    protected SystemCollection m_AbilityResolveSystems = new SystemCollection();
    
    public CharacterModuleShared(GameWorld world) { m_world = world; }

    public void HandleSpawns() { m_HandleSpawnSystems.Update(); }
    public void HandleDepawns() { m_HandleDespawnSystems.Update(); }
    public void AbilityRequestUpdate() { m_AbilityRequestUpdateSystems.Update(); }
    // ... more phase methods
}
```

**Why relevant:** Shows the manual update phase pattern. Systems are grouped into named phases and updated in a specific order. This is how the project controls ECS system execution order without relying on `[UpdateBefore]/[UpdateAfter]` attributes.

---

### Snippet 3: Network Replication Interface Pattern

**File:** `Assets/Scripts/Game/Modules/ReplicatedEntity/ReplicatedComponent.cs` (lines 26-48)

```csharp
// Interface for components that are replicated to all clients
public interface IReplicatedComponent 
{
    void Serialize(ref SerializeContext context, ref NetworkWriter writer);
    void Deserialize(ref SerializeContext context, ref NetworkReader reader);
}

// Interface for components that are replicated only to predicting clients
public interface IPredictedComponent<T> : IPredictedDataBase
{
    void Serialize(ref SerializeContext context, ref NetworkWriter writer);
    void Deserialize(ref SerializeContext context, ref NetworkReader reader);
}

// Interface for components that are replicated to all non-predicting clients
public interface IInterpolatedComponent<T> : IInterpolatedDataBase
{
    void Serialize(ref SerializeContext context, ref NetworkWriter writer);
    void Deserialize(ref SerializeContext context, ref NetworkReader reader);
    void Interpolate(ref SerializeContext context, ref T first, ref T last, float t);
}
```

**Why relevant:** Defines the three-tier network replication model. Components choose which interface to implement based on who needs the data. `SerializeContext` carries `EntityManager`, `Entity`, and `IEntityReferenceSerializer`.

---

### Snippet 4: Server/Client Game Loop Module Creation

**File:** `Assets/Scripts/Game/Main/ServerGameLoop.cs` (lines 24-57)

```csharp
public ServerGameWorld(GameWorld world, NetworkServer networkServer, 
    Dictionary<int, ServerGameLoop.ClientInfo> clients, 
    ChatSystemServer m_ChatSystem, BundledResourceManager resourceSystem)
{
    m_GameWorld = world;
    m_CharacterModule = new CharacterModuleServer(m_GameWorld, resourceSystem);
    m_ProjectileModule = new ProjectileModuleServer(m_GameWorld, resourceSystem);
    m_HitCollisionModule = new HitCollisionModule(m_GameWorld, 128, 1);
    m_PlayerModule = new PlayerModuleServer(m_GameWorld, resourceSystem);
    m_SpectatorCamModule = new SpectatorCamModuleServer(m_GameWorld, resourceSystem);
    m_ReplicatedEntityModule = new ReplicatedEntityModuleServer(m_GameWorld, resourceSystem, m_NetworkServer);
    m_ItemModule = new ItemModule(m_GameWorld);

    m_GameModeSystem = m_GameWorld.GetECSWorld().CreateManager<GameModeSystemServer>(
        m_GameWorld, m_ChatSystem, resourceSystem);
    m_DestructablePropSystem = m_GameWorld.GetECSWorld().CreateManager<UpdateDestructableProps>(m_GameWorld);
    m_DamageAreaSystem = m_GameWorld.GetECSWorld().CreateManager<DamageAreaSystemServer>(m_GameWorld);
    // ... more systems
}
```

**Why relevant:** Shows the server-side module instantiation pattern. Each module receives `GameWorld` and `BundledResourceManager`. ECS systems are created via `m_GameWorld.GetECSWorld().CreateManager<T>(...)`. The client side (`ClientGameLoop.cs`) follows the same pattern with `*Client` variants.

---

### Snippet 5: ConfigVar Attribute Pattern

**File:** `Assets/Scripts/Game/Main/Game.cs` (lines 169-185)

```csharp
[ConfigVar(Name = "server.tickrate", DefaultValue = "60", 
    Description = "Tickrate for server", Flags = ConfigVar.Flags.ServerInfo)]
public static ConfigVar serverTickRate;

[ConfigVar(Name = "config.fov", DefaultValue = "60", 
    Description = "Field of view", Flags = ConfigVar.Flags.Save)]
public static ConfigVar configFov;

[ConfigVar(Name = "config.mousesensitivity", DefaultValue = "1.5", 
    Description = "Mouse sensitivity", Flags = ConfigVar.Flags.Save)]
public static ConfigVar configMouseSensitivity;
```

**Why relevant:** Shows the `[ConfigVar]` attribute convention. Static `ConfigVar` fields are auto-discovered at init. `Flags.Save` means the value persists to `user.cfg`. `Flags.ServerInfo` means the value is replicated to clients. This is the project's runtime configuration system.