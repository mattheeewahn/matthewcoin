"""
wallet.py - 지갑: 키 생성, 서명, 검증
"""
import hashlib
import json
import os
import base64
from typing import Optional

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature


class Wallet:
    def __init__(self, private_key=None):
        if private_key:
            self._private_key = private_key
        else:
            # 새 키 쌍 생성 (SECP256K1 - 비트코인과 동일한 곡선)
            self._private_key = ec.generate_private_key(
                ec.SECP256K1(), default_backend()
            )
        self._public_key = self._private_key.public_key()
        self.address = self._derive_address()

    def _derive_address(self) -> str:
        """공개키에서 지갑 주소 유도 (SHA256 + RIPEMD160 방식)"""
        pub_bytes = self._public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.CompressedPoint,
        )
        sha256_hash = hashlib.sha256(pub_bytes).digest()
        ripemd160 = hashlib.new("ripemd160")
        ripemd160.update(sha256_hash)
        return "KRC" + ripemd160.hexdigest().upper()

    @property
    def public_key_hex(self) -> str:
        """공개키를 hex 문자열로 반환"""
        pub_bytes = self._public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.CompressedPoint,
        )
        return pub_bytes.hex()

    @property
    def private_key_hex(self) -> str:
        """개인키를 hex 문자열로 반환"""
        priv_bytes = self._private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return priv_bytes.hex()

    def sign_transaction(self, transaction: dict) -> str:
        """트랜잭션에 서명"""
        tx_data = json.dumps(
            {
                "sender": transaction["sender"],
                "recipient": transaction["recipient"],
                "amount": transaction["amount"],
            },
            sort_keys=True,
        ).encode()

        signature = self._private_key.sign(tx_data, ec.ECDSA(hashes.SHA256()))
        return base64.b64encode(signature).decode()

    def create_transaction(self, recipient: str, amount: float) -> dict:
        """서명된 트랜잭션 생성"""
        tx = {
            "sender": self.address,
            "recipient": recipient,
            "amount": amount,
            "public_key": self.public_key_hex,
        }
        tx["signature"] = self.sign_transaction(tx)
        tx["tx_id"] = self._compute_tx_id(tx)
        return tx

    @staticmethod
    def _compute_tx_id(tx: dict) -> str:
        data = json.dumps(
            {
                "sender": tx["sender"],
                "recipient": tx["recipient"],
                "amount": tx["amount"],
                "signature": tx.get("signature", ""),
            },
            sort_keys=True,
        )
        return hashlib.sha256(data.encode()).hexdigest()

    @staticmethod
    def verify_transaction(transaction: dict) -> bool:
        """트랜잭션 서명 검증"""
        try:
            pub_bytes = bytes.fromhex(transaction["public_key"])
            public_key = ec.EllipticCurvePublicKey.from_encoded_point(
                ec.SECP256K1(), pub_bytes
            )
            tx_data = json.dumps(
                {
                    "sender": transaction["sender"],
                    "recipient": transaction["recipient"],
                    "amount": transaction["amount"],
                },
                sort_keys=True,
            ).encode()
            signature = base64.b64decode(transaction["signature"])
            public_key.verify(signature, tx_data, ec.ECDSA(hashes.SHA256()))
            return True
        except (InvalidSignature, Exception):
            return False

    def save(self, filepath: str, password: Optional[str] = None):
        """지갑을 파일로 저장"""
        if password:
            encryption = serialization.BestAvailableEncryption(password.encode())
        else:
            encryption = serialization.NoEncryption()

        priv_bytes = self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption,
        )
        with open(filepath, "wb") as f:
            f.write(priv_bytes)
        print(f"[✓] 지갑 저장됨: {filepath}")

    @classmethod
    def load(cls, filepath: str, password: Optional[str] = None) -> "Wallet":
        """파일에서 지갑 로드"""
        with open(filepath, "rb") as f:
            pem_data = f.read()
        pwd = password.encode() if password else None
        private_key = serialization.load_pem_private_key(
            pem_data, password=pwd, backend=default_backend()
        )
        return cls(private_key=private_key)

    def __repr__(self):
        return f"<Wallet address={self.address}>"
