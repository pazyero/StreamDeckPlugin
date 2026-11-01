# DialAudioMixer+

このフォルダは Stream Deck 側のカスタムプラグインです。

フォルダ構成 (主要ファイル):

- `manifest.json` — プラグインのメタ情報
- `main.js` — Stream Deck 側のコード（WebSocket イベント受信）
- `plugin.html` — WebView の初期化
- `images/` — アイコン画像
- `propertyinspector/` — 設定 UI (inspector.html, inspector.js, inspector.css)

Python サーバーは別フォルダ `../server` に分離しています。

セットアップ:

リポジトリのルートにある `setup.bat` を実行してください。
ポータブルPython、Python依存ライブラリ、サーバー、選択したStream Deckプラグインを
まとめてセットアップします。PythonやVisual Studio C++ Build Toolsを個別に
インストールする必要はありません。

注意:

- images/\*.png はプレースホルダになっています。実際の PNG を用意してください。
