# Specification: <project>

What must stay true (invariants), what happens when things go wrong (failure modes), and behavior that is planned but not built.
It does not repeat wire formats or command references: name the normative doc (for example `docs/api.md`) and change it in the
same commit as the behavior.

## 1. Components

<!-- Modules and how a request or command flows through them, in a few lines. Link the architecture doc if there is one. -->

## 2. Invariants

Tests and reviews cite these by number. Changing one needs operator approval.

| # | Invariant |
|---|---|
| I1 | <!-- A property that must always hold, stated so a test can check it. --> |

## 3. Failure modes (current behavior)

| Situation | Behavior | Where specified |
|---|---|---|
| <!-- what goes wrong --> | <!-- status code, exit code or message --> | <!-- doc or file --> |

## 4. Planned behavior (not implemented)

<!-- New behavior goes here before its plan item starts, and moves up into the sections above when built. -->
