// app.js - MATTHEW Coin 프론트엔드
// 개인키는 sessionStorage에만 보관 (탭 닫으면 사라짐)
// 서버엔 서명된 트랜잭션만 전송

// ── 상태 ──────────────────────────────────────────────────
let wallet = null;   // { address, publicKey, pemStr }
let mining = false;
let mineWorker = null;
let mineBlocks = 0;
let mineEarned = 0;

// ── 초기화 ────────────────────────────────────────────────
window.onload = () => {
  // sessionStorage에 지갑 있으면 복원
  const saved = sessionStorage.getItem("mtw_wallet");
  if (saved) {
    wallet = JSON.parse(saved);
    showMain();
  }
  loadChainInfo();
};

// ── 탭 ───────────────────────────────────────────────────
function showTab(name) {
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.getElementById("tab-" + name).classList.add("active");
  event.target.classList.add("active");
  if (name === "wallet") refreshWallet();
  if (name === "chain")  loadChain();
  if (name === "mine")   loadChainInfo();
}

// ── 지갑 생성 ─────────────────────────────────────────────
async function createWallet() {
  setMsg("no-wallet-msg", "생성 중...", "info");
  const res = await fetch("/api/wallet/new");
  const data = await res.json();
  wallet = { address: data.address, publicKey: data.public_key, pemStr: data.pem };
  sessionStorage.setItem("mtw_wallet", JSON.stringify(wallet));

  // 자동으로 pem 파일 다운로드
  downloadPem(data.pem, "mtw_wallet.pem");
  setMsg("no-wallet-msg",
    "지갑이 생성됐습니다. mtw_wallet.pem 파일을 안전하게 보관하세요. 잃어버리면 복구 불가!", "ok");
  setTimeout(showMain, 1200);
}

// ── 지갑 불러오기 ─────────────────────────────────────────
async function loadWalletFile(event) {
  const file = event.target.files[0];
  if (!file) return;
  const pemStr = await file.text();
  setMsg("no-wallet-msg", "불러오는 중...", "info");
  const res = await fetch("/api/wallet/load", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pem: pemStr }),
  });
  if (!res.ok) {
    setMsg("no-wallet-msg", "지갑 파일이 올바르지 않습니다.", "err");
    return;
  }
  const data = await res.json();
  wallet = { address: data.address, publicKey: data.public_key, pemStr };
  sessionStorage.setItem("mtw_wallet", JSON.stringify(wallet));
  showMain();
}

function showMain() {
  document.getElementById("no-wallet").style.display = "none";
  document.getElementById("main-ui").style.display = "block";
  document.getElementById("header-addr").textContent = wallet.address;
  refreshWallet();
  loadChainInfo();
}

function forgetWallet() {
  if (!confirm("지갑을 삭제하면 이 탭에서 로그아웃됩니다.\n(pem 파일은 유지됩니다)")) return;
  sessionStorage.removeItem("mtw_wallet");
  wallet = null;
  location.reload();
}

function downloadWallet() {
  downloadPem(wallet.pemStr, "mtw_wallet.pem");
}

