"""On-chain anchor read/write. See SCHEMA.md §4."""


def write_hash(
    agent_id: int,
    payload_hash: bytes,
    signature: bytes,
    rpc_url: str,
    contract: str,
    private_key: str,
) -> str:
    # TODO: implement per SCHEMA.md §4
    raise NotImplementedError


def read_hash(
    agent_id: int,
    payload_hash: bytes,
    rpc_url: str,
    contract: str,
) -> dict | None:
    # TODO: implement per SCHEMA.md §4
    raise NotImplementedError
