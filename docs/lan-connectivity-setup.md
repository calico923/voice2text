# LAN接続設定手順（T06）

## 1. 目的
- Mac から Windows(WSL2) 上の `/v1/realtime` へ接続できるようにする。
- `portproxy` と `mirrored` の2方式を整理し、採用方式を固定する。

## 2. 前提
- vLLM サーバは WSL 内で `0.0.0.0:8000` 待受
- Windows Firewall は管理者権限で設定
- ルータのポート開放はしない（LAN限定）

## 3. 方式A: `portproxy`

### 3.1 概要
- Windowsホストの `TCP:<port>` を WSL IP の同ポートへ転送する。
- WSL再起動でIPが変わるため、必要に応じて再設定が必要。

### 3.2 手順（管理者PowerShell）
```powershell
.\windows-network\setup-portproxy.ps1 `
  -ListenAddress 0.0.0.0 `
  -ListenPort 8000 `
  -ConnectAddress <WSL_IP> `
  -ConnectPort 8000
```

### 3.3 削除
```powershell
.\windows-network\remove-portproxy.ps1 -ListenAddress 0.0.0.0 -ListenPort 8000
```

## 4. 方式B: `mirrored`（Windows 11 22H2+）

### 4.1 概要
- WSL2 ネットワークを mirrored モードにし、到達性を改善する方式。
- NAT前提の手動転送より維持負荷が低い。

### 4.2 設定手順
1. Windows 側 `%UserProfile%\.wslconfig` を編集:
```ini
[wsl2]
networkingMode=mirrored
```
2. 反映:
```powershell
wsl --shutdown
```
3. WSL再起動後に到達確認を実施。

## 5. Firewall 設定（Mac IP限定）
```powershell
.\windows-network\setup-firewall-rule.ps1 `
  -RuleName "voice2text-realtime-8000" `
  -Port 8000 `
  -MacIp <MAC_IP>
```

## 6. 採用方針（暫定）
- 暫定採用: `mirrored`
- 理由:
  - WSL IP変動への追従作業が少ない
  - 運用時の再設定コストが低い
- 最終確定:
  - `T08` の3経路試験結果で最終決定する

## 7. 完了条件（T06 DoD向け）
- [ ] 採用方式で Mac -> Windows host IP の接続成功ログがある
- [ ] Firewall を Mac IP に限定できている
- [ ] 第三者が再現できる手順として文書化済み
