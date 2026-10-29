# DialAudioMixer for Stream Deck

## 概要

**DialAudioMixer** は、Elgato Stream Deck 用のプラグインで、Windows 上のアクティブなオーディオアプリを管理し、ダイヤル操作で個別アプリの音量を調整できるプラグインです。

- Stream Deck のダイヤル（エンコーダー）で音量操作
- アクティブなアプリを自動検出
- アイコンと音量を Stream Deck 上に表示
- アプリの除外リスト機能
- 音量の増減・絶対設定対応

---

## プロジェクト構成

将来の機能追加を前提に、Python サーバーと Stream Deck 側を分離して保管します。

```text
DialAudioMixer/
├─ server/
│  ├─ helper.py
│  ├─ icon_extractor.py
│  ├─ requirements.txt
│  └─ exclude.json
├─ streamdeck/
│  └─ com.shay.dialaudiomixer.sdPlugin/
│     ├─ manifest.json
│     ├─ main.js
│     ├─ plugin.html
│     ├─ images/
│     ├─ propertyinspector/
│     └─ README.md
├─ README.md
├─ LICENSE
└─ ...
```

- `server/` には共通の Python API とオーディオ制御を置く
- `streamdeck/` には Stream Deck UI / WebSocket / 表示処理を置く
- 今後の機能追加は、Python 側は `server` に、Stream Deck 側は `streamdeck` に追加していく構成

---

## 動作環境

- Windows 10 / 11
- Stream Deck 5.0 以上
- Python 3.8 以上

### Python 依存パッケージ

- psutil
- pycaw
- comtypes
- Pillow
- Flask
- pywin32

---

## インストール方法

1. このリポジトリをダウンロードまたはクローン
2. `streamdeck/com.shay.dialaudiomixer.sdPlugin` を Stream Deck のプラグイン格納先に配置
3. `server` 側で依存ライブラリをインストール
4. `server/helper.py` を起動してローカル API を待機
5. Stream Deck にプラグインを読み込ませて利用

---

## 使い方

1. Stream Deck 上で「Dial Audio Mixer」アクションを追加
2. アクションのダイヤルを回すとアクティブなアプリの音量が変更されます
3. アプリ名と音量がダイヤル上に表示されます
4. 除外したいアプリはプラグイン設定から追加可能

---

## 開発用

- Stream Deck 側: `streamdeck/com.shay.dialaudiomixer.sdPlugin/`
- Python サーバー: `server/helper.py`
- アイコン抽出: `server/icon_extractor.py`

### 起動

Python サーバーを手動で起動する場合:

```bash
cd server
pip install -r requirements.txt
python helper.py
```
