"""
server.py - MATTHEW Coin 웹 서버
라즈베리파이에서 실행: python server.py
"""
import json
import os
import time
from flask import Flask, jsonify, request, render_template, abort
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from blockchain import Blockchain, Block
from wallet import Wallet

app = Flask(__name__)
CHAIN_FILE = "mtw_chain.json"


def load_bc():
    if os.path.exists(CHAIN_FILE):
        with open(CHAIN_FILE) as f:
            return Blockchain.from_dict(json.load(f))
    return Blockchain()


def save_bc(bc):
    with open(CHAIN_FILE, "w") as f:
        json.dump(bc.to_dict(), f, indent=2)


bc = load_bc()


# ── 페이지 ────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


# ── 지갑 API ──────────────────────────────────────────────
@app.route("/api/wallet/new")
def api_wallet_new():
    """새 지갑 생성 — PEM을 클라이언트에 반환 (서버에 저장 안 함)"""
    w = Wallet()
    pem = w._private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    return jsonify({"address": w.address, "public_key": w.public_key_hex, "pem": pem})


@app.route("/api/wallet/load", methods=["POST"])
def api_wallet_load():
    """PEM 업로드 → 주소/공개키 반환"""
    pem_str = request.get_json().get("pem", "")
    try:
        priv = serialization.load_pem_private_key(
            pem_str.encode(), password=None, backend=default_backend())
        w = Wallet(private_key=priv)
        return jsonify({"address": w.address, "public_key": w.public_key_hex})
    except Exception as e:
        abort(400, str(e))


@app.route("/api/balance/<address>")
def api_balance(address):
    return jsonify({"address": address, "balance": bc.get_balance(address),
                    "symbol": bc.COIN_SYMBOL})


@app.route("/api/history/<address>")
def api_history(address):
    return jsonify(bc.get_transaction_history(address))


# ── 트랜잭션 API ──────────────────────────────────────────
@app.route("/api/tx/sign_and_send", methods=["POST"])
def api_sign_and_send():
    """PEM + 수신자 + 금액 → 서버에서 서명 후 대기 풀 추가"""
    data = request.get_json()
    try:
        priv = serialization.load_pem_private_key(
            data["pem"].encode(), password=None, backend=default_backend())
        w = Wallet(private_key=priv)
        tx = w.create_transaction(data["recipient"], float(data["amount"]))
        if bc.add_transaction(tx):
            save_bc(bc)
            return jsonify({"ok": True, "tx_id": tx["tx_id"]}), 201
        abort(400, "트랜잭션 실패 (잔액 부족 또는 서명 오류)")
    except Exception as e:
        abort(400, str(e))


@app.route("/api/tx/pending")
def api_pending():
    return jsonify(bc.pending_transactions)


# ── 채굴 API ──────────────────────────────────────────────
@app.route("/api/mine/work")
def api_mine_work():
    """클라이언트에게 채굴 작업(블록 템플릿) 제공"""
    miner_address = request.args.get("address", "")
    if not miner_address:
        abort(400, "address 필요")
    reward_tx = {
        "sender": "COINBASE",
        "recipient": miner_address,
        "amount": bc.MINING_REWARD,
        "tx_id": f"coinbase-{bc.last_block.index + 1}",
    }
    transactions = bc.pending_transactions.copy()
    transactions.append(reward_tx)
    ts = time.time()

    base_block = {
        "index": bc.last_block.index + 1,
        "timestamp": ts,
        "transactions": transactions,
        "previous_hash": bc.last_block.hash,
    }

    # JS가 nonce만 바꿔서 해시를 계산할 수 있도록
    # prefix + str(nonce) + suffix 형태로 분리해서 내려줌
    # json.dumps(sort_keys=True) 결과에서 "nonce" 키 위치를 찾아 분리
    full = json.dumps({**base_block, "nonce": 0}, sort_keys=True)
    # "nonce": 0 의 위치를 찾아서 앞/뒤로 분리
    marker = '"nonce": 0'
    idx = full.index(marker)
    prefix = full[:idx + len('"nonce": ')]   # '..."nonce": ' 까지
    suffix = full[idx + len(marker):]         # 0 이후 부분

    return jsonify({
        "index": bc.last_block.index + 1,
        "transactions": transactions,
        "previous_hash": bc.last_block.hash,
        "difficulty": bc.DIFFICULTY,
        "timestamp": ts,
        "hash_prefix": prefix,   # JS: prefix + nonce + suffix 로 해시 계산
        "hash_suffix": suffix,
    })


