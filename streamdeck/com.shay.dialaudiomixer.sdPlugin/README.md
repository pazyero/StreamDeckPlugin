# DialAudioMixer+

このフォルダは Stream Deck 側のカスタムプラグインです。

フォルダ構成 (主要ファイル):

- `manifest.json` — プラグインのメタ情報
- `main.js` — Stream Deck 側のコード（WebSocket イベント受信）
- `plugin.html` — WebView の初期化
- `images/` — アイコン画像
- `propertyinspector/` — 設定 UI (inspector.html, inspector.js, inspector.css)

Python サーバーは別フォルダ `../server` に分離しています。

セットアップ (簡易):

1. Python 依存のインストール:

   cd ../server
   pip install -r requirements.txt

2. サーバーを起動:

   python helper.py

3. このプラグインフォルダを Stream Deck に配置するか、開発環境で WebSocket と接続します。

注意:

- images/\*.png はプレースホルダになっています。実際の PNG を用意してください。
- `helper.py` の `/volume` 実装は現在ダミーです。WASAPI 等での実装が必要です。
