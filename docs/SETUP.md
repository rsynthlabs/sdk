# SETUP — scaffold spec for Claude Code

This file is a **specification for an LLM-assisted scaffolding pass**, not user-facing documentation. Once the repository is scaffolded per this spec, this file can be deleted or moved to `docs/`.

Goal: produce a working monorepo skeleton for the rsynth Verifiable Robot Execution SDK. **Empty interfaces, not implementations.** Implementation comes later.

---

## Stack

- **Python 3.11+** — client SDK. Lives in `sdk/`.
- **Solidity 0.8.24+ with Foundry** — on-chain contracts. Lives in `contracts/`.
- **TypeScript (Node 20+)** — optional tooling (deploy scripts, indexer). May live alongside Foundry in `contracts/script/` or `tooling/` if needed; do not over-provision.
- **No CI yet.** No GitHub Actions, no Husky, no pre-commit hooks. Add later.

## Target tree

```
sdk/
├── pyproject.toml
├── README.md
├── src/
│   └── rsynth/
│       ├── __init__.py
│       ├── payload.py        # Payload dataclass + canonical_bytes()
│       ├── sign.py           # sign(), verify() — EIP-191 over canonical bytes
│       ├── anchor.py         # write_hash(), read_hash() — contract interaction
│       └── errors.py
└── tests/
    └── __init__.py

contracts/
├── foundry.toml
├── README.md
├── src/
│   └── ExecutionLog.sol      # See SCHEMA.md §4 for interface
├── test/
│   └── ExecutionLog.t.sol
└── script/
    └── Deploy.s.sol

examples/
├── README.md
└── lerobot_eval/
    └── README.md             # Placeholder: hook from a LeRobot eval loop into rsynth SDK

.gitignore                    # Standard Python + Foundry ignores
LICENSE                       # MIT, copyright "rsynth"
README.md                     # Already provided — do not overwrite
SCHEMA.md                     # Already provided — do not overwrite
```

## Initialization commands

Run in this order, from repo root:

```bash
# Python — src-layout package
mkdir -p sdk/src/rsynth sdk/tests
cd sdk
python3 -m venv .venv
# (do NOT activate or install anything; just have venv ready)
cd ..

# Foundry
mkdir -p contracts
cd contracts
forge init --no-git --no-commit .
# forge init creates src/, test/, script/, foundry.toml — keep, then replace the Counter example
rm -f src/Counter.sol test/Counter.t.sol script/Counter.s.sol
cd ..
```

After Foundry init, replace `Counter.*` with `ExecutionLog.*` stubs (see below).

## File-by-file content

### `sdk/pyproject.toml`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "rsynth"
version = "0.0.1"
description = "Verifiable Robot Execution SDK — sign payloads, anchor proofs on Base."
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [{ name = "rsynth" }]
dependencies = [
  "eth-account>=0.13.0",
  "web3>=7.0.0",
  "pydantic>=2.0.0",
]

[project.urls]
Homepage = "https://rsynth.ai"
Repository = "https://github.com/rsynthlabs/sdk"

[tool.hatch.build.targets.wheel]
packages = ["src/rsynth"]
```

### `sdk/src/rsynth/__init__.py`

```python
"""rsynth — Verifiable Robot Execution SDK."""

__version__ = "0.0.1"
```

### `sdk/src/rsynth/payload.py`

Module docstring at top: brief, points to `SCHEMA.md`.

Define:
- `Outcome` — `enum.Enum` with `SUCCESS`, `PARTIAL`, `FAIL`.
- `Metrics` — `pydantic.BaseModel` with `rmse: float`, `jerk: float`, `end_variance: float`.
- `Payload` — `pydantic.BaseModel` with every field from SCHEMA.md §1.
- `def canonical_bytes(payload: Payload) -> bytes:` — body raises `NotImplementedError` for now, with `# TODO: implement per SCHEMA.md §2`.
- `def payload_hash(payload: Payload) -> bytes:` — same, `NotImplementedError` + TODO comment referencing SCHEMA.md §2.

No implementations. Type signatures and TODOs only.

### `sdk/src/rsynth/sign.py`

Module docstring: references SCHEMA.md §3.

Define:
- `def sign(payload: Payload, private_key: str) -> bytes:` — `NotImplementedError`.
- `def verify(payload: Payload, signature: bytes, expected_signer: str) -> bool:` — `NotImplementedError`.

### `sdk/src/rsynth/anchor.py`

Module docstring: references SCHEMA.md §4.

Define:
- `def write_hash(agent_id: int, payload_hash: bytes, signature: bytes, rpc_url: str, contract: str, private_key: str) -> str:` — `NotImplementedError`. Returns transaction hash.
- `def read_hash(agent_id: int, payload_hash: bytes, rpc_url: str, contract: str) -> dict | None:` — `NotImplementedError`. Returns event data or `None`.

