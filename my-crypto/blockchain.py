"""
blockchain.py - 핵심 블록체인 로직
"""
import hashlib
import json
import time
from typing import List, Optional


class Block:
    def __init__(
        self,
        index: int,
        transactions: list,
        previous_hash: str,
        nonce: int = 0,
        timestamp: float = None,
    ):
        self.index = index
        self.timestamp = timestamp or time.time()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.compute_hash()

    def compute_hash(self) -> str:
        block_data = json.dumps(
            {
                "index": self.index,
                "timestamp": self.timestamp,
                "transactions": self.transactions,
                "previous_hash": self.previous_hash,
                "nonce": self.nonce,
            },
            sort_keys=True,
        )
        return hashlib.sha256(block_data.encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Block":
        block = cls(
            index=data["index"],
            transactions=data["transactions"],
            previous_hash=data["previous_hash"],
            nonce=data["nonce"],
            timestamp=data["timestamp"],
        )
        block.hash = data["hash"]
        return block

    def __repr__(self):
        return f"<Block #{self.index} hash={self.hash[:12]}...>"


class Blockchain:
    # 채굴 난이도 (앞에 0이 몇 개 붙어야 하는지)
    DIFFICULTY = 3
    # 채굴 보상 (단위: MatthewCoin)
    MINING_REWARD = 50.0
    # 코인 이름
    COIN_NAME = "MATTHEW Coin"
    COIN_SYMBOL = "MTW"

    def __init__(self):
        self.chain: List[Block] = []
        self.pending_transactions: list = []
        self._create_genesis_block()

    def _create_genesis_block(self):
        """제네시스 블록 (첫 번째 블록) 생성"""
        genesis = Block(
            index=0,
            transactions=[],
            previous_hash="0" * 64,
            nonce=0,
            timestamp=0,
        )
        genesis.hash = genesis.compute_hash()
        self.chain.append(genesis)

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    def add_transaction(self, transaction: dict) -> bool:
        """
        트랜잭션을 대기 풀에 추가.
        transaction = {
            "sender": <주소>,
            "recipient": <주소>,
            "amount": <금액>,
            "signature": <서명>,
            "public_key": <공개키>,
            "tx_id": <트랜잭션 ID>
        }
        """
        required = ["sender", "recipient", "amount"]
        if not all(k in transaction for k in required):
            return False
        if transaction["amount"] <= 0:
            return False
        # COINBASE 트랜잭션(채굴 보상)은 서명 검증 생략
        if transaction["sender"] != "COINBASE":
            from wallet import Wallet
            if not Wallet.verify_transaction(transaction):
                return False
        # 잔액 확인 (COINBASE 제외)
        if transaction["sender"] != "COINBASE":
            balance = self.get_balance(transaction["sender"])
            if balance < transaction["amount"]:
                return False
        self.pending_transactions.append(transaction)
        return True

    def mine_pending_transactions(self, miner_address: str) -> Optional[Block]:
        """
        대기 중인 트랜잭션을 채굴하여 새 블록 생성.
        채굴 성공 시 보상 트랜잭션 추가.
        """
        # 채굴 보상 트랜잭션
        reward_tx = {
            "sender": "COINBASE",
            "recipient": miner_address,
            "amount": self.MINING_REWARD,
            "tx_id": f"coinbase-{self.last_block.index + 1}",
        }
        transactions = self.pending_transactions.copy()
        transactions.append(reward_tx)

        new_block = Block(
            index=self.last_block.index + 1,
            transactions=transactions,
            previous_hash=self.last_block.hash,
        )

        # 작업 증명 (Proof of Work)
        self._proof_of_work(new_block)

        self.chain.append(new_block)
        self.pending_transactions = []
        return new_block

    def _proof_of_work(self, block: Block):
        """난이도에 맞는 해시를 찾을 때까지 nonce 증가"""
        target = "0" * self.DIFFICULTY
        block.nonce = 0
        block.hash = block.compute_hash()
        while not block.hash.startswith(target):
            block.nonce += 1
            block.hash = block.compute_hash()

    def get_balance(self, address: str) -> float:
        """특정 주소의 잔액 계산"""
        balance = 0.0
        for block in self.chain:
            for tx in block.transactions:
                if tx["recipient"] == address:
                    balance += tx["amount"]
                if tx["sender"] == address:
                    balance -= tx["amount"]
        return balance

    def is_chain_valid(self) -> bool:
        """블록체인 무결성 검증"""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            # 해시 재계산 검증
            if current.hash != current.compute_hash():
                print(f"[!] 블록 #{current.index} 해시 불일치")
                return False

            # 이전 블록 해시 연결 검증
            if current.previous_hash != previous.hash:
                print(f"[!] 블록 #{current.index} 이전 해시 불일치")
                return False

            # 작업 증명 검증
            if not current.hash.startswith("0" * self.DIFFICULTY):
                print(f"[!] 블록 #{current.index} 작업 증명 실패")
                return False

        return True

    def get_transaction_history(self, address: str) -> list:
        """특정 주소의 트랜잭션 내역 조회"""
        history = []
        for block in self.chain:
            for tx in block.transactions:
                if tx["sender"] == address or tx["recipient"] == address:
                    history.append({**tx, "block_index": block.index})
        return history

    def to_dict(self) -> dict:
        return {
            "chain": [b.to_dict() for b in self.chain],
            "pending_transactions": self.pending_transactions,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Blockchain":
        bc = cls.__new__(cls)
        bc.chain = [Block.from_dict(b) for b in data["chain"]]
        bc.pending_transactions = data["pending_transactions"]
        return bc
