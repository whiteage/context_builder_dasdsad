Now I have a comprehensive understanding of the entire project. Let me compile the full architecture analysis.

---

## Project Summary

**SurvivalGame** is an Unreal Engine 4 (C++) third-person survival shooter game. It features a day/night cycle, zombie AI enemies, weapon/equipment systems, player hunger mechanics, object carrying, and a co-op game mode. The project is built with UE4's standard GameFramework (GameMode, GameState, PlayerController, Character, etc.) and uses Behavior Trees for AI.

- **Scale**: 75 C++ source files (38 headers + 37 implementations), 43 classes, 380 methods
- **Tech Stack**: Unreal Engine 4 C++, UHT (Unreal Header Tool), Behavior Trees, Blackboard, UMG (Blueprint UI)
- **Plugins**: ExtendedRifleMod, MyFlashlightMod (modding examples)

---

## Architecture

**Architecture Type**: Unreal Engine Game Framework (Layered/Component-based)

The project follows UE4's standard GameFramework pattern with clear separation into these layers:

### Layer Map

| Layer | Directory | Responsibility |
|---|---|---|
| **World/Game Rules** | `World/` | GameMode, GameState, GameInstance, TimeOfDay, PlayerStart |
| **Player** | `Player/` | Character, BaseCharacter, PlayerController, PlayerState, CameraManager, SpectatorPawn, LocalPlayer |
| **Items/Weapons** | `Items/` | Weapon hierarchy, Pickups, Consumables, Bombs, Flashlight, Impact Effects, Damage Types |
| **AI** | `AI/` | ZombieCharacter, ZombieAIController, Behavior Tree tasks, Waypoints |
| **Components** | `Components/` | CarryObjectComponent, CharacterMovementComponent |
| **UI** | `UI/` | HUD |
| **Mutators** | `Mutators/` | Mutator chain system for modding |
| **Core** | `Core/` | GameplayStatics utility library |
| **Editor** | `Editor/` | SoundNodeLocalPlayer (editor utility) |

### Key Relationships

```
SGameMode (World)
  ├── spawns → SZombieCharacter (AI)
  ├── owns → SGameState (World)
  ├── uses → SMutator chain (Mutators)
  ├── spawns → ASCharacter (Player)
  └── references → SPlayerStart (World)

ASCharacter (Player)
  ├── extends → ASBaseCharacter (Player)
  ├── owns → Inventory: TArray<ASWeapon*> (Items)
  ├── owns → USCarryObjectComponent (Components)
  ├── owns → USCharacterMovementComponent (Components)
  ├── uses → ASUsableActor (Items) via focus/interaction
  └── controlled by → ASPlayerController (Player)

ASWeapon (Items)
  ├── extends → AActor
  ├── owned by → ASCharacter (MyPawn)
  ├── subclasses: ASWeaponInstant, ASFlashlight
  └── references → ASImpactEffect, USDamageType

SZombieCharacter (AI)
  ├── extends → ASBaseCharacter (Player)
  ├── controlled by → ASZombieAIController (AI)
  ├── uses → UPawnSensingComponent
  └── references → EBotBehaviorType (STypes)

ASZombieAIController (AI)
  ├── owns → UBehaviorTreeComponent
  ├── owns → UBlackboardComponent
  └── uses → BTTask_FindBotWaypoint, BTTask_FindPatrolLocation
```

---

## Key Files

### 1. `SurvivalGame/Source/SurvivalGame/Public/Player/SBaseCharacter.h`
**Purpose**: Abstract base class for all characters (player + AI). Defines health, damage/death pipeline, sprinting, targeting, and replication of hit info.
**Why relevant**: Root of the character hierarchy. All damage flows through `TakeDamage()` → `Die()` → `OnDeath()`.

### 2. `SurvivalGame/Source/SurvivalGame/Public/Player/SCharacter.h`
**Purpose**: Concrete player character. Adds inventory system (weapon slots), hunger mechanics, object interaction, camera, movement input, and weapon firing.
**Why relevant**: Central hub connecting all player systems — weapons, items, carry component, hunger, noise emission.

### 3. `SurvivalGame/Source/SurvivalGame/Public/Items/SWeapon.h`
**Purpose**: Abstract weapon base class. Manages equip state, firing state machine, ammo, weapon mesh attachment, animation, and sound.
**Why relevant**: Root of the weapon hierarchy. Defines `FireWeapon()` (PURE_VIRTUAL), `StartFire()`/`StopFire()`, and server RPCs for firing.