@app.route("/api/mine", methods=["POST"])
def api_mine():
    """클라이언트가 PoW 완료한 블록 제출 → 검증 후 체인 추가"""
    data = request.get_json()
    block_data = data.get("block")
    if not block_data:
        abort(400, "block 없음")

    # JS가 보낸 hash 를 prefix+nonce+suffix 로 직접 재계산해서 검증
    # timestamp 부동소수점 오차 문제를 피하기 위해
    # 서버도 동일한 방식(prefix+nonce+suffix)으로 검증
    hash_prefix = data.get("hash_prefix", "")
    hash_suffix = data.get("hash_suffix", "")
    submitted_hash = block_data.get("hash", "")
    nonce = block_data.get("nonce", 0)

    if hash_prefix and hash_suffix:
        # JS와 동일한 방식으로 재계산
        import hashlib
        block_str = hash_prefix + str(nonce) + hash_suffix
        recomputed = hashlib.sha256(block_str.encode()).hexdigest()
    else:
        # fallback: Block.compute_hash
        block = Block.from_dict(block_data)
        recomputed = block.compute_hash()

    if submitted_hash != recomputed:
        abort(400, f"해시 불일치 | 제출={submitted_hash[:16]} | 재계산={recomputed[:16]}")

    if not submitted_hash.startswith("0" * bc.DIFFICULTY):
        abort(400, "작업 증명 부족")

    # previous_hash 검증
    if block_data.get("previous_hash") != bc.last_block.hash:
        abort(400, "이전 해시 불일치 — 다시 시도하세요")

    # 체인에 추가 (hash 는 JS가 계산한 값 그대로 사용)
    from blockchain import Block as B
    block = B.from_dict(block_data)
    block.hash = submitted_hash  # JS가 계산한 hash 사용
    bc.chain.append(block)
    included = {tx.get("tx_id") for tx in block.transactions}
    bc.pending_transactions = [
        tx for tx in bc.pending_transactions
        if tx.get("tx_id") not in included
    ]
    save_bc(bc)
    return jsonify({"ok": True, "block_index": block.index}), 201


# ── 체인 API ──────────────────────────────────────────────
@app.route("/api/chain")
def api_chain():
    return jsonify({
        "chain": [b.to_dict() for b in bc.chain],
        "length": len(bc.chain),
        "difficulty": bc.DIFFICULTY,
        "mining_reward": bc.MINING_REWARD,
        "coin": bc.COIN_NAME,
        "symbol": bc.COIN_SYMBOL,
    })


@app.route("/api/chain/latest")
def api_chain_latest():
    n = int(request.args.get("n", 10))
    blocks = bc.chain[-n:]
    return jsonify({
        "blocks": [b.to_dict() for b in reversed(blocks)],
        "total": len(bc.chain),
        "pending": len(bc.pending_transactions),
        "valid": bc.is_chain_valid(),
        "difficulty": bc.DIFFICULTY,
        "mining_reward": bc.MINING_REWARD,
    })


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=5000)
    p.add_argument("--host", default="0.0.0.0")
    args = p.parse_args()
    print(f"\nMATTHEW Coin 서버 시작  →  http://{args.host}:{args.port}")
    print(f"난이도: {bc.DIFFICULTY}  보상: {bc.MINING_REWARD} MTW\n")
    app.run(host=args.host, port=args.port, debug=False)
