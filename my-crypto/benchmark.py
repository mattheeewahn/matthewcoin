"""
1분 동안 얼마나 채굴되는지 측정
"""
import time
from blockchain import Blockchain
from wallet import Wallet
from miner import Miner

bc = Blockchain()
w = Wallet()
m = Miner(bc, w)

print(f"⛏  1분 채굴 벤치마크 시작 (난이도: {bc.DIFFICULTY})")
print(f"   보상: {bc.MINING_REWARD} {bc.COIN_SYMBOL} / 블록\n")

start = time.time()
deadline = start + 60
blocks = 0
total_nonce = 0

while time.time() < deadline:
    remaining = deadline - time.time()
    block = bc.mine_pending_transactions(w.address)
    blocks += 1
    total_nonce += block.nonce
    elapsed = time.time() - start
    print(f"  블록 #{block.index:3d}  nonce={block.nonce:7,}  {elapsed:.1f}s 경과  (남은 시간: {max(0, 60-elapsed):.0f}s)")

total_earned = bc.get_balance(w.address)
avg_nonce = total_nonce / blocks if blocks else 0
avg_time = 60 / blocks if blocks else 0

print(f"\n{'='*50}")
print(f"📊 결과 (1분)")
print(f"   채굴된 블록:     {blocks}개")
print(f"   획득한 코인:     {total_earned:.0f} {bc.COIN_SYMBOL}")
print(f"   평균 nonce:      {avg_nonce:,.0f}")
print(f"   블록당 평균 시간: {avg_time:.2f}초")
print(f"   초당 해시 속도:  {total_nonce/60:,.0f} H/s")