### 4. `SurvivalGame/Source/SurvivalGame/Public/Items/SWeaponInstant.h`
**Purpose**: Hit-scan (instant) weapon. Implements `FireWeapon()` with line traces, damage application, impact effects, trail FX, and server-side hit confirmation.
**Why relevant**: The only concrete weapon implementation. Shows the hit-scan damage pipeline.

### 5. `SurvivalGame/Source/SurvivalGame/Public/AI/SZombieCharacter.h`
**Purpose**: Zombie AI character. Extends `ASBaseCharacter` with `UPawnSensingComponent` for perception, melee attacks, audio loops, and bot behavior types.
**Why relevant**: The only AI enemy. Shows perception-driven behavior and melee combat.

### 6. `SurvivalGame/Source/SurvivalGame/Public/AI/SZombieAIController.h`
**Purpose**: AI controller for zombies. Owns `UBehaviorTreeComponent` and `UBlackboardComponent`. Manages waypoints, target enemies, and bot type.
**Why relevant**: The brain of the zombie. Connects Behavior Tree to game state.

### 7. `SurvivalGame/Source/SurvivalGame/Public/World/SGameMode.h`
**Purpose**: Base game mode. Manages player spawning, bot spawning (night cycle), default inventory, damage rules (friendly fire), mutator chain, and day/night state.
**Why relevant**: Central game rules authority. Orchestrates all systems.

### 8. `SurvivalGame/Source/SurvivalGame/Public/World/SGameState.h`
**Purpose**: Replicated game state. Tracks total score, day/night cycle (elapsed game minutes, sunrise/sunset), and broadcasts HUD messages.
**Why relevant**: Source of truth for time-of-day and score across all clients.

### 9. `SurvivalGame/Source/SurvivalGame/Public/Items/SUsableActor.h`
**Purpose**: Abstract base for all interactable objects. Defines `OnBeginFocus()`, `OnEndFocus()`, `OnUsed()`.
**Why relevant**: Foundation of the interaction system. Extended by Pickups, Bombs, etc.

### 10. `SurvivalGame/Source/SurvivalGame/Public/Items/SPickupActor.h`
**Purpose**: Abstract pickup base. Adds respawn logic, active/inactive state, and pickup sound.
**Why relevant**: Foundation for weapon pickups and consumables.

### 11. `SurvivalGame/Source/SurvivalGame/Public/Components/SCarryObjectComponent.h`
**Purpose**: Spring arm component that allows picking up, carrying, rotating, and throwing physics objects.
**Why relevant**: Unique gameplay mechanic. Server-authoritative with multicast replication.

### 12. `SurvivalGame/Source/SurvivalGame/Public/World/STimeOfDayManager.h`
**Purpose**: Manages visual day/night cycle. Lerps sun brightness, skylight intensity/color, and plays ambient audio.
**Why relevant**: Drives the core survival pressure (zombies spawn at night).

### 13. `SurvivalGame/Source/SurvivalGame/Public/Mutators/SMutator.h`
**Purpose**: Base mutator class. Forms a chain-of-responsibility pattern for modifying actors at spawn time.
**Why relevant**: Modding/extension system. Allows runtime replacement of weapons and actors.

### 14. `SurvivalGame/Source/SurvivalGame/STypes.h`
**Purpose**: Shared type definitions: `EInventorySlot` (Hands/Primary/Secondary), `EBotBehaviorType` (Passive/Patrolling), `FTakeHitInfo` (replicated damage struct).
**Why relevant**: Shared enums and structs used across all systems.

### 15. `SurvivalGame/Source/SurvivalGame/Public/Player/SPlayerController.h`
**Purpose**: Player controller. Handles respawn, spectating, HUD messages, suicide, and chat.
**Why relevant**: Client-server communication bridge.

---

## Key Symbols

### Class Hierarchy