### `sdk/src/rsynth/errors.py`

```python
class RsynthError(Exception):
    """Base class for rsynth SDK errors."""

class InvalidPayloadError(RsynthError):
    pass

class SignatureError(RsynthError):
    pass

class AnchorError(RsynthError):
    pass
```

### `sdk/README.md`

Short — 10–15 lines. Same voice as root `README.md` (terse, lowercase, declarative). Cover: what the package is (one sentence), install (`pip install -e .` for dev), reference to root `SCHEMA.md`. No examples yet.

### `sdk/tests/__init__.py`

Empty file.

### `contracts/foundry.toml`

```toml
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
solc_version = "0.8.24"
optimizer = true
optimizer_runs = 200
```

### `contracts/src/ExecutionLog.sol`

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title ExecutionLog — anchor robot execution payload hashes on-chain.
/// @notice See SCHEMA.md §4. This is a scaffold; verification logic is not yet implemented.
contract ExecutionLog {
    event ExecutionRecorded(
        uint256 indexed agentId,
        bytes32 indexed payloadHash,
        uint256 blockTimestamp
    );

    /// @notice Anchor a signed payload hash. Reverts if signature does not match
    ///         the address registered for `agentId` in the ERC-8004 registry.
    /// @dev    Implementation pending. Currently no-op except event emission.
    function record(
        uint256 agentId,
        bytes32 payloadHash,
        bytes calldata signature
    ) external {
        // TODO: ERC-8004 registry lookup + EIP-191 recover + match check.
        // For now, emit unconditionally so off-chain tooling can be tested.
        signature; // silence unused-var warning
        emit ExecutionRecorded(agentId, payloadHash, block.timestamp);
    }
}
```

### `contracts/test/ExecutionLog.t.sol`

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/ExecutionLog.sol";

contract ExecutionLogTest is Test {
    ExecutionLog log;

    function setUp() public {
        log = new ExecutionLog();
    }

    function test_emits_event_on_record() public {
        bytes32 hash = keccak256("test");
        vm.expectEmit(true, true, false, false);
        emit ExecutionLog.ExecutionRecorded(10311, hash, 0);
        log.record(10311, hash, "");
    }
}
```

### `contracts/script/Deploy.s.sol`

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/ExecutionLog.sol";

contract Deploy is Script {
    function run() external returns (ExecutionLog) {
        vm.startBroadcast();
        ExecutionLog log = new ExecutionLog();
        vm.stopBroadcast();
        return log;
    }
}
```

### `contracts/README.md`

Short — purpose, `forge build`, `forge test`, deploy command stub. Voice consistent with root.

### `examples/README.md`

One paragraph. "Reference integrations live here. First target: LeRobot eval pipeline → rsynth SDK → on-chain anchor."

### `examples/lerobot_eval/README.md`

One paragraph. "Hook from a LeRobot eval loop. Pending implementation alongside SDK v0.1."

### `.gitignore`

Standard combined:

```
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
build/
dist/

# Foundry
out/
cache/
broadcast/

# OS / editors
.DS_Store
.idea/
.vscode/

# Env
.env
.env.local
```

### `LICENSE`

Standard MIT. Copyright holder: `rsynth`. Year: 2026.

---

## Constraints — what NOT to do

- **No marketing prose** in any README beyond what's specified. The root `README.md` is the marketing surface and it's already written.
- **No emojis** anywhere — in code, comments, or docs.
- **No CI configuration** (no `.github/workflows/`).
- **No detailed implementation** of `canonical_bytes`, `sign`, `verify`, `anchor`. Stubs only. The point of this pass is structure, not logic.
- **Do not modify** the existing root `README.md` or `SCHEMA.md`.
- **Do not add** dependencies beyond those listed in `pyproject.toml`.

## Voice for any README you do generate

Lowercase, terse, declarative. Match the root `README.md`. No headlines like "🚀 Welcome!" — none of that.

## After scaffolding

When the tree is in place and all files match this spec, run:

```bash
git add .
git commit -m "scaffold: monorepo skeleton (python sdk, foundry contracts, examples)"
git push
```

That's the deliverable.

---

## Foundry: forge-std `event log(string)` collision

`forge-std/Test.sol` declares `event log(string)` (and other `log*` variants). In Solidity, events, state variables, and functions share a single per-contract namespace, and inherited identifiers count too — so any contract that inherits `Test` and declares its own `log` (as an event, a state variable, or anything else) will fail to compile with:

```
DeclarationError: Identifier already declared.
```

When naming identifiers in a forge-std-importing contract, avoid `log` — pick something descriptive (e.g. `ExecutionRecorded` for an event, `executionLog` for a state variable holding a contract instance).
