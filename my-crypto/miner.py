"""
miner.py - 채굴 로직
"""
import time
from blockchain import Blockchain
from wallet import Wallet


class Miner:
    def __init__(self, blockchain: Blockchain, wallet: Wallet):
        self.blockchain = blockchain
        self.wallet = wallet
        self.blocks_mined = 0

    def mine(self, verbose: bool = True) -> dict:
        """
        대기 중인 트랜잭션을 채굴.
        보상: {MINING_REWARD} KRC
        """
        pending_count = len(self.blockchain.pending_transactions)

        if verbose:
            print(f"\n⛏  채굴 시작...")
            print(f"   채굴자 주소: {self.wallet.address}")
            print(f"   대기 트랜잭션: {pending_count}개")
            print(f"   난이도: {'0' * self.blockchain.DIFFICULTY}...")

        start_time = time.time()
        block = self.blockchain.mine_pending_transactions(self.wallet.address)
        elapsed = time.time() - start_time

        self.blocks_mined += 1

        if verbose:
            print(f"\n✅ 블록 #{block.index} 채굴 성공!")
            print(f"   해시: {block.hash}")
            print(f"   Nonce: {block.nonce:,}")
            print(f"   소요 시간: {elapsed:.2f}초")
            print(f"   보상: {self.blockchain.MINING_REWARD} {self.blockchain.COIN_SYMBOL}")
            print(f"   현재 잔액: {self.blockchain.get_balance(self.wallet.address):.2f} {self.blockchain.COIN_SYMBOL}")

        return {
            "block_index": block.index,
            "hash": block.hash,
            "nonce": block.nonce,
            "elapsed_seconds": round(elapsed, 4),
            "reward": self.blockchain.MINING_REWARD,
            "transactions_included": len(block.transactions),
        }