```
AActor
├── ASUsableActor (ABSTRACT) — Items/SUsableActor.h
│   ├── ASPickupActor (ABSTRACT) — Items/SPickupActor.h
│   │   ├── ASWeaponPickup — Items/SWeaponPickup.h
│   │   └── ASConsumableActor — Items/SConsumableActor.h
│   └── ASBombActor — Items/SBombActor.h
├── ASWeapon (ABSTRACT) — Items/SWeapon.h
│   ├── ASWeaponInstant (ABSTRACT) — Items/SWeaponInstant.h
│   └── ASFlashlight (ABSTRACT) — Items/SFlashlight.h
├── ASImpactEffect (ABSTRACT) — Items/SImpactEffect.h
├── ASTimeOfDayManager (ABSTRACT) — World/STimeOfDayManager.h
└── ASMutator (ABSTRACT) — Mutators/SMutator.h
    └── ASMutator_WeaponReplacement — Mutators/SMutator_WeaponReplacement.h

ACharacter
└── ASBaseCharacter (ABSTRACT) — Player/SBaseCharacter.h
    ├── ASCharacter — Player/SCharacter.h
    └── ASZombieCharacter (ABSTRACT) — AI/SZombieCharacter.h

AController
├── ASPlayerController — Player/SPlayerController.h
└── ASZombieAIController — AI/SZombieAIController.h

AGameMode
└── ASGameMode — World/SGameMode.h
    ├── ASCoopGameMode (ABSTRACT) — World/SCoopGameMode.h
    └── ASOpenWorldGameMode (ABSTRACT) — World/SOpenWorldGameMode.h

AGameState
└── ASGameState — World/SGameState.h

APlayerState
└── ASPlayerState — Player/SPlayerState.h

AHUD
└── ASHUD — UI/SHUD.h

UActorComponent
├── USCarryObjectComponent (extends USpringArmComponent) — Components/SCarryObjectComponent.h
└── USCharacterMovementComponent (extends UCharacterMovementComponent) — Components/SCharacterMovementComponent.h

UBTTask_BlackboardBase
├── UBTTask_FindBotWaypoint — AI/BTTask_FindBotWaypoint.h
└── UBTTask_FindPatrolLocation — AI/BTTask_FindPatrolLocation.h
```

### Key Methods

| Method | Class | Purpose |
|---|---|---|
| `TakeDamage()` | `ASBaseCharacter` | Entry point for all damage. Calls `Die()` → `OnDeath()` |
| `FireWeapon()` (PURE_VIRTUAL) | `ASWeapon` | Abstract — implemented by subclasses |
| `FireWeapon()` | `ASWeaponInstant` | Line trace hit-scan, calls `ProcessInstantHit()` |
| `ProcessInstantHitConfirmed()` | `ASWeaponInstant` | Server-authoritative damage application |
| `OnUsed()` | `ASUsableActor` | Player interaction callback |
| `OnSeePlayer()` / `OnHearNoise()` | `ASZombieCharacter` | Perception delegates from `UPawnSensingComponent` |
| `PerformMeleeStrike()` | `ASZombieCharacter` | Melee attack damage |
| `ExecuteTask()` | `BTTask_FindBotWaypoint` / `BTTask_FindPatrolLocation` | Behavior tree task execution |
| `Killed()` | `ASGameMode` | Called when any pawn dies. Routes to scoring/logic |
| `DefaultTimer()` | `ASGameMode` | Periodic tick for day/night checks and bot spawning |
| `GetAndUpdateIsNight()` | `ASGameState` | Determines if current time is night |
| `Pickup()` / `Drop()` / `Throw()` | `USCarryObjectComponent` | Object carrying mechanics |
| `CheckRelevance()` | `ASMutator` | Chain-of-responsibility for actor modification |

---

## Dependencies

### Module-Level (Directory) Dependencies

Based on `#include` analysis:

```
Player/  ────>  Items/  (SCharacter.h includes SWeapon.h via forward decl + SWeapon.h includes SCharacter.h)
Player/  ────>  Components/  (SCharacter.h owns USCarryObjectComponent)
Player/  ────>  STypes.h  (SBaseCharacter.h includes STypes.h)
Player/  ────>  UI/  (SPlayerController.h includes SHUD.h)

AI/  ────>  Player/  (SZombieCharacter.h includes SBaseCharacter.h)
AI/  ────>  STypes.h  (SZombieAIController.h includes STypes.h)

World/  ────>  Mutators/  (SGameMode.h includes SMutator.h)
World/  ────>  Player/  (SGameMode.h forward-declares ASPlayerState)

Items/  ────>  Player/  (SWeapon.h includes SCharacter.h)
Items/  ────>  Items/  (SWeaponInstant.h includes SWeapon.h, SPickupActor.h includes SUsableActor.h)

Mutators/  ────>  Items/  (SMutator_WeaponReplacement.h includes SWeapon.h)
```

