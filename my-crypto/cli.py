"""
cli.py - 커맨드라인 인터페이스
사용법: python cli.py [명령어]
"""
import argparse
import json
import os
import sys
from blockchain import Blockchain
from wallet import Wallet
from miner import Miner

CHAIN_FILE = "chain_data.json"


def load_blockchain() -> Blockchain:
    if os.path.exists(CHAIN_FILE):
        with open(CHAIN_FILE) as f:
            return Blockchain.from_dict(json.load(f))
    return Blockchain()


def save_blockchain(bc: Blockchain):
    with open(CHAIN_FILE, "w") as f:
        json.dump(bc.to_dict(), f, indent=2)


def cmd_wallet_new(args):
    """새 지갑 생성"""
    w = Wallet()
    print(f"\n🔑 새 지갑 생성됨")
    print(f"   주소:    {w.address}")
    print(f"   공개키:  {w.public_key_hex[:32]}...")
    print(f"   개인키:  {w.private_key_hex[:32]}...")

    if args.save:
        path = args.save
        w.save(path)
        print(f"   저장됨:  {path}")
    else:
        print(f"\n⚠️  지갑을 저장하려면 --save <파일명> 옵션을 사용하세요.")


def cmd_wallet_info(args):
    """지갑 정보 출력"""
    if not os.path.exists(args.wallet):
        print(f"[!] 지갑 파일을 찾을 수 없습니다: {args.wallet}")
        sys.exit(1)
    w = Wallet.load(args.wallet)
    bc = load_blockchain()
    balance = bc.get_balance(w.address)
    print(f"\n💼 지갑 정보")
    print(f"   주소:   {w.address}")
    print(f"   잔액:   {balance:.4f} {bc.COIN_SYMBOL}")


def cmd_send(args):
    """코인 전송"""
    if not os.path.exists(args.wallet):
        print(f"[!] 지갑 파일을 찾을 수 없습니다: {args.wallet}")
        sys.exit(1)

    bc = load_blockchain()
    w = Wallet.load(args.wallet)
    balance = bc.get_balance(w.address)

    print(f"\n💸 전송 준비")
    print(f"   보내는 주소: {w.address}")
    print(f"   받는 주소:   {args.to}")
    print(f"   금액:        {args.amount} {bc.COIN_SYMBOL}")
    print(f"   현재 잔액:   {balance:.4f} {bc.COIN_SYMBOL}")

    if balance < args.amount:
        print(f"\n[!] 잔액 부족! (필요: {args.amount}, 보유: {balance:.4f})")
        sys.exit(1)

    tx = w.create_transaction(args.to, args.amount)
    success = bc.add_transaction(tx)

    if success:
        save_blockchain(bc)
        print(f"\n✅ 트랜잭션 추가됨!")
        print(f"   TX ID: {tx['tx_id']}")
        print(f"   채굴 후 확정됩니다. 'python cli.py mine' 실행하세요.")
    else:
        print(f"\n[!] 트랜잭션 실패")


def cmd_mine(args):
    """채굴 실행"""
    if not os.path.exists(args.wallet):
        print(f"[!] 지갑 파일을 찾을 수 없습니다: {args.wallet}")
        sys.exit(1)

    bc = load_blockchain()
    w = Wallet.load(args.wallet)
    m = Miner(bc, w)

    if not bc.pending_transactions:
        print("\n[i] 대기 중인 트랜잭션이 없습니다. 빈 블록을 채굴합니다.")

    m.mine(verbose=True)
    save_blockchain(bc)


def cmd_balance(args):
    """잔액 조회"""
    bc = load_blockchain()
    balance = bc.get_balance(args.address)
    print(f"\n💰 잔액: {balance:.4f} {bc.COIN_SYMBOL}")
    print(f"   주소: {args.address}")


def cmd_history(args):
    """트랜잭션 내역 조회"""
    bc = load_blockchain()
    history = bc.get_transaction_history(args.address)
    print(f"\n📋 트랜잭션 내역 ({args.address[:20]}...)")
    print(f"   총 {len(history)}건\n")
    for tx in history:
        direction = "← 수신" if tx["recipient"] == args.address else "→ 송신"
        other = tx["sender"] if tx["recipient"] == args.address else tx["recipient"]
        print(f"   [{direction}] {tx['amount']:.4f} {bc.COIN_SYMBOL}  |  블록 #{tx['block_index']}  |  {other[:20]}...")


def cmd_chain(args):
    """블록체인 정보 출력"""
    bc = load_blockchain()
    valid = bc.is_chain_valid()
    print(f"\n⛓  블록체인 정보")
    print(f"   블록 수:          {len(bc.chain)}")
    print(f"   대기 트랜잭션:    {len(bc.pending_transactions)}개")
    print(f"   난이도:           {bc.DIFFICULTY}")
    print(f"   채굴 보상:        {bc.MINING_REWARD} {bc.COIN_SYMBOL}")
    print(f"   무결성:           {'✅ 유효' if valid else '❌ 손상됨'}")

    if args.verbose:
        print(f"\n   블록 목록:")
        for block in bc.chain:
            print(f"   #{block.index:4d}  {block.hash[:20]}...  tx:{len(block.transactions)}")


def cmd_demo(args):
    """데모: 지갑 생성 → 채굴 → 전송 전체 흐름"""
    print("\n🎮 KiroCoin 데모 시작\n")
    bc = Blockchain()

    # 지갑 생성
    alice = Wallet()
    bob = Wallet()
    print(f"👤 Alice: {alice.address}")
    print(f"👤 Bob:   {bob.address}")

    # Alice가 채굴
    print(f"\n⛏  Alice 채굴 중...")
    m = Miner(bc, alice)
    m.mine(verbose=True)

    # Alice → Bob 전송
    print(f"\n💸 Alice → Bob 10 {bc.COIN_SYMBOL} 전송")
    tx = alice.create_transaction(bob.address, 10.0)
    bc.add_transaction(tx)

    # 다시 채굴 (트랜잭션 확정)
    print(f"\n⛏  트랜잭션 확정을 위해 채굴...")
    m.mine(verbose=True)

    # 잔액 확인
    print(f"\n💰 최종 잔액")
    print(f"   Alice: {bc.get_balance(alice.address):.2f} {bc.COIN_SYMBOL}")
    print(f"   Bob:   {bc.get_balance(bob.address):.2f} {bc.COIN_SYMBOL}")

    # 체인 검증
    print(f"\n🔍 체인 무결성: {'✅ 유효' if bc.is_chain_valid() else '❌ 손상됨'}")
    print(f"   총 블록 수: {len(bc.chain)}")


def main():
    parser = argparse.ArgumentParser(
        description=f"🪙  KiroCoin (KRC) - 나만의 블록체인 암호화폐",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python cli.py demo                          # 전체 흐름 데모
  python cli.py wallet new --save my.pem      # 새 지갑 생성
  python cli.py wallet info --wallet my.pem   # 지갑 정보
  python cli.py mine --wallet my.pem          # 채굴
  python cli.py send --wallet my.pem --to <주소> --amount 10
  python cli.py balance <주소>
  python cli.py chain --verbose
        """,
    )
    subparsers = parser.add_subparsers(dest="command")

    # demo
    subparsers.add_parser("demo", help="전체 흐름 데모 실행")

    # wallet
    wallet_parser = subparsers.add_parser("wallet", help="지갑 관리")
    wallet_sub = wallet_parser.add_subparsers(dest="wallet_command")

    w_new = wallet_sub.add_parser("new", help="새 지갑 생성")
    w_new.add_argument("--save", metavar="FILE", help="저장할 파일 경로 (예: my.pem)")

    w_info = wallet_sub.add_parser("info", help="지갑 정보 조회")
    w_info.add_argument("--wallet", required=True, metavar="FILE", help="지갑 파일 경로")

    # mine
    mine_parser = subparsers.add_parser("mine", help="채굴 실행")
    mine_parser.add_argument("--wallet", required=True, metavar="FILE", help="채굴 보상 받을 지갑 파일")

    # send
    send_parser = subparsers.add_parser("send", help="코인 전송")
    send_parser.add_argument("--wallet", required=True, metavar="FILE", help="보내는 지갑 파일")
    send_parser.add_argument("--to", required=True, metavar="ADDRESS", help="받는 주소")
    send_parser.add_argument("--amount", required=True, type=float, metavar="AMOUNT", help="전송 금액")

    # balance
    balance_parser = subparsers.add_parser("balance", help="잔액 조회")
    balance_parser.add_argument("address", help="조회할 주소")

    # history
    history_parser = subparsers.add_parser("history", help="트랜잭션 내역")
    history_parser.add_argument("address", help="조회할 주소")

    # chain
    chain_parser = subparsers.add_parser("chain", help="블록체인 정보")
    chain_parser.add_argument("--verbose", "-v", action="store_true", help="블록 목록 출력")

    args = parser.parse_args()

    if args.command == "demo":
        cmd_demo(args)
    elif args.command == "wallet":
        if args.wallet_command == "new":
            cmd_wallet_new(args)
        elif args.wallet_command == "info":
            cmd_wallet_info(args)
        else:
            wallet_parser.print_help()
    elif args.command == "mine":
        cmd_mine(args)
    elif args.command == "send":
        cmd_send(args)
    elif args.command == "balance":
        cmd_balance(args)
    elif args.command == "history":
        cmd_history(args)
    elif args.command == "chain":
        cmd_chain(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