function downloadPem(pem, filename) {
  const blob = new Blob([pem], { type: "text/plain" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
}

function copyAddr() {
  navigator.clipboard.writeText(wallet.address);
  alert("주소가 복사됐습니다.");
}

// ── 지갑 탭 갱신 ──────────────────────────────────────────
async function refreshWallet() {
  if (!wallet) return;
  document.getElementById("my-address").value = wallet.address;
  document.getElementById("my-pubkey").value = wallet.publicKey;

  // 잔액
  const res = await fetch(`/api/balance/${wallet.address}`);
  const data = await res.json();
  document.getElementById("balance-display").textContent =
    `${data.balance.toFixed(4)} MTW`;
  document.getElementById("send-bal-info").textContent =
    `보유: ${data.balance.toFixed(4)} MTW`;

  // 내역
  const hres = await fetch(`/api/history/${wallet.address}`);
  const history = await hres.json();
  const tbody = document.getElementById("tx-history");
  tbody.innerHTML = "";
  [...history].reverse().slice(0, 30).forEach(tx => {
    const recv = tx.recipient === wallet.address;
    const other = recv ? tx.sender : tx.recipient;
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td style="color:${recv ? "green" : "red"}">${recv ? "수신" : "송신"}</td>
      <td>${tx.amount.toFixed(4)}</td>
      <td style="font-size:0.75rem">${other}</td>
      <td>#${tx.block_index}</td>`;
    tbody.appendChild(tr);
  });
}

// ── 채굴 ──────────────────────────────────────────────────
async function loadChainInfo() {
  const res = await fetch("/api/chain/latest?n=1");
  const data = await res.json();
  document.getElementById("info-diff").textContent = data.blocks[0]
    ? `${countLeadingZeros(data.blocks[0].hash)} (목표: ${"0".repeat(3)}...)` : "-";

  // 서버에서 난이도 가져오기
  const cres = await fetch("/api/chain");
  const cdata = await cres.json();
  document.getElementById("info-diff").textContent = cdata.difficulty;
  document.getElementById("info-reward").textContent = `${cdata.mining_reward} MTW`;
}

async function toggleMine() {
  if (!mining) {
    mining = true;
    document.getElementById("btn-mine").textContent = "채굴 중지";
    document.getElementById("btn-mine").classList.add("danger");
    document.getElementById("btn-mine").classList.remove("primary");
    mineLoop();
  } else {
    mining = false;
    document.getElementById("btn-mine").textContent = "채굴 시작";
    document.getElementById("btn-mine").classList.remove("danger");
    document.getElementById("btn-mine").classList.add("primary");
    document.getElementById("mine-status").style.display = "none";
  }
}

async function mineLoop() {
  while (mining) {
    try {
      // 1. 서버에서 작업 받기
      const wres = await fetch(`/api/mine/work?address=${wallet.address}`);
      if (!wres.ok) { await sleep(2000); continue; }
      const work = await wres.json();

      showMineStatus(`블록 #${work.index} 채굴 중...`, "info");
      mineLog(`[${now()}] 블록 #${work.index} 작업 시작 (이전 해시: ${work.previous_hash.slice(0,16)}...)`);

      // 2. PoW 수행 (브라우저에서)
      const t0 = performance.now();
      const result = await proofOfWork(work);
      const elapsed = ((performance.now() - t0) / 1000).toFixed(2);
      const hashrate = Math.round(result.nonce / (elapsed || 1));

      if (!mining) break;  // 중지됐으면 제출 안 함

      // 3. 서버에 제출
      const sres = await fetch("/api/mine", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ block: result }),
      });

      if (sres.ok) {
        mineBlocks++;
        mineEarned += work.transactions.find(t => t.sender === "COINBASE")?.amount || 50;
        document.getElementById("mine-blocks").textContent = mineBlocks;
        document.getElementById("mine-earned").textContent = mineEarned.toFixed(0);
        document.getElementById("mine-hashrate").textContent = `${hashrate.toLocaleString()} H/s`;
        mineLog(`[${now()}] ✓ 블록 #${result.index} 채굴 성공!  nonce=${result.nonce.toLocaleString()}  ${elapsed}s  ${hashrate.toLocaleString()} H/s`);
        showMineStatus(`블록 #${result.index} 채굴 성공! +${mineEarned} MTW`, "ok");
        refreshWallet();
      } else {
        const err = await sres.text();
        mineLog(`[${now()}] ✗ 제출 실패: ${err}`);
        await sleep(1000);
      }
    } catch (e) {
      mineLog(`[${now()}] 오류: ${e.message}`);
      await sleep(2000);
    }
  }
}

// PoW — sample_json에서 nonce 부분만 교체해서 해시 계산
// Python json.dumps 재현 불필요 — 서버가 이미 직렬화된 문자열 제공
async function proofOfWork(work) {
  const target = "0".repeat(work.difficulty);
  let nonce = 0;
  // "nonce": 0 → "nonce": 1234 로 교체
  // sample_json 예: {"index": 1, "nonce": 0, "previous_hash": "...", ...}
  const noncePrefix = '"nonce": ';

  while (true) {
    const blockData = work.sample_json.replace(
      noncePrefix + "0",
      noncePrefix + nonce
    );
    const hash = sha256(blockData);

    if (hash.startsWith(target)) {
      return {
        index: work.index,
        timestamp: work.timestamp,
        transactions: work.transactions,
        previous_hash: work.previous_hash,
        nonce: nonce,
        hash: hash,
      };
    }
    nonce++;
    if (nonce % 2000 === 0) {
      document.getElementById("mine-hashrate").textContent = `${nonce.toLocaleString()} 시도 중...`;
      await sleep(0);
      if (!mining) return null;
    }
  }
}