### Key Circular Dependency

`SCharacter.h` ↔ `SWeapon.h` — This is a bidirectional dependency:
- `SCharacter.h` includes `SWeapon.h` (for `Inventory` array and `CurrentWeapon`)
- `SWeapon.h` includes `SCharacter.h` (for `MyPawn` owner reference)

This is handled via UE4's header generation system and forward declarations.

---

## Conventions

### Naming Conventions

| Convention | Evidence | Examples |
|---|---|---|
| **Prefix `A` for Actor classes** | All game actors start with `A` | `ASCharacter`, `ASWeapon`, `ASBombActor`, `ASGameMode`, `ASZombieCharacter` |
| **Prefix `U` for Component/Object classes** | All component/object classes start with `U` | `USCarryObjectComponent`, `USCharacterMovementComponent`, `USGameInstance`, `USLocalPlayer` |
| **Prefix `S` for SurvivalGame classes** | All project-specific classes use `S` prefix after `A`/`U` | `ASBaseCharacter`, `ASWeaponInstant`, `USGameplayStatics`, `ASZombieAIController` |
| **Prefix `I` for interfaces** | Not used in this project | N/A |
| **Suffix `Component` for components** | Component classes end with `Component` | `SCarryObjectComponent`, `SCharacterMovementComponent` |
| **Suffix `Controller` for controllers** | Controller classes end with `Controller` | `ASPlayerController`, `ASZombieAIController` |
| **Suffix `Character` for characters** | Character classes end with `Character` | `ASBaseCharacter`, `ASCharacter`, `ASZombieCharacter` |
| **Suffix `State` for state classes** | State classes end with `State` | `ASGameState`, `ASPlayerState` |
| **Suffix `Mode` for game modes** | Game mode classes end with `Mode` | `ASGameMode`, `ASCoopGameMode`, `ASOpenWorldGameMode` |
| **Suffix `Actor` for usable/pickup actors** | Interactable actors end with `Actor` | `ASUsableActor`, `ASBombActor`, `ASConsumableActor`, `ASPickupActor` |
| **Suffix `Pickup` for pickup items** | Pickup items end with `Pickup` | `ASPickupActor`, `ASWeaponPickup` |
| **Suffix `Manager` for manager actors** | Manager ends with `Manager` | `ASTimeOfDayManager`, `ASPlayerCameraManager` |
| **Suffix `Task` for BTTask classes** | Behavior tree tasks end with `Task` | `BTTask_FindBotWaypoint`, `BTTask_FindPatrolLocation` |
| **Prefix `b` for booleans** | All boolean properties use `b` prefix | `bIsActive`, `bIsJumping`, `bSensedTarget`, `bAllowFriendlyFireDamage`, `bIsPunching` |
| **PascalCase for all types** | Classes, enums, structs use PascalCase | `EInventorySlot`, `EBotBehaviorType`, `FTakeHitInfo`, `FReplacementInfo` |
| **Prefix `E` for enums** | Enums use `E` prefix | `EInventorySlot`, `EBotBehaviorType`, `EWeaponState`, `EHUDState`, `EHUDMessage` |
| **Prefix `F` for structs** | Structs use `F` prefix | `FTakeHitInfo`, `FReplacementInfo` |

### Architectural Patterns

