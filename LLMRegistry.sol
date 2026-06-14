// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract LLMRegistry {
    // 儲存對話紀錄：Prompt Hash -> Output Hash
    mapping(bytes32 => bytes32) public auditTrail;
    address public serverAdmin;

    event TaskRecorded(bytes32 indexed promptHash, bytes32 indexed outputHash, uint256 timestamp);

    constructor() {
        serverAdmin = msg.sender; 
    }

    // 僅允許 AI 伺服器地址呼叫
    function recordTask(bytes32 promptHash, bytes32 outputHash) public {
        require(msg.sender == serverAdmin, "Only authorized server can record!");
        auditTrail[promptHash] = outputHash;
        emit TaskRecorded(promptHash, outputHash, block.timestamp);
    }
}