# 🪙 KiroCoin (KRC)

나만의 블록체인 암호화폐입니다.

## 구조

```
my-crypto/
├── blockchain.py   # 블록 & 체인 핵심 로직
├── wallet.py       # 지갑 (SECP256K1 키 쌍, ECDSA 서명)
├── miner.py        # 채굴 (Proof of Work)
├── node.py         # P2P 네트워크 동기화
├── api.py          # REST API 서버
└── cli.py          # 커맨드라인 인터페이스
```

## 설치

```bash
cd my-crypto
pip install -r requirements.txt
```

## 빠른 시작

### 1. 데모 실행 (전체 흐름 한 번에)
```bash
python cli.py demo
```

### 2. 지갑 만들기
```bash
python cli.py wallet new --save my_wallet.pem
```

### 3. 채굴하기 (코인 획득)
```bash
python cli.py mine --wallet my_wallet.pem
```

### 4. 잔액 확인
```bash
python cli.py balance <주소>
```

### 5. 코인 보내기
```bash
python cli.py send --wallet my_wallet.pem --to <받는주소> --amount 10
```

### 6. 블록체인 상태 확인
```bash
python cli.py chain --verbose
```

---

## REST API 서버

```bash
python api.py --port 5000
```

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/` | 노드 정보 |
| GET | `/chain` | 전체 체인 조회 |
| GET | `/blocks/<index>` | 특정 블록 조회 |
| POST | `/transactions/new` | 트랜잭션 전송 |
| GET | `/transactions/pending` | 대기 트랜잭션 |
| POST | `/mine` | 채굴 실행 |
| GET | `/wallet/new` | 새 지갑 생성 |
| GET | `/balance/<address>` | 잔액 조회 |
| GET | `/history/<address>` | 트랜잭션 내역 |
| POST | `/peers/register` | 피어 등록 |
| POST | `/peers/sync` | 체인 동기화 |

---

## 기술 스펙

| 항목 | 내용 |
|------|------|
| 합의 알고리즘 | Proof of Work (PoW) |
| 서명 알고리즘 | ECDSA (SECP256K1) |
| 해시 함수 | SHA-256 |
| 주소 생성 | SHA-256 + RIPEMD-160 |
| 채굴 난이도 | 3 (앞 0 세 개) |
| 채굴 보상 | 50 KRC |
| 네트워크 | HTTP P2P (Nakamoto Consensus) |