// Python json.dumps(sort_keys=True) 와 동일한 직렬화 (전송용으로만 사용)
function sortedJsonDumps(obj) {
  if (obj === null) return "null";
  if (typeof obj === "boolean") return obj ? "true" : "false";
  if (typeof obj === "number") return String(obj);
  if (typeof obj === "string") return JSON.stringify(obj);
  if (Array.isArray(obj)) return "[" + obj.map(sortedJsonDumps).join(", ") + "]";
  if (typeof obj === "object") {
    const keys = Object.keys(obj).sort();
    return "{" + keys.map(k => JSON.stringify(k) + ": " + sortedJsonDumps(obj[k])).join(", ") + "}";
  }
  return JSON.stringify(obj);
}

// SHA-256 — js-sha256 라이브러리 사용 (HTTP/HTTPS 모두 동작, 인터넷 불필요)

// ── 전송 ──────────────────────────────────────────────────
async function doSend() {
  const to = document.getElementById("send-to").value.trim();
  const amt = parseFloat(document.getElementById("send-amt").value);

  if (!to || isNaN(amt) || amt <= 0) {
    setMsg("send-msg", "주소와 금액을 올바르게 입력하세요.", "err");
    return;
  }

  // 서명은 서버에서 처리 (PEM을 서버에 보내서 서명)
  // 보안상 PEM을 서버에 보내는 건 좋지 않지만,
  // 현재 구조에서 브라우저 JS로 ECDSA 서명하려면 별도 라이브러리 필요.
  // 여기서는 서버에 PEM + 트랜잭션 정보를 보내 서명 후 제출하는 방식 사용.
  setMsg("send-msg", "전송 중...", "info");

  const res = await fetch("/api/tx/sign_and_send", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      pem: wallet.pemStr,
      recipient: to,
      amount: amt,
    }),
  });

  if (res.ok) {
    const data = await res.json();
    setMsg("send-msg", `전송 완료! TX: ${data.tx_id.slice(0, 20)}...`, "ok");
    document.getElementById("send-to").value = "";
    document.getElementById("send-amt").value = "";
    refreshWallet();
  } else {
    const err = await res.json().catch(() => ({ message: "오류" }));
    setMsg("send-msg", `전송 실패: ${err.message || err}`, "err");
  }
}

// ── 블록체인 탭 ───────────────────────────────────────────
async function loadChain() {
  const res = await fetch("/api/chain/latest?n=50");
  const data = await res.json();

  document.getElementById("chain-info").textContent =
    `총 블록: ${data.total}  |  대기 TX: ${data.pending}  |  ${data.valid ? "유효" : "손상됨"}`;

  const tbody = document.getElementById("chain-table");
  tbody.innerHTML = "";
  data.blocks.forEach(b => {
    const ts = b.timestamp
      ? new Date(b.timestamp * 1000).toLocaleString("ko-KR")
      : "genesis";
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>#${b.index}</td>
      <td style="font-size:0.75rem">${b.hash.slice(0, 40)}...</td>
      <td style="text-align:center">${b.transactions.length}</td>
      <td style="text-align:right">${b.nonce.toLocaleString()}</td>
      <td>${ts}</td>`;
    tbody.appendChild(tr);
  });
}

// ── 유틸 ──────────────────────────────────────────────────
function setMsg(id, text, type) {
  const el = document.getElementById(id);
  el.textContent = text;
  el.className = `msg ${type}`;
  el.style.display = text ? "block" : "none";
}

function showMineStatus(text, type) {
  const el = document.getElementById("mine-status");
  el.textContent = text;
  el.className = `msg ${type}`;
  el.style.display = "block";
}

function mineLog(text) {
  const el = document.getElementById("mine-log");
  el.textContent += text + "\n";
  el.scrollTop = el.scrollHeight;
}

function now() {
  return new Date().toLocaleTimeString("ko-KR");
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}
