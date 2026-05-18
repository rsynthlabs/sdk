// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {MessageHashUtils} from "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

/// @title ExecutionLog — anchor robot execution payload hashes on-chain.
/// @notice See SCHEMA.md §4.
contract ExecutionLog {
    using MessageHashUtils for bytes32;

    error InvalidSigner();

    event ExecutionRecorded(
        address indexed signer,
        bytes32 indexed payloadHash,
        uint256 blockTimestamp
    );

    function record(bytes32 payloadHash, bytes calldata signature) external {
        address signer = ECDSA.recover(
            payloadHash.toEthSignedMessageHash(),
            signature
        );
        if (signer == address(0)) revert InvalidSigner();
        emit ExecutionRecorded(signer, payloadHash, block.timestamp);
    }
}
