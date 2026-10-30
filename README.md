# DialAudioMixer and Mic Controller for Stream Deck

## 概要

このリポジトリには、WindowsとStream Deck向けの2つのプラグインがあります。

- **Dial Audio Mixer**
  - アクティブなオーディオアプリを検出
  - ダイヤルまたはキー操作で個別アプリの音量を変更
  - アプリの除外設定を管理
  - アプリ名、音量、アイコンをStream Deckへ表示
- **Mic Controller**
  - HyperX SoloCastのミュート状態を監視
  - マイク本体操作とStream Deck操作を相互同期

## プロジェクト構成

```text
StreamDeckPlugin/
├─ server/
│  ├─ server.py
│  ├─ icon_extractor.py
│  ├─ requirements.txt
│  ├─ com.shay.dialaudiomixer.sdPlugin/
│  │  ├─ dialAudioMixer.py
│  │  └─ exclude.json
│  └─ com.shay.miccontroller.sdPlugin/
│     ├─ micController.py
│     ├─ soloCastHidReader.py
│     ├─ test_soloCastHidReader.py
│     └─ README.md
├─ streamdeck/
│  ├─ com.shay.dialaudiomixer.sdPlugin/
│  │  ├─ manifest.json
│  │  ├─ main.js
│  │  ├─ plugin.html
│  │  ├─ exclude.json
│  │  ├─ images/
│  │  ├─ propertyinspector/
│  │  └─ README.md
│  └─ com.shay.miccontroller.sdPlugin/
│     ├─ manifest.json
│     ├─ main.js
│     ├─ plugin.html
│     ├─ images/
│     └─ README.md
├─ update-streamdeck.bat
├─ update-streamdeck.ps1
├─ README.md
└─ LICENSE
```

- `server/server.py`
  - ローカルHTTPサーバー
  - Flask Blueprintで各プラグインモジュールを登録
  - 待受ポートは`8823`
- `server/com.shay.dialaudiomixer.sdPlugin/dialAudioMixer.py`
  - Dial Audio Mixerの音量制御API
- `server/com.shay.miccontroller.sdPlugin/micController.py`
  - Mic ControllerのHTTP APIとSSEイベント
- `server/com.shay.miccontroller.sdPlugin/soloCastHidReader.py`
  - SoloCastのHID列挙、監視、WindowsキャプチャEndpoint制御
- `streamdeck/`
  - Stream Deckプラグイン本体

## 動作環境

- Windows 10 / 11
- Stream Deck Software 6.0以上
- Python 3.13で動作確認済み

Python依存パッケージ:

- Flask
- psutil
- pywin32
- pycaw
- comtypes
- Pillow
- hidapi

## セットアップ

リポジトリのルートで依存パッケージをインストールします。

```powershell
python -m pip install -r server/requirements.txt
```

サーバーを起動します。

```powershell
python server/server.py
```

サーバーは`http://127.0.0.1:8823`で待ち受けます。

## Stream Deckプラグインの更新

`update-streamdeck.bat`を実行すると、以下を行います。

1. Stream Deckを停止
2. `streamdeck/*.sdPlugin`をStream Deckのプラグインフォルダへコピー
3. Stream Deckを再起動

```powershell
.\update-streamdeck.bat
```

更新処理には管理者権限が必要です。UAC確認後、自動的に管理者プロセスへ切り替わります。

## Dial Audio Mixer

Stream Deck上でDial Audio Mixerのアクションを追加します。

- ダイヤル操作: 音量の調整
- キー操作: ミュート切り替え
- プロパティインスペクター: 除外アプリなどの設定

サーバー側の音量制御は、`server/com.shay.dialaudiomixer.sdPlugin/dialAudioMixer.py`に実装されています。

## Mic Controller

対象デバイスはHyperX SoloCastです。
