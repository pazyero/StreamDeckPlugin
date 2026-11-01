import sys
import win32ui
import win32gui
import win32con
import win32api
from PIL import Image
from common_logging import log_output

def extract_icon(exe_path, output_png):
# 指定した実行ファイルからアイコンを抽出してPNGとして保存する関数。
# exe_path: アイコンを抽出する実行ファイルのパス
# output_png: PNG画像の保存先パス
    large = []
    small = []
    hicon = None
    hdc = None
    hdc_obj = None
    hbmp = None
    hbm_color = None
    def cleanup_resources():
        for handle in set(large + small):
            try:
                win32gui.DestroyIcon(handle)
            except Exception:
                pass
        if hbm_color is not None:
            try:
                win32gui.DeleteObject(hbm_color)
            except Exception:
                pass
        if hdc_obj is not None:
            try:
                hdc_obj.DeleteDC()
            except Exception:
                pass
        if hbmp is not None:
            try:
                hbmp.DeleteObject()
            except Exception:
                pass
        if hdc is not None:
            try:
                hdc.DeleteDC()
            except Exception:
                pass
    # 大/小アイコンを取得
    large, small = win32gui.ExtractIconEx(exe_path, 0)
    if not large and not small:
        return False  # アイコンが存在しない場合

    # 優先して大アイコンを使用
    hicon = large[0] if large else small[0]

    # アイコン情報を取得
    icon_info = win32gui.GetIconInfo(hicon)
    hbmColor = icon_info[4]
    hbm_color = hbmColor

    # ビットマップ情報の取得
    bmpinfo = win32gui.GetObject(hbmColor)
    width, height = bmpinfo.bmWidth, bmpinfo.bmHeight

    # デバイスコンテキスト作成
    hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
    hbmp = win32ui.CreateBitmap()
    hbmp.CreateCompatibleBitmap(hdc, width, height)
    hdc_obj = hdc.CreateCompatibleDC()
    hdc_obj.SelectObject(hbmp)

    # アイコンを描画
    win32gui.DrawIconEx(
        hdc_obj.GetSafeHdc(), 0, 0, hicon, width, height, 0, None, win32con.DI_NORMAL
    )

    # ビットマップ情報とピクセルデータ取得
    bmpinfo = hbmp.GetInfo()
    bmpstr = hbmp.GetBitmapBits(True)

    img = None
    errors = []

    # PILイメージ作成の試行
    try:
        # 1. BGRA -> RGBA
        img = Image.frombuffer('RGBA', (width, height), bmpstr, 'raw', 'BGRA', 0, 1)
    except Exception as e:
        errors.append(f'frombuffer BGRA failed: {e}')

    if img is None:
        try:
            # 2. frombytesで試す
            img = Image.frombytes('RGBA', (width, height), bmpstr, 'raw', 'BGRA')
        except Exception as e:
            errors.append(f'frombytes BGRA failed: {e}')

    if img is None:
        try:
            # 3. BGRX (アルファなし) -> RGBAに変換
            img = Image.frombuffer('RGB', (width, height), bmpstr, 'raw', 'BGRX', 0, 1)
            img = img.convert('RGBA')
        except Exception as e:
            errors.append(f'frombuffer BGRX failed: {e}')

    if img is None:
        # 全て失敗
        log_output(
            f"画像作成失敗, 試行エラー: {errors}",
            "error",
            logger_name="icon_extractor",
        )
        try:
            win32gui.DestroyIcon(hicon)
        except Exception:
            pass
        cleanup_resources()
        return False

    # RGBA形式に変換して保存
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    img.save(output_png, "PNG")

    # アイコンハンドルの解放
    try:
        win32gui.DestroyIcon(hicon)
    except Exception:
        pass
    cleanup_resources()

    return True
