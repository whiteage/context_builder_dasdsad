Now I have all the information needed. Let me compile the comprehensive documentation.

---

## Weapon System Architecture — Complete Documentation

### Project Summary

This is **FPS Sample**, a Unity multiplayer first-person shooter reference project. It uses Unity's **ECS (Entity Component System)** architecture with a **custom networking layer** built on top of Unity's low-level transport. The project is organized into **Modules** (Character, Item, Projectile, Grenade, HitCollision, Effect, etc.) that each contain server-side and client-side systems.

**Tech stack:** Unity (C#), ECS (Unity.Entities), custom networking (BitStream/DeltaReader/DeltaWriter), ScriptableObject-based registries, Visual Effect Graph.

**Scale:** 1,513 C# source files, 199 HLSL shader files, 7,781 YAML/asset files.

---

### Architecture

The project follows a **Modular ECS Architecture** with clear **Server/Client separation** and a **Component-Based Ability System**. The layers are:

```
┌─────────────────────────────────────────────────────────────┐
│                     Game World (GameWorld)                    │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │Character │  │  Item    │  │Projectile│  │  Grenade   │  │
│  │ Module   │  │  Module  │  │  Module  │  │  Module    │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘  │
│       │              │             │               │         │
│  ┌────┴──────────────┴─────────────┴───────────────┴──────┐  │
│  │                  HitCollision Module                    │  │
│  │  (RaySphereQueryReciever, SplashDamageSystem)          │  │
│  └──────────────────────────┬─────────────────────────────┘  │
│                             │                                │
│  ┌──────────────────────────┴─────────────────────────────┐  │
│  │              Damage System (DamageEvent)                │  │
│  │              HealthState, DamageHistory                 │  │
│  └─────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Server/Client split:                                        │
│  - *ModuleServer.cs → server-side systems                   │
│  - *ModuleClient.cs → client-side systems                   │
│  - *SystemsShared.cs → shared logic (movement, collision)   │
└─────────────────────────────────────────────────────────────┘
```

**Key architectural patterns:**
- **ECS (Entity Component System):** All gameplay data is in `IComponentData` structs. Systems operate on component groups.
- **Server-Authoritative:** Server runs all ability logic, spawns projectiles, applies damage. Client predicts and interpolates.
- **Ability System:** Weapons are not monolithic — they are composed of **Abilities** (e.g., `Ability_AutoRifle`, `Ability_Chaingun`, `Ability_ProjectileLauncher`, `Ability_GrenadeLauncher`, `Ability_Melee`) that are attached to characters via `AbilityCollection`.
- **Registry Pattern:** `ProjectileRegistry`, `HeroTypeRegistry`, `CharacterTypeRegistry` are ScriptableObject-based registries that map GUIDs to type definitions.
- **Request/Command Pattern:** Spawn requests (`ProjectileRequest`, `CharacterSpawnRequest`, `GrenadeSpawnRequest`) are ECS components created via `EntityCommandBuffer` and processed by dedicated systems.
- **Replicated/Predicted/Interpolated Components:** Each ability has three data tiers: `PredictedState` (server-authoritative, client-predicted), `InterpolatedState` (for visual smoothing), and replicated via `IReplicatedComponent`.

---

### Key Files

| File | Purpose | Relevance |
|------|---------|-----------|
| `Assets/Scripts/Game/Modules/Item/ItemModule.cs` | Registers all weapon update systems | Entry point for weapon client-side updates |
| `Assets/Scripts/Game/Modules/Item/RobotWeaponA/RobotWeaponA.cs` | Robot weapon component + update system | Reads `Ability_Chaingun`, `Ability_GrenadeLauncher`, `Ability_Melee` interpolated states |
| `Assets/Scripts/Game/Modules/Item/TerraformerWeaponA/TerraformerWeaponA.cs` | Terraformer weapon component + update system | Reads `Ability_AutoRifle`, `Ability_ProjectileLauncher`, `Ability_Melee` interpolated states |
| `Assets/Scripts/Game/Modules/Character/Behaviours/Abilities/Ability_AutoRifle.cs` | Hitscan auto-rifle ability | Defines `Settings`, `PredictedState`, `InterpolatedState`; performs raycast collision queries |
| `Assets/Scripts/Game/Modules/Character/Behaviours/Abilities/Ability_Chaingun.cs` | Chaingun projectile ability | Spawns `ProjectileRequest` for each shot |
| `Assets/Scripts/Game/Modules/Character/Behaviours/Abilities/Ability_ProjectileLauncher.cs` | Rocket launcher ability | Spawns `ProjectileRequest` with range-limited end position |
| `Assets/Scripts/Game/Modules/Character/Behaviours/Abilities/Ability_GrenadeLauncher.cs` | Grenade launcher ability | Spawns `GrenadeSpawnRequest` with velocity-based trajectory |
| `Assets/Scripts/Game/Modules/Character/Behaviours/Abilities/Ability_Melee.cs` | Melee ability | Performs close-range hit collision query |
| `Assets/Scripts/Game/Modules/Character/Behaviours/AbilityCollection.cs` | Ability controller system | Manages ability activation/deactivation, priority, interruption |
| `Assets/Scripts/Game/Modules/Character/Behaviours/IAbility.cs` | Ability interface | Defines `UpdateAbilityUI` contract |
| `Assets/Scripts/Game/Modules/Projectile/Projectile.cs` | `ProjectileData` component | Core projectile state: position, impact, owner, serialization |
| `Assets/Scripts/Game/Modules/Projectile/ProjectileSpawnRequest.cs` | `ProjectileRequest` component | Request struct for spawning projectiles |
| `Assets/Scripts/Game/Modules/Projectile/ProjectileSystemsShared.cs` | Shared projectile movement/collision | Movement queries, collision resolution, despawning |
| `Assets/Scripts/Game/Modules/Projectile/ProjectileSystemsServer.cs` | Server projectile request handler | Converts `ProjectileRequest` → `ProjectileData` entities |
| `Assets/Scripts/Game/Modules/Projectile/ProjectileSystemsClient.cs` | Client projectile prediction/visuals | Predicted projectiles, client projectile spawning, visual updates |
| `Assets/Scripts/Game/Modules/Projectile/ProjectileTypeDefinition.cs` | `ProjectileSettings` + `ProjectileTypeDefinition` | Defines velocity, damage, splash damage, collision radius |
| `Assets/Scripts/Game/Modules/Projectile/ProjectileRegistry.cs` | Registry of all projectile types | Maps `WeakAssetReference` GUID → `ProjectileTypeDefinition` |
| `Assets/Scripts/Game/Modules/Projectile/ClientProjectile.cs` | Client-side projectile visual | Handles visibility, effects, trail, thrust sound |
| `Assets/Scripts/Game/Modules/HitCollision/RaySphereQueryReciever.cs` | Ray/sphere collision query system | Broadphase + narrowphase collision detection |
| `Assets/Scripts/Game/Modules/HitCollision/SplashDamageSystem.cs` | Splash damage system | Sphere overlap, damage falloff, impulse calculation |
| `Assets/Scripts/Game/Systems/Damage/DamageEvent.cs` | `DamageEvent` buffer element | Damage payload: instigator, damage, direction, impulse |
| `Assets/Scripts/Game/Systems/Damage/HealthState.cs` | `HealthStateData` component | Health tracking, death detection |
| `Assets/Scripts/Game/Modules/Character/CharacterModuleServer.cs` | Server character module | Spawn/despawn handling, damage application |
| `Assets/Scripts/Game/Modules/Character/CharacterSystemShared.cs` | Shared character systems | Item spawning, presentation setup, ability binding |
| `Assets/Scripts/Game/Modules/Character/Components/CharacterReplicated.cs` | `CharacterReplicatedData` | Hero type, ability collection reference, `FindAbilityWithComponent` |
| `Assets/Scripts/Game/Modules/Character/Components/CharacterPredicted.cs` | `CharacterPredictedData` | Position, velocity, action, loco state, damage state |
| `Assets/Scripts/Game/Modules/Character/Components/CharacterInterpolated.cs` | `CharacterInterpolatedData` | Interpolated position/rotation, action, loco state |
| `Assets/Scripts/Game/Modules/Character/HeroTypeAsset.cs` | Hero type definition | Health, eye height, abilities reference, items array |
| `Assets/Scripts/Game/Modules/Item/ItemTypeDefinition.cs` | Item type definition | Prefab references (server, client, 1P) |
| `Assets/Scripts/Game/Modules/Grenade/Grenade.cs` | Grenade component | Settings, internal state, interpolated state |
| `Assets/Scripts/Game/Modules/Grenade/GrenadeSystemServer.cs` | Server grenade system | Handles `GrenadeSpawnRequest`, physics, explosion |
| `Assets/Scripts/Game/Modules/Effect/HitscanEffect/HitscanEffectTypeDefinition.cs` | Hitscan effect definition | Visual effect asset for hitscan trails |
| `Assets/Scripts/Game/Modules/Effect/SpatialEffect/SpatialEffectTypeDefinition.cs` | Spatial effect definition | Impact VFX, sound, shockwave settings |

---

### Key Symbols

#### Weapon Components (Client-Only MonoBehaviour)

```csharp
// RobotWeaponA.cs
[ClientOnlyComponent]
public class RobotWeaponA : MonoBehaviour {
    TickEventHandler primFireEvent, secFireEvent, meleeImpactEvent;
    GunBarrelSetup barrelSetup;  // barrels, muzzleFlash, fireSound, fireAnimCurve
    SoundDef secondaryFireSound;
    VisualEffect secondaryMuzzleFlash;
    SoundDef meleeImpactSound;
    VisualEffect meleeImpactEffect;
}

// TerraformerWeaponA.cs
[ClientOnlyComponent]
public class TerraformerWeaponA : MonoBehaviour {
    Transform muzzle;
    PlayableDirector timelineGrenadeRefill;
    Transform grenadeFuelBase, magazineFuelBase;
    Transform[] vents;
    SoundDef primaryFireSound, secondaryFireSound, meleeImpactSound;
    VisualEffect primaryMuzzleFlash, secondaryMuzzleFlash, meleeImpactEffect;
    HitscanEffectTypeDefinition hitscanEffect;
    SpatialEffectTypeDefinition environmentImpactEffect, characterImpactEffect;
    TickEventHandler primaryFireEvent, secondaryFireEvent, meleeImpactEvent;
}
```

#### Ability Data Contracts

```csharp
// Ability_AutoRifle (Hitscan)
struct Settings { UserCommand.Button fireButton, reloadButton; float damage, damageImpulse, roundsPerSecond; int clipSize; float reloadDuration, hitscanRadius; float minCOF, maxCOF, shotCOFIncrease, COFDecreaseVel; }
struct PredictedState : IPredictedComponent { State action; int phaseStartTick; int ammoInClip; float COF; }
struct InterpolatedState : IInterpolatedComponent { int fireTick; float3 fireEndPos; ImpactType impactType; float3 impactNormal; }

// Ability_Chaingun (Projectile)
struct Settings { UserCommand.Button fireButton, reloadButton; int clipSize; float minFireRate, maxFireRate, fireRateAcceleration, reloadDuration, projectileRange; WeakAssetReference projectileAssetGuid; }
struct PredictedState : IPredictedComponent { State state; int actionStartTick; int ammoInClip; float fireRate; }
struct InterpolatedState : IInterpolatedComponent { int fireTick; }

// Ability_ProjectileLauncher (Rocket)
struct Settings { UserCommand.Button activateButton; float activationDuration, cooldownDuration; CharacterPredictedData.Action fireAction; float projectileRange; WeakAssetReference projectileAssetGuid; }
struct PredictedState : IPredictedComponent { int activeTick; }
struct InterpolatedState : IInterpolatedComponent { int fireTick; }

// Ability_GrenadeLauncher (Grenade)
struct Settings { UserCommand.Button activateButton; float activationDuration, cooldownDuration; CharacterPredictedData.Action fireAction; float grenadeVelocity, grenadePitchAngle; WeakAssetReference assetGuid; }
struct PredictedState : IPredictedComponent { Phase phase; int phaseStartTick; int fireRequestedTick; }
struct InterpolatedState : IInterpolatedComponent { int fireTick; }

// Ability_Melee
struct Settings { UserCommand.Button activateButton; float damage, damageDist, damageRadius, damageImpulse, impactTime; int punchPerSecond; CharacterPredictedData.Action punchAction; }
struct PredictedState : IPredictedComponent { Phase phase; int phaseStartTick; }
```

#### Projectile Data Contracts

```csharp
// ProjectileRequest (spawn command)
struct ProjectileRequest : IComponentData {
    WeakAssetReference projectileAssetGuid;
    int startTick;
    float3 startPosition, endPosition;
    Entity owner;
    int teamId;
    int collisionTestTickDelay;
}

// ProjectileData (runtime state, replicated)
struct ProjectileData : IComponentData, IReplicatedComponent {
    int projectileTypeRegistryIndex;
    Entity projectileOwner;
    int startTick;
    float3 startPos, endPos;
    int impacted;
    float3 impactPos, impactNormal;
    // Non-replicated state:
    int rayQueryId, teamId, collisionCheckTickDelay;
    float3 position;
    ProjectileSettings settings;
    float maxAge;
    int impactTick;
}

// ProjectileSettings (from ProjectileTypeDefinition)
struct ProjectileSettings {
    float velocity;
    float impactDamage;
    float impactImpulse;
    float collisionRadius;
    SplashDamageSettings splashDamage;
}

// SplashDamageSettings
struct SplashDamageSettings {
    float radius, falloffStartRadius;
    float damage, minDamage;
    float impulse, minImpulse;
    float ownerDamageFraction;
}
```

#### Damage Contracts

```csharp
struct DamageEvent : IBufferElementData {
    Entity instigator;
    float damage;
    Vector3 direction;
    float impulse;
}

struct HealthStateData : IComponentData, IReplicatedComponent {
    float health, maxHealth;
    int deathTick;
    Entity killedBy;
}
```

#### Character Data Contracts

```csharp
struct CharacterReplicatedData : IComponentData, IReplicatedComponent {
    int heroTypeIndex;
    Entity abilityCollection;
    Entity FindAbilityWithComponent(EntityManager, Type abilityType);
}

struct CharacterPredictedData : IComponentData, IPredictedComponent {
    enum LocoState { Stand, GroundMove, Jump, DoubleJump, InAir }
    enum Action { None, PrimaryFire, SecondaryFire, Reloading, Melee }
    int tick; Vector3 position, velocity;
    LocoState locoState; int locoStartTick;
    Action action; int actionStartTick;
    int jumpCount, sprinting;
    CameraProfile cameraProfile;
    int damageTick; Vector3 damageDirection; float damageImpulse;
}

struct CharacterInterpolatedData : IInterpolatedComponent, IComponentData {
    Vector3 position; float rotation, aimYaw, aimPitch, moveYaw;
    CharacterPredictedData.LocoState charLocoState; int charLocoTick;
    CharacterPredictedData.Action charAction; int charActionTick;
    int damageTick; float damageDirection;
    int sprinting; float sprintWeight;
    // ... animation-specific fields
}
```

---

### Dependencies

#### Module-Level Dependency Graph

```
CharacterModule
  ├── AbilityCollection (manages all abilities)
  │   ├── Ability_AutoRifle → RaySphereQueryReciever, DamageEvent
  │   ├── Ability_Chaingun → ProjectileRequest
  │   ├── Ability_ProjectileLauncher → ProjectileRequest
  │   ├── Ability_GrenadeLauncher → GrenadeSpawnRequest
  │   └── Ability_Melee → RaySphereQueryReciever, DamageEvent
  ├── CharacterSystemShared → ItemTypeDefinition, HeroTypeAsset
  └── CharacterModuleServer → HealthStateData, DamageEvent, HitCollisionOwnerData

ItemModule (client-only)
  ├── System_RobotWeaponA → CharacterReplicatedData, Ability_Chaingun.InterpolatedState, Ability_GrenadeLauncher.InterpolatedState, Ability_Melee.InterpolatedState
  ├── UpdateTerraformerWeaponA → CharacterReplicatedData, Ability_AutoRifle.InterpolatedState, Ability_ProjectileLauncher.InterpolatedState, Ability_Melee.InterpolatedState
  └── RobotWeaponClientProjectileSpawnHandler / TerraformerWeaponClientProjectileSpawnHandler → ClientProjectile

ProjectileModule
  ├── ProjectileSystemsServer → ProjectileRequest → ProjectileData, ProjectileRegistry
  ├── ProjectileSystemsShared → ProjectileData, RaySphereQueryReciever, DamageEvent, SplashDamageSystem
  └── ProjectileSystemsClient → ProjectileRequest, ClientProjectile, ProjectileRegistry

GrenadeModule
  ├── GrenadeSystemServer → GrenadeSpawnRequest → Grenade.Settings, SplashDamageSystem
  └── GrenadeSystemClient → Grenade.InterpolatedState, GrenadePresentation

HitCollisionModule
  ├── RaySphereQueryReciever → HitCollisionHistory, HitCollisionData
  └── SplashDamageSystem → HitCollisionHistory, DamageEvent

DamageSystem
  └── DamageEvent → HealthStateData, DamageHistoryData
```

#### Key Call Graph: Weapon Firing Flow

```
UserCommand (input)
  → AbilityCollection (activates ability)
    → Ability_*_RequestActive (checks button, sets RequestActive)
      → Ability_*_Update (server-side)
        ├── [Hitscan] AutoRifle_EnterFiringPhase
        │     → RaySphereQueryReciever.RegisterQuery()
        │     → AutoRifle_HandleCollisionQuery
        │       → DamageEvent.AddEvent() (on hit)
        │       → Sets InterpolatedState (fireTick, fireEndPos, impactType, impactNormal)
        │
        ├── [Projectile] Chaingun_EnterFiringPhase
        │     → ProjectileRequest.Create() (startPos, endPos, assetGuid, owner, teamId)
        │       → HandleServerProjectileRequests
        │         → ProjectileData.SetupFromRequest()
        │         → ProjectileSystemsShared: movement + collision
        │           → RaySphereQueryReciever.RegisterQuery()
        │           → HandleProjectileMovementCollisionQuery
        │             → DamageEvent.AddEvent() (on hit)
        │             → SplashDamageRequest.Create() (if splashDamage.radius > 0)
        │
        ├── [Projectile] ProjectileLauncher_Update
        │     → ProjectileRequest.Create() (same as Chaingun)
        │
        └── [Grenade] GrenadeLauncher_Update
              → GrenadeSpawnRequest.Create() (position, velocity, assetGuid, owner, teamId)
                → HandleGrenadeRequest
                  → Grenade physics (gravity, bounce)
                  → SplashDamageRequest.Create() (on explosion)

  → Weapon Update Systems (client-side, reads InterpolatedState)
    ├── System_RobotWeaponA.Update()
    │   → Reads Ability_Chaingun.InterpolatedState.fireTick → primFireEvent
    │   → Reads Ability_GrenadeLauncher.InterpolatedState.fireTick → secFireEvent
    │   → Reads Ability_Melee.InterpolatedState.impactTick → meleeImpactEvent
    │   → Plays sounds, muzzle flashes, barrel animations
    │
    └── UpdateTerraformerWeaponA.Update()
        → Reads Ability_AutoRifle.InterpolatedState.fireTick → primaryFireEvent
        → Reads Ability_AutoRifle.InterpolatedState.fireEndPos → hitscan effect
        → Reads Ability_ProjectileLauncher.InterpolatedState.fireTick → secondaryFireEvent
        → Reads Ability_Melee.InterpolatedState.impactTick → meleeImpactEvent
        → Plays sounds, muzzle flashes, impact effects
```

---

### Conventions

#### Naming Conventions

| Convention | Examples | Evidence |
|-----------|----------|----------|
| **PascalCase** for all types | `ProjectileData`, `HealthStateData`, `CharacterPredictedData` | All structs and classes use PascalCase |
| **Prefix `I`** for interfaces | `IComponentData`, `IReplicatedComponent`, `IPredictedComponent`, `IInterpolatedComponent` | Unity ECS standard |
| **Suffix `Data`** for ECS component structs | `ProjectileData`, `HealthStateData`, `CharacterReplicatedData`, `CharacterPredictedData`, `HitCollisionOwnerData` | Consistent across all ECS components |
| **Suffix `Settings`** for configuration | `ProjectileSettings`, `SplashDamageSettings`, `Ability_AutoRifle.Settings`, `Ability_Chaingun.Settings` | All ability settings nested structs |
| **Suffix `Request`** for spawn commands | `ProjectileRequest`, `CharacterSpawnRequest`, `GrenadeSpawnRequest`, `SplashDamageRequest` | All ECS request components |
| **Prefix `Ability_`** for ability factories | `Ability_AutoRifle`, `Ability_Chaingun`, `Ability_ProjectileLauncher`, `Ability_GrenadeLauncher`, `Ability_Melee` | All ability ScriptableObjects |
| **Suffix `Module`** for module classes | `ItemModule`, `ProjectileModuleServer`, `CharacterModuleClient` | Module entry points |
| **Suffix `System`** for ECS systems | `HandleCharacterSpawn`, `HandleDamage`, `HandleServerProjectileRequests` | All `ComponentSystem` subclasses |
| **Suffix `_Update`** for ability update systems | `AutoRifle_Update`, `Chaingun_Update`, `ProjectileLauncher_Update` | Inner classes within ability files |
| **Suffix `_RequestActive`** for activation systems | `AutoRifle_RequestActive`, `Chaingun_RequestActive` | Inner classes within ability files |
| **Prefix `m_`** for member fields | `m_world`, `m_resourceManager`, `m_handleSpawnSystems` | Consistent private field naming |
| **Prefix `m_`** for serialized non-public fields | `m_settings` | Unity serialization convention |

#### Architectural Patterns

| Pattern | Usage | Evidence |
|---------|-------|----------|
| **ECS (Entity Component System)** | All gameplay data is in `IComponentData` structs; systems operate on component groups | `ProjectileData : IComponentData`, `BaseComponentSystem<T>`, `ComponentGroup` |
| **Server-Authoritative** | Server runs all ability logic; client only reads interpolated states | `ExtraComponentRequirements = { typeof(ServerEntity) }` on all ability update systems |
| **Prediction/Rollback** | `IPredictedComponent` + `VerifyPrediction()` for client-side prediction | `Ability_AutoRifle.PredictedState : IPredictedComponent` |
| **Interpolation** | `IInterpolatedComponent` for visual smoothing between server updates | `Ability_AutoRifle.InterpolatedState : IInterpolatedComponent` |
| **Replicated Components** | `IReplicatedComponent` for network serialization | `ProjectileData : IReplicatedComponent` with `Serialize`/`Deserialize` |
| **Request/Command** | Spawn requests as ECS components processed by dedicated systems | `ProjectileRequest.Create()` → `HandleServerProjectileRequests` |
| **Registry Pattern** | ScriptableObject registries mapping GUIDs to definitions | `ProjectileRegistry`, `HeroTypeRegistry`, `CharacterTypeRegistry` |
| **Factory Pattern** | `CharBehaviorFactory` base class for ability creation | `Ability_AutoRifle : CharBehaviorFactory` with `Create()` override |
| **Ability Composition** | Characters own an `AbilityCollection` containing multiple abilities | `CharacterReplicatedData.abilityCollection` → `EntityGroupChildren` buffer |
| **Module Pattern** | Each feature area has `*ModuleServer`/`*ModuleClient`/`*SystemsShared` | `ProjectileModuleServer`, `ProjectileModuleClient`, `ProjectileSystemsShared` |
| **Tick-Based Timing** | All timing uses game ticks, not real time | `DurationSinceTick()`, `startTick`, `phaseStartTick` |
| **DynamicBuffer for Events** | `DamageEvent` uses `InternalBufferCapacity` for event queuing | `[InternalBufferCapacity(16)] public struct DamageEvent : IBufferElementData` |

#### Style Conventions

| Convention | Evidence |
|-----------|----------|
| **Explicit `ref` for struct mutation** | `void Update(GameTime time, RobotWeaponA weapon, ref CharacterReplicatedData charRepAll, float deltaTime)` |
| **PostUpdateCommands for entity creation** | `ProjectileRequest.Create(PostUpdateCommands, ...)` |
| **Profiler.BeginSample/EndSample** | Used in all update methods for performance tracking |
| **GameDebug.Assert for validation** | `GameDebug.Assert(chaingunAbility != Entity.Null, ...)` |
| **ConfigVar for debug toggles** | `ConfigVar(Name = "projectile.drawserverdebug", DefaultValue = "0")` |
| **DisableAutoCreation attribute** | `[DisableAutoCreation]` on all systems (manually registered in modules) |
| **ClientOnlyComponent attribute** | `[ClientOnlyComponent]` on weapon MonoBehaviours |
| **Serializable nested structs** | All Settings/PredictedState/InterpolatedState are `[Serializable]` structs nested in ability classes |
| **WeakAssetReference for asset references** | All cross-references use `WeakAssetReference` GUIDs, not direct references |

---

### Similar Implementations

**1. `Ability_AutoRifle` and `Ability_Chaingun`** — Both follow the same pattern:
- Both extend `CharBehaviorFactory`
- Both define `Settings`, `PredictedState` (with `IPredictedComponent`), `InterpolatedState` (with `IInterpolatedComponent`)
- Both have inner `_RequestActive` and `_Update` systems with `typeof(ServerEntity)` requirement
- Both use `SetPhase()`/`SetAction()` state machine pattern
- Both manage ammo (`ammoInClip`, `clipSize`, `reloadDuration`)
- Difference: AutoRifle uses hitscan (raycast), Chaingun spawns projectiles

**2. `Ability_ProjectileLauncher` and `Ability_GrenadeLauncher`** — Both follow the same pattern:
- Both extend `CharBehaviorFactory`
- Both have `Phase` enum (Idle/Active/Cooldown)
- Both spawn physics objects via request commands
- Both use `LocalState` with `lastFireTick` to prevent double-fire on re-prediction
- Difference: ProjectileLauncher uses `ProjectileRequest` (linear), GrenadeLauncher uses `GrenadeSpawnRequest` (velocity + gravity)

**3. `System_RobotWeaponA` and `UpdateTerraformerWeaponA`** — Both follow the same pattern:
- Both extend `BaseComponentSystem<WeaponComponent, CharacterPresentationSetup>`
- Both check `charPresentation.IsVisible` before updating
- Both read `CharacterReplicatedData` to find ability entities via `FindAbilityWithComponent()`
- Both read ability `InterpolatedState` to drive visual effects (sounds, muzzle flashes, impacts)
- Both have `TickEventHandler` for rate-limiting event triggers

---

### Context for the Task

#### System Overview

The weapon system is a **two-layer architecture**:

1. **Server-side Ability Layer** (`Ability_*` classes): Each weapon ability is a `CharBehaviorFactory` that creates ECS entities with `Settings`, `PredictedState`, and `InterpolatedState` components. Server systems process input, manage state machines (Idle→Fire→Reload), and spawn projectiles or perform hitscan raycasts. The `AbilityCollection` manages activation/deactivation with priority/interruption rules.

2. **Client-side Presentation Layer** (`RobotWeaponA`, `TerraformerWeaponA`): MonoBehaviour components on weapon prefabs that read ability `InterpolatedState` data to drive visual effects. These are updated in `ItemModule.LateUpdate()`.

#### API Contract: Weapon → Character

Weapons access character data through `CharacterReplicatedData`:
```csharp
// CharacterReplicatedData holds reference to ability collection
var charRepAll = EntityManager.GetComponentData<CharacterReplicatedData>(charPresentation.character);
// Find ability by component type
var chaingunAbility = charRepAll.FindAbilityWithComponent(EntityManager, typeof(Ability_Chaingun.InterpolatedState));
// Read interpolated state for visual sync
var chaingunState = EntityManager.GetComponentData<Ability_Chaingun.InterpolatedState>(chaingunAbility);
```

#### API Contract: Ability → Projectile

Abilities spawn projectiles via `ProjectileRequest.Create()`:
```csharp
ProjectileRequest.Create(
    PostUpdateCommands,          // EntityCommandBuffer
    time.tick,                   // startTick
    time.tick - command.renderTick,  // collisionTestTickDelay
    settings.projectileAssetGuid,    // WeakAssetReference to ProjectileTypeDefinition
    charAbility.character,           // owner Entity
    character.teamId,                // teamId (for collision masking)
    eyePos,                          // startPosition
    endPos                           // endPosition (eyePos + lookDir * range)
);
```

#### API Contract: Projectile → Damage

Projectiles apply damage through the HitCollision system:
```csharp
// In HandleProjectileMovementCollisionQuery (ProjectileSystemsShared.cs):
if (EntityManager.HasComponent<DamageEvent>(queryResult.hitCollisionOwner))
{
    var damageEventBuffer = EntityManager.GetBuffer<DamageEvent>(queryResult.hitCollisionOwner);
    DamageEvent.AddEvent(damageEventBuffer, 
        projectileData.projectileOwner,  // instigator
        projectileData.settings.impactDamage,  // damage amount
        projectileDir,                    // direction
        projectileData.settings.impactImpulse);  // impulse
}

// Splash damage (if configured):
if (projectileData.settings.splashDamage.radius > 0)
{
    SplashDamageRequest.Create(PostUpdateCommands, 
        query.hitCollisionTestTick, 
        damageInstigator, 
        queryResult.hitPoint, 
        collisionMask, 
        projectileData.settings.splashDamage);
}
```

#### API Contract: Hitscan (AutoRifle) → Damage

Hitscan weapons use `RaySphereQueryReciever` directly:
```csharp
// Register query in EnterFiringPhase
internalState.rayQueryId = queryReciever.RegisterQuery(new RaySphereQueryReciever.Query()
{
    origin = eyePos,
    direction = direction,
    distance = 500,
    ExcludeOwner = charAbility.character,
    hitCollisionTestTick = command.renderTick,
    radius = settings.hitscanRadius,
    mask = collisionMask,
});

// Handle result in AutoRifle_HandleCollisionQuery
queryReciever.GetResult(internalState.rayQueryId, out query, out queryResult);
if (queryResult.hit == 1 && queryResult.hitCollisionOwner != Entity.Null)
{
    var damageEventBuffer = EntityManager.GetBuffer<DamageEvent>(queryResult.hitCollisionOwner);
    DamageEvent.AddEvent(damageEventBuffer, charAbility.character, settings.damage, query.direction, settings.damageImpulse);
}
```

#### Data Flow Summary

```
Input (UserCommand.buttons)
  → AbilityCollection (activates/deactivates abilities)
    → Ability_*_Update (server, with typeof(ServerEntity))
      → [Hitscan] RaySphereQueryReciever → DamageEvent → HealthStateData
      → [Projectile] ProjectileRequest → ProjectileData → movement/collision → DamageEvent → HealthStateData
      → [Grenade] GrenadeSpawnRequest → Grenade physics → SplashDamageRequest → DamageEvent → HealthStateData
    → Sets InterpolatedState (replicated to client)
  → Weapon Update System (client, reads InterpolatedState)
    → Plays VFX, sounds, animations
```