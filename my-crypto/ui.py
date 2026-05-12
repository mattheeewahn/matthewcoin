"""
ui.py - MATTHEW Coin (MTW) 지갑
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import json
import os
import time
import queue

from blockchain import Blockchain
from wallet import Wallet

CHAIN_FILE  = "mtw_chain.json"
WALLET_FILE = "mtw_wallet.pem"


def load_blockchain():
    if os.path.exists(CHAIN_FILE):
        with open(CHAIN_FILE) as f:
            return Blockchain.from_dict(json.load(f))
    return Blockchain()


def save_blockchain(bc):
    with open(CHAIN_FILE, "w") as f:
        json.dump(bc.to_dict(), f, indent=2)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MATTHEW Coin (MTW)")
        self.geometry("700x520")
        self.resizable(False, False)

        self.bc = load_blockchain()
        self.mining = False
        self.log_queue = queue.Queue()

        # 지갑 로드 or 생성
        if os.path.exists(WALLET_FILE):
            self.wallet = Wallet.load(WALLET_FILE)
        else:
            self.wallet = Wallet()
            self.wallet.save(WALLET_FILE)

        self._build()
        self._refresh()
        self._poll_log()

    # ── UI ────────────────────────────────────────────────
    def _build(self):
        # 탭
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=6, pady=6)

        self.t_wallet = tk.Frame(nb)
        self.t_mine   = tk.Frame(nb)
        self.t_send   = tk.Frame(nb)
        self.t_chain  = tk.Frame(nb)

        nb.add(self.t_wallet, text="지갑")
        nb.add(self.t_mine,   text="채굴")
        nb.add(self.t_send,   text="전송")
        nb.add(self.t_chain,  text="블록체인")

        self._tab_wallet()
        self._tab_mine()
        self._tab_send()
        self._tab_chain()

    # ── 지갑 탭 ───────────────────────────────────────────
    def _tab_wallet(self):
        f = self.t_wallet
        p = dict(padx=16, pady=4)

        tk.Label(f, text="MATTHEW Coin (MTW) 지갑", font=("", 13, "bold")).pack(anchor="w", **p)
        ttk.Separator(f).pack(fill="x", padx=16, pady=2)

        tk.Label(f, text="잔액").pack(anchor="w", padx=16, pady=(8,0))
        self.lbl_balance = tk.Label(f, text="0 MTW", font=("", 22, "bold"), fg="#1a6e1a")
        self.lbl_balance.pack(anchor="w", **p)

        tk.Label(f, text="내 주소").pack(anchor="w", padx=16, pady=(8,0))
        addr_row = tk.Frame(f)
        addr_row.pack(fill="x", padx=16)
        self.lbl_addr = tk.Entry(addr_row, font=("Courier", 9), state="readonly", width=52)
        self.lbl_addr.pack(side="left")
        tk.Button(addr_row, text="복사", command=self._copy_addr).pack(side="left", padx=4)

        tk.Label(f, text="공개키").pack(anchor="w", padx=16, pady=(8,0))
        self.lbl_pubkey = tk.Text(f, height=2, font=("Courier", 8), state="disabled", wrap="char")
        self.lbl_pubkey.pack(fill="x", padx=16)

        btn_row = tk.Frame(f)
        btn_row.pack(anchor="w", padx=16, pady=10)
        tk.Button(btn_row, text="새 지갑 만들기", command=self._new_wallet).pack(side="left", padx=(0,6))
        tk.Button(btn_row, text="내역 보기", command=self._show_history).pack(side="left")

        tk.Label(f, text="최근 트랜잭션").pack(anchor="w", padx=16, pady=(4,0))
        cols = ("방향", "금액", "상대 주소", "블록")
        self.tree = ttk.Treeview(f, columns=cols, show="headings", height=7)
        self.tree.heading("방향", text="방향")
        self.tree.heading("금액", text="금액 (MTW)")
        self.tree.heading("상대 주소", text="상대 주소")
        self.tree.heading("블록", text="블록")
        self.tree.column("방향", width=55, anchor="center")
        self.tree.column("금액", width=110, anchor="e")
        self.tree.column("상대 주소", width=360)
        self.tree.column("블록", width=55, anchor="center")
        self.tree.pack(fill="x", padx=16, pady=4)

    # ── 채굴 탭 ───────────────────────────────────────────
    def _tab_mine(self):
        f = self.t_mine
        p = dict(padx=16, pady=4)

        tk.Label(f, text="채굴", font=("", 13, "bold")).pack(anchor="w", **p)
        ttk.Separator(f).pack(fill="x", padx=16, pady=2)

        info = tk.Frame(f)
        info.pack(fill="x", padx=16, pady=6)
        tk.Label(info, text=f"난이도: {self.bc.DIFFICULTY}   보상: {self.bc.MINING_REWARD} MTW / 블록",
                 font=("", 10)).pack(side="left")

        stat_row = tk.Frame(f)
        stat_row.pack(fill="x", padx=16, pady=4)
        tk.Label(stat_row, text="채굴 블록:").pack(side="left")
        self.lbl_mblocks = tk.Label(stat_row, text="0", font=("", 10, "bold"), fg="#1a6e1a")
        self.lbl_mblocks.pack(side="left", padx=(2,16))
        tk.Label(stat_row, text="획득 MTW:").pack(side="left")
        self.lbl_mearned = tk.Label(stat_row, text="0", font=("", 10, "bold"), fg="#1a6e1a")
        self.lbl_mearned.pack(side="left", padx=(2,16))
        tk.Label(stat_row, text="속도:").pack(side="left")
        self.lbl_mhash = tk.Label(stat_row, text="0 H/s", font=("", 10, "bold"))
        self.lbl_mhash.pack(side="left", padx=2)

        self.btn_mine = tk.Button(f, text="채굴 시작", font=("", 11, "bold"),
                                  width=14, command=self._toggle_mine)
        self.btn_mine.pack(pady=8)

        self.pb = ttk.Progressbar(f, mode="indeterminate", length=400)
        self.pb.pack(pady=2)

        tk.Label(f, text="로그").pack(anchor="w", padx=16, pady=(8,0))
        self.log_box = scrolledtext.ScrolledText(f, height=14, font=("Courier", 9),
                                                  state="disabled")
        self.log_box.pack(fill="both", expand=True, padx=16, pady=4)

    # ── 전송 탭 ───────────────────────────────────────────
    def _tab_send(self):
        f = self.t_send
        p = dict(padx=16, pady=4)

        tk.Label(f, text="MTW 전송", font=("", 13, "bold")).pack(anchor="w", **p)
        ttk.Separator(f).pack(fill="x", padx=16, pady=2)
        tk.Label(f, text="전송 후 채굴을 해야 블록에 기록됩니다.", fg="gray").pack(anchor="w", padx=16)

        tk.Label(f, text="받는 주소").pack(anchor="w", padx=16, pady=(12,0))
        self.entry_to = tk.Entry(f, font=("Courier", 10), width=56)
        self.entry_to.pack(padx=16, pady=2)

        tk.Label(f, text="금액 (MTW)").pack(anchor="w", padx=16, pady=(8,0))
        self.entry_amt = tk.Entry(f, font=("", 11), width=20)
        self.entry_amt.pack(anchor="w", padx=16, pady=2)

        self.lbl_bal2 = tk.Label(f, text="", fg="gray")
        self.lbl_bal2.pack(anchor="w", padx=16)

        tk.Button(f, text="전송", font=("", 11, "bold"), width=12,
                  command=self._do_send).pack(pady=14)

        self.lbl_send_msg = tk.Label(f, text="", font=("", 10))
        self.lbl_send_msg.pack()

    # ── 블록체인 탭 ───────────────────────────────────────
    def _tab_chain(self):
        f = self.t_chain
        p = dict(padx=16, pady=4)

        top = tk.Frame(f)
        top.pack(fill="x", padx=16, pady=6)
        self.lbl_chain_info = tk.Label(top, text="", font=("", 9))
        self.lbl_chain_info.pack(side="left")
        tk.Button(top, text="새로고침", command=self._refresh_chain).pack(side="right")

        cols = ("블록", "해시", "TX", "Nonce", "시간")
        self.tree_chain = ttk.Treeview(f, columns=cols, show="headings", height=18)
        self.tree_chain.heading("블록",  text="블록")
        self.tree_chain.heading("해시",  text="해시")
        self.tree_chain.heading("TX",    text="TX")
        self.tree_chain.heading("Nonce", text="Nonce")
        self.tree_chain.heading("시간",  text="시간")
        self.tree_chain.column("블록",  width=50,  anchor="center")
        self.tree_chain.column("해시",  width=320)
        self.tree_chain.column("TX",    width=40,  anchor="center")
        self.tree_chain.column("Nonce", width=90,  anchor="e")
        self.tree_chain.column("시간",  width=150, anchor="center")
        sb = ttk.Scrollbar(f, orient="vertical", command=self.tree_chain.yview)
        self.tree_chain.configure(yscrollcommand=sb.set)
        self.tree_chain.pack(side="left", fill="both", expand=True, padx=(16,0), pady=4)
        sb.pack(side="left", fill="y", pady=4)

    # ── 갱신 ──────────────────────────────────────────────
    def _refresh(self):
        self._refresh_wallet()
        self._refresh_chain()

    def _refresh_wallet(self):
        bal = self.bc.get_balance(self.wallet.address)
        self.lbl_balance.config(text=f"{bal:,.4f} MTW")
        self.lbl_bal2.config(text=f"보유: {bal:,.4f} MTW")

        # 주소 entry
        self.lbl_addr.config(state="normal")
        self.lbl_addr.delete(0, "end")
        self.lbl_addr.insert(0, self.wallet.address)
        self.lbl_addr.config(state="readonly")

        # 공개키
        self.lbl_pubkey.config(state="normal")
        self.lbl_pubkey.delete("1.0", "end")
        self.lbl_pubkey.insert("1.0", self.wallet.public_key_hex)
        self.lbl_pubkey.config(state="disabled")

        # 내역
        for r in self.tree.get_children():
            self.tree.delete(r)
        for tx in reversed(self.bc.get_transaction_history(self.wallet.address)[-20:]):
            recv = tx["recipient"] == self.wallet.address
            other = tx["sender"] if recv else tx["recipient"]
            self.tree.insert("", "end", values=(
                "수신" if recv else "송신",
                f"{tx['amount']:,.4f}",
                other[:50],
                f"#{tx['block_index']}",
            ))

    def _refresh_chain(self):
        valid = self.bc.is_chain_valid()
        self.lbl_chain_info.config(
            text=f"블록: {len(self.bc.chain)}  |  대기 TX: {len(self.bc.pending_transactions)}  |  "
                 f"{'유효' if valid else '손상됨'}",
            fg="black" if valid else "red")
        for r in self.tree_chain.get_children():
            self.tree_chain.delete(r)
        for block in reversed(self.bc.chain):
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(block.timestamp)) \
                 if block.timestamp else "genesis"
            self.tree_chain.insert("", "end", values=(
                f"#{block.index}",
                block.hash[:48] + "...",
                len(block.transactions),
                f"{block.nonce:,}",
                ts,
            ))

    # ── 채굴 ──────────────────────────────────────────────
    def _toggle_mine(self):
        if not self.mining:
            self.mining = True
            self.btn_mine.config(text="채굴 중지")
            self.pb.start(10)
            threading.Thread(target=self._mine_loop, daemon=True).start()
        else:
            self.mining = False
            self.btn_mine.config(text="채굴 시작")
            self.pb.stop()

    def _mine_loop(self):
        blocks = 0
        earned = 0.0
        while self.mining:
            t0 = time.time()
            block = self.bc.mine_pending_transactions(self.wallet.address)
            elapsed = time.time() - t0
            blocks += 1
            earned += self.bc.MINING_REWARD
            hashrate = block.nonce / elapsed if elapsed > 0 else 0

            msg = (f"[{time.strftime('%H:%M:%S')}] "
                   f"블록 #{block.index}  nonce={block.nonce:,}  "
                   f"{elapsed:.2f}s  {hashrate:,.0f} H/s\n")
            self.log_queue.put(("log", msg))
            self.log_queue.put(("stat", blocks, earned, hashrate))
            save_blockchain(self.bc)
            self.after(0, self._refresh)

    def _poll_log(self):
        try:
            while True:
                item = self.log_queue.get_nowait()
                if item[0] == "log":
                    self.log_box.config(state="normal")
                    self.log_box.insert("end", item[1])
                    self.log_box.see("end")
                    self.log_box.config(state="disabled")
                elif item[0] == "stat":
                    _, blocks, earned, hashrate = item
                    self.lbl_mblocks.config(text=str(blocks))
                    self.lbl_mearned.config(text=f"{earned:,.0f}")
                    self.lbl_mhash.config(text=f"{hashrate:,.0f} H/s")
        except queue.Empty:
            pass
        self.after(100, self._poll_log)

    # ── 전송 ──────────────────────────────────────────────
    def _do_send(self):
        to = self.entry_to.get().strip()
        amt_str = self.entry_amt.get().strip()
        if not to or not amt_str:
            self.lbl_send_msg.config(text="주소와 금액을 입력하세요.", fg="red")
            return
        try:
            amt = float(amt_str)
        except ValueError:
            self.lbl_send_msg.config(text="금액이 올바르지 않습니다.", fg="red")
            return
        if amt <= 0:
            self.lbl_send_msg.config(text="금액은 0보다 커야 합니다.", fg="red")
            return
        bal = self.bc.get_balance(self.wallet.address)
        if bal < amt:
            self.lbl_send_msg.config(text=f"잔액 부족 (보유: {bal:.4f} MTW)", fg="red")
            return
        tx = self.wallet.create_transaction(to, amt)
        if self.bc.add_transaction(tx):
            save_blockchain(self.bc)
            self.lbl_send_msg.config(text=f"전송 완료. TX: {tx['tx_id'][:20]}...", fg="green")
            self.entry_to.delete(0, "end")
            self.entry_amt.delete(0, "end")
            self._refresh_wallet()
        else:
            self.lbl_send_msg.config(text="전송 실패.", fg="red")

    # ── 기타 ──────────────────────────────────────────────
    def _copy_addr(self):
        self.clipboard_clear()
        self.clipboard_append(self.wallet.address)

    def _new_wallet(self):
        if not messagebox.askyesno("새 지갑", "기존 지갑이 교체됩니다. 계속하시겠습니까?"):
            return
        self.wallet = Wallet()
        self.wallet.save(WALLET_FILE)
        self._refresh_wallet()
        messagebox.showinfo("완료", f"새 지갑:\n{self.wallet.address}")

    def _show_history(self):
        history = self.bc.get_transaction_history(self.wallet.address)
        win = tk.Toplevel(self)
        win.title("트랜잭션 내역")
        win.geometry("640x360")
        txt = scrolledtext.ScrolledText(win, font=("Courier", 9))
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        for tx in history:
            recv = tx["recipient"] == self.wallet.address
            other = tx["sender"] if recv else tx["recipient"]
            txt.insert("end",
                f"[블록 #{tx['block_index']}] {'수신' if recv else '송신'}  "
                f"{tx['amount']:,.4f} MTW  |  {other}\n")
        txt.config(state="disabled")


if __name__ == "__main__":
    App().mainloop()
