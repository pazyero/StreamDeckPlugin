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

- Windows 10/11 x64
- Stream Deck Software 6.0以上
- Stream Deck本体と接続済みであること
- インターネット接続
- 管理者権限

セットアップ時にポータブルPythonと以下の依存パッケージを自動で導入します。PCにPythonやVisual Studio C++ Build Toolsを事前にインストールする必要はありません。

- Flask
- psutil
- pywin32
- pycaw
- comtypes
- Pillow
- hidapi

## セットアップ

Stream Deck Softwareをインストール済み、Stream Deck本体を接続済み、かつStream Deck Softwareで使用できる状態になっているPCで実行します。

1. このリポジトリをダウンロードして任意のフォルダーに展開します。
2. 展開したフォルダーにある `setup.bat` をダブルクリックします。
3. 表示された選択画面で、インストールする機能を順番に指定します。

   - `Install Mic Controller? (y/n)`：Mic Controllerをインストールするか選択
   - `Install Dial Audio Mixer? (y/n)`：Dial Audio Mixerをインストールするか選択

   `y`または`yes`でインストール、`n`または未入力ではインストールしません。

4. 管理者権限の確認画面が表示された場合は「はい」を選択します。
5. インストール完了メッセージを確認します。

`setup.bat`は1回実行するだけで、次の処理をまとめて行います。

- ポータブルPythonの配置
- Python依存パッケージのインストール
- 選択したStream Deckプラグインのコピーと登録
- Stream Deck Softwareの再起動
- ローカルサーバーの起動
- Windowsログイン時にサーバーを自動起動する設定

セットアップ後はサーバーを個別に起動する必要はありません。サーバーは `http://127.0.0.1:8823` で待ち受けます。

`Mic Controller`と`Dial Audio Mixer`の選択結果に応じて、導入内容とサーバーの読み込みモジュールが切り替わります。

| 選択 | Stream Deckプラグイン | サーバーで起動するモジュール |
|---|---|---|
| Mic=N、Dial=Y | `com.shay.dialaudiomixer.sdPlugin`のみ | Dial Audio Mixerのみ |
| Mic=Y、Dial=N | `com.shay.miccontroller.sdPlugin`のみ | Mic Controllerのみ |
| Mic=Y、Dial=Y | 2つのプラグインを両方 | Dial Audio MixerとMic Controller |
| Mic=N、Dial=N | プラグインなし | 共通APIのみ |

インストール済みのプラグインを再実行時に選択解除すると、そのプラグインはStream Deckから削除されます。選択を`N`にした場合、対応するサーバーモジュールもロードされず、そのHID監視スレッドやWindowsオーディオ制御APIも起動しません。

手動確認が必要な場合は、リポジトリのルートにある `start-server.bat` を実行できます。サーバーが正常に起動しているか確認する場合は、ブラウザーまたはPowerShellで次のURLへアクセスします。

```text
http://127.0.0.1:8823/health
```

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
