"""
api.py - Flask REST API 서버
"""
import json
import os
from flask import Flask, jsonify, request, abort
from blockchain import Blockchain
from wallet import Wallet
from miner import Miner
from node import Node

app = Flask(__name__)

# ── 전역 상태 ──────────────────────────────────────────────
CHAIN_FILE = "chain_data.json"
blockchain = Blockchain()
node = Node(blockchain)

# 서버 지갑 (채굴 보상 수신용)
if os.path.exists("server_wallet.pem"):
    server_wallet = Wallet.load("server_wallet.pem")
else:
    server_wallet = Wallet()
    server_wallet.save("server_wallet.pem")

miner = Miner(blockchain, server_wallet)

# 체인 파일이 있으면 로드
if os.path.exists(CHAIN_FILE):
    with open(CHAIN_FILE) as f:
        blockchain_data = json.load(f)
    blockchain = Blockchain.from_dict(blockchain_data)
    node.blockchain = blockchain
    miner.blockchain = blockchain
    print(f"[✓] 체인 로드됨 (블록 수: {len(blockchain.chain)})")


def save_chain():
    with open(CHAIN_FILE, "w") as f:
        json.dump(blockchain.to_dict(), f, indent=2)


# ── 엔드포인트 ─────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "coin": blockchain.COIN_NAME,
        "symbol": blockchain.COIN_SYMBOL,
        "blocks": len(blockchain.chain),
        "pending_transactions": len(blockchain.pending_transactions),
        "difficulty": blockchain.DIFFICULTY,
        "mining_reward": blockchain.MINING_REWARD,
    })


@app.route("/chain", methods=["GET"])
def get_chain():
    return jsonify({
        "chain": [b.to_dict() for b in blockchain.chain],
        "length": len(blockchain.chain),
        "is_valid": blockchain.is_chain_valid(),
    })


@app.route("/blocks/<int:index>", methods=["GET"])
def get_block(index):
    if index >= len(blockchain.chain):
        abort(404, "블록을 찾을 수 없습니다.")
    return jsonify(blockchain.chain[index].to_dict())


@app.route("/transactions/new", methods=["POST"])
def new_transaction():
    data = request.get_json()
    required = ["sender", "recipient", "amount", "signature", "public_key"]
    if not all(k in data for k in required):
        abort(400, "필수 필드 누락")

    success = blockchain.add_transaction(data)
    if not success:
        abort(400, "트랜잭션 유효하지 않음 (잔액 부족 또는 서명 오류)")

    node.broadcast_transaction(data)
    save_chain()
    return jsonify({"message": "트랜잭션 추가됨", "tx_id": data.get("tx_id")}), 201


@app.route("/transactions/pending", methods=["GET"])
def pending_transactions():
    return jsonify({
        "pending": blockchain.pending_transactions,
        "count": len(blockchain.pending_transactions),
    })


@app.route("/mine", methods=["POST"])
def mine():
    """채굴 실행 (POST body에 miner_address 선택적)"""
    data = request.get_json(silent=True) or {}
    miner_address = data.get("miner_address", server_wallet.address)

    # 임시로 채굴자 주소 변경
    temp_miner = Miner(blockchain, server_wallet)
    temp_miner.wallet.address = miner_address  # 주소만 교체

    block = blockchain.mine_pending_transactions(miner_address)
    save_chain()
    node.broadcast_block(block)

    return jsonify({
        "message": "채굴 성공!",
        "block": block.to_dict(),
        "reward": blockchain.MINING_REWARD,
        "miner": miner_address,
    }), 200


@app.route("/wallet/new", methods=["GET"])
def new_wallet():
    """새 지갑 생성"""
    w = Wallet()
    return jsonify({
        "address": w.address,
        "public_key": w.public_key_hex,
        "private_key": w.private_key_hex,
        "warning": "개인키를 안전하게 보관하세요! 분실 시 복구 불가.",
    })


@app.route("/balance/<address>", methods=["GET"])
def get_balance(address):
    balance = blockchain.get_balance(address)
    return jsonify({
        "address": address,
        "balance": balance,
        "symbol": blockchain.COIN_SYMBOL,
    })


@app.route("/history/<address>", methods=["GET"])
def get_history(address):
    history = blockchain.get_transaction_history(address)
    return jsonify({
        "address": address,
        "transactions": history,
        "count": len(history),
    })


@app.route("/peers", methods=["GET"])
def get_peers():
    return jsonify({"peers": list(node.peers)})


@app.route("/peers/register", methods=["POST"])
def register_peer():
    data = request.get_json()
    peer = data.get("peer")
    if not peer:
        abort(400, "peer 주소 필요")
    node.register_peer(peer)
    return jsonify({"message": f"피어 등록됨: {peer}"}), 201


@app.route("/peers/sync", methods=["POST"])
def sync():
    replaced = node.sync_chain()
    save_chain()
    return jsonify({
        "message": "체인 교체됨" if replaced else "이미 최신 체인",
        "chain_length": len(blockchain.chain),
    })


@app.route("/blocks/new", methods=["POST"])
def receive_block():
    block_data = request.get_json()
    success = node.receive_block(block_data)
    if success:
        save_chain()
        return jsonify({"message": "블록 수락됨"}), 201
    return jsonify({"message": "블록 거부됨"}), 400


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="KiroCoin 노드 실행")
    parser.add_argument("--port", type=int, default=5000, help="포트 번호 (기본: 5000)")
    parser.add_argument("--host", default="0.0.0.0", help="호스트 (기본: 0.0.0.0)")
    args = parser.parse_args()

    print(f"\n🪙  {blockchain.COIN_NAME} ({blockchain.COIN_SYMBOL}) 노드 시작")
    print(f"   주소: http://{args.host}:{args.port}")
    print(f"   서버 지갑: {server_wallet.address}\n")
    app.run(host=args.host, port=args.port, debug=False)
