"""
node.py - P2P 네트워크 노드 (간단한 HTTP 기반)
다른 노드와 블록체인을 동기화합니다.
"""
import json
import requests
from typing import Set
from blockchain import Blockchain, Block


class Node:
    def __init__(self, blockchain: Blockchain):
        self.blockchain = blockchain
        self.peers: Set[str] = set()  # "http://host:port" 형태

    def register_peer(self, address: str):
        """피어 노드 등록"""
        self.peers.add(address.rstrip("/"))
        print(f"[+] 피어 등록: {address}")

    def remove_peer(self, address: str):
        self.peers.discard(address.rstrip("/"))

    def broadcast_transaction(self, transaction: dict):
        """새 트랜잭션을 모든 피어에 전파"""
        for peer in self.peers:
            try:
                requests.post(
                    f"{peer}/transactions/new",
                    json=transaction,
                    timeout=3,
                )
            except requests.RequestException:
                print(f"[!] 피어 연결 실패: {peer}")

    def broadcast_block(self, block: Block):
        """새 블록을 모든 피어에 전파"""
        for peer in self.peers:
            try:
                requests.post(
                    f"{peer}/blocks/new",
                    json=block.to_dict(),
                    timeout=3,
                )
            except requests.RequestException:
                print(f"[!] 피어 연결 실패: {peer}")

    def sync_chain(self) -> bool:
        """
        가장 긴 유효한 체인으로 동기화 (Nakamoto Consensus).
        더 긴 체인을 발견하면 교체하고 True 반환.
        """
        longest_chain = None
        max_length = len(self.blockchain.chain)

        for peer in self.peers:
            try:
                response = requests.get(f"{peer}/chain", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    length = data["length"]
                    chain_data = data["chain"]

                    if length > max_length:
                        # 체인 유효성 검증
                        candidate = Blockchain.from_dict(
                            {"chain": chain_data, "pending_transactions": []}
                        )
                        if candidate.is_chain_valid():
                            max_length = length
                            longest_chain = candidate.chain
            except requests.RequestException:
                print(f"[!] 피어 연결 실패: {peer}")

        if longest_chain:
            self.blockchain.chain = longest_chain
            print(f"[✓] 체인 동기화 완료 (길이: {max_length})")
            return True

        print("[i] 이미 최신 체인입니다.")
        return False

    def receive_block(self, block_data: dict) -> bool:
        """
        다른 노드로부터 새 블록 수신.
        유효하면 체인에 추가.
        """
        block = Block.from_dict(block_data)
        last = self.blockchain.last_block

        # 연속된 블록인지 확인
        if block.previous_hash != last.hash:
            # 체인이 뒤처진 경우 전체 동기화
            self.sync_chain()
            return False

        # 해시 유효성 확인
        if block.hash != block.compute_hash():
            return False

        # 작업 증명 확인
        if not block.hash.startswith("0" * self.blockchain.DIFFICULTY):
            return False

        self.blockchain.chain.append(block)
        # 포함된 트랜잭션은 대기 풀에서 제거
        included_ids = {tx.get("tx_id") for tx in block.transactions}
        self.blockchain.pending_transactions = [
            tx for tx in self.blockchain.pending_transactions
            if tx.get("tx_id") not in included_ids
        ]
        return True