| Pattern | Usage | Evidence |
|---|---|---|
| **Unreal Game Framework** | Core architecture follows UE4's AGameMode/AGameState/APlayerController/ACharacter pattern | `ASGameMode : AGameMode`, `ASGameState : AGameState`, `ASPlayerController : APlayerController`, `ASBaseCharacter : ACharacter` |
| **Chain of Responsibility** | Mutator system chains mutators together | `ASMutator::NextMutator` — each mutator calls the next in `CheckRelevance()` |
| **Strategy (Behavior Tree)** | AI behavior driven by Behavior Trees + Blackboard | `ASZombieAIController` owns `UBehaviorTreeComponent` + `UBlackboardComponent`; `ASZombieCharacter` has `UBehaviorTree* BehaviorTree` |
| **Observer (Delegates)** | UE4 delegate system for events | `FPlayerArrayChanged` delegate in `SGameInstance`, `FChatMessageReceived` in `SPlayerController`, `UPawnSensingComponent` delegates |
| **Server Authority** | All gameplay actions validated on server | `UFUNCTION(Server, Reliable, WithValidation)` on all critical methods (`ServerSetSprinting`, `ServerUse`, `ServerPickup`, `ServerStartFire`, etc.) |
| **Replication (NetMulticast)** | Visual effects replicated to all clients | `UFUNCTION(Reliable, NetMulticast)` on `SimulateMeleeStrike()`, `BroadcastUpdateAudioLoop()`; `UFUNCTION(Unreliable, NetMulticast)` on `SimulateFuzeFX()`, `SimulateExplosion()` |
| **Template Method** | Base classes define virtual hooks for subclasses | `ASWeapon::FireWeapon()` is PURE_VIRTUAL; `ASUsableActor::OnUsed()` is virtual; `ASGameMode::Killed()` is virtual |
| **Blueprint Native Event** | C++ with Blueprint override points | `UFUNCTION(BlueprintNativeEvent)` on `CheckRelevance()`, `OnStateChanged()`; `UFUNCTION(BlueprintImplementableEvent)` on `FindBotSpawnTransform()`, `K2_SimulateExplosion()`, `MessageReceived()` |

### Style Conventions

| Convention | Evidence |
|---|---|
| **Async/Replication** | All state-changing functions use `Server, Reliable, WithValidation` RPC pattern. Each has `_Implementation` and `_Validate` variants. |
| **Error Handling** | Damage pipeline uses `CanDie()` → `Die()` → `OnDeath()` with validation checks. `ShouldDealDamage()` filters actors before applying damage. |
| **Validation** | Every server RPC has a `_Validate()` method that returns `bool` to prevent cheating. |
| **Hit Replication** | `FTakeHitInfo` struct is replicated via `OnRep_LastTakeHitInfo` for client-side hit effects. |
| **Component Design** | Gameplay features are encapsulated in components: `USCarryObjectComponent` for object carrying, `USCharacterMovementComponent` for speed modifiers. |
| **Config-Driven** | All numeric values exposed as `UPROPERTY(EditDefaultsOnly)` for designer tuning. |
| **Comment Style** | Extensive use of `/* */` block comments for section headers (e.g., `/* Movement */`, `/* Weapons & Inventory */`). |

---

## Similar Implementations

### 1. Similar to `ASWeapon` → `ASWeaponInstant` and `ASFlashlight`

Both `ASWeaponInstant` and `ASFlashlight` extend `ASWeapon` and override `FireWeapon()` and `HandleFiring()`.

- **`ASWeaponInstant`** (`Items/SWeaponInstant.h`): Hit-scan weapon. Overrides `FireWeapon()` to perform line traces, spawn impact effects, and apply damage.
- **`ASFlashlight`** (`Items/SFlashlight.h`): Flashlight tool. Overrides `HandleFiring()` to toggle light on/off instead of firing a projectile.

### 2. Similar to `ASUsableActor` → `ASPickupActor`, `ASBombActor`

All extend `ASUsableActor` and override `OnUsed()`.

- **`ASPickupActor`** (`Items/SPickupActor.h`): Adds respawn logic, active/inactive state.
- **`ASBombActor`** (`Items/SBombActor.h`): Explosive that detonates on timer or damage.
- **`ASWeaponPickup`** (`Items/SWeaponPickup.h`): Gives weapon to player inventory.
- **`ASConsumableActor`** (`Items/SConsumableActor.h`): Restores health/hunger.

### 3. Similar to `ASGameMode` → `ASCoopGameMode`, `ASOpenWorldGameMode`

Both extend `ASGameMode` with different game rules.

- **`ASCoopGameMode`** (`World/SCoopGameMode.h`): Adds match end when all players die, team spawning, scoring for surviving nights.
- **`ASOpenWorldGameMode`** (`World/SOpenWorldGameMode.h`): Disables spectating of other players.

### 4. Similar to `ASBaseCharacter` → `ASCharacter`, `ASZombieCharacter`

Both extend `ASBaseCharacter` with different behaviors.

- **`ASCharacter`** (`Player/SCharacter.h`): Player-controlled. Adds inventory, hunger, camera, input.
- **`ASZombieCharacter`** (`AI/SZombieCharacter.h`): AI-controlled. Adds perception, melee attacks, audio loops.

---

## Context for the Task

### System Overview

The **SurvivalGame** project is a UE4 C++ survival shooter with these interconnected systems:

1. **Player System**: `ASBaseCharacter` → `ASCharacter`. Manages health, damage, sprinting, targeting. `ASCharacter` adds inventory (weapon slots), hunger (decays over time, causes damage at critical), object interaction (focus/use), and camera.

2. **Weapon System**: `ASWeapon` (abstract) → `ASWeaponInstant` (hit-scan), `ASFlashlight` (toggle light). Weapons are owned by `ASCharacter` via `TArray<ASWeapon*> Inventory`. Firing uses server-authoritative RPCs (`ServerStartFire`, `ServerHandleFiring`). `ASWeaponInstant` implements hit-scan with `FireWeapon()` doing line traces, `ProcessInstantHitConfirmed()` for server-side damage, and `SpawnImpactEffects()` for VFX.

3. **AI System**: `ASZombieCharacter` (extends `ASBaseCharacter`) + `ASZombieAIController` (extends `AAIController`). Uses `UPawnSensingComponent` for perception (sight/hearing), Behavior Tree for decision-making, and Blackboard for state. Two bot types: `Passive` (idle until player spotted) and `Patrolling` (patrols waypoints). Melee attacks via `PerformMeleeStrike()`.

4. **Item System**: `ASUsableActor` (abstract) → `ASPickupActor` (respawn logic) → `ASWeaponPickup` (gives weapon), `ASConsumableActor` (restores stats). Also `ASBombActor` (explosive). Interaction via `OnUsed()` called from `ASCharacter::Use()`.

5. **World System**: `ASGameMode` (base) → `ASCoopGameMode`, `ASOpenWorldGameMode`. Manages player spawning, bot spawning (night-only), default inventory, damage rules, mutator chain. `ASGameState` tracks score and day/night cycle. `ASTimeOfDayManager` handles visual day/night transitions.

### Key Code Snippets

**Damage Pipeline (SBaseCharacter.h)**:
```cpp
virtual float TakeDamage(float Damage, struct FDamageEvent const& DamageEvent, 
    class AController* EventInstigator, class AActor* DamageCauser) override;
virtual bool CanDie(float KillingDamage, FDamageEvent const& DamageEvent, 
    AController* Killer, AActor* DamageCauser);
virtual bool Die(float KillingDamage, FDamageEvent const& DamageEvent, 
    AController* Killer, AActor* DamageCauser);
virtual void OnDeath(float KillingDamage, FDamageEvent const& DamageEvent, 
    APawn* PawnInstigator, AActor* DamageCauser);
```

**Weapon Firing RPC Pattern (SWeapon.h)**:
```cpp
UFUNCTION(Reliable, Server, WithValidation)
void ServerStartFire();
void ServerStartFire_Implementation();
bool ServerStartFire_Validate();
```

**Inventory System (SCharacter.h)**:
```cpp
UPROPERTY(Transient, Replicated)
TArray<ASWeapon*> Inventory;

UPROPERTY(Transient, ReplicatedUsing = OnRep_CurrentWeapon)
class ASWeapon* CurrentWeapon;

void SetCurrentWeapon(class ASWeapon* newWeapon, class ASWeapon* LastWeapon = nullptr);
void EquipWeapon(ASWeapon* Weapon);
void AddWeapon(class ASWeapon* Weapon);
void RemoveWeapon(class ASWeapon* Weapon, bool bDestroy);
```

**AI Perception (SZombieCharacter.h)**:
```cpp
UPROPERTY(VisibleAnywhere, Category = "AI")
class UPawnSensingComponent* PawnSensingComp;

UFUNCTION()
void OnSeePlayer(APawn* Pawn);

UFUNCTION()
void OnHearNoise(APawn* PawnInstigator, const FVector& Location, float Volume);
```

**Mutator Chain (SMutator.h)**:
```cpp
ASMutator* NextMutator;  // Next mutator in the chain

UFUNCTION(BlueprintNativeEvent, BlueprintAuthorityOnly)
bool CheckRelevance(AActor* Other);
// Return false to destroy Other. Call Super to process additional mutators.
```

**Day/Night Cycle (SGameState.h)**:
```cpp
UPROPERTY(Replicated)
bool bIsNight;

UPROPERTY(BlueprintReadOnly, Replicated, Category = "TimeOfDay")
int32 ElapsedGameMinutes;

UPROPERTY(EditDefaultsOnly, Category = "TimeOfDay")
float TimeScale;  // 1 real second = X game seconds
```