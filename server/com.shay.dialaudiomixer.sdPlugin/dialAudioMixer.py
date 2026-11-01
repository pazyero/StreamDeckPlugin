# Stream Deckダイヤル用のWindowsオーディオ制御API。
# pycawで実行中プロセスの音量・ミュートを操作し、アイコン取得や除外リストの
# 管理も提供する。

import psutil
import json
from flask import Blueprint, request, jsonify
from icon_extractor import extract_icon
import os
import base64
import tempfile
import sys
from contextlib import contextmanager
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parent.parent
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from common_logging import log_output

# pycawが利用できない環境でもサーバー自体は起動できるよう、利用可否を判定する。
try:
    from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
    from comtypes import CLSCTX_ALL
    import comtypes
    PYCAW_AVAILABLE = True
except Exception:
    PYCAW_AVAILABLE = False


@contextmanager
def com_apartment():
# 現在のFlaskワーカースレッドでCOMを初期化し、処理終了時に必ず解除する。
    initialized = False
    if PYCAW_AVAILABLE:
        try:
            comtypes.CoInitialize()
            initialized = True
        except Exception as error:
            raise RuntimeError(f"Windows COM initialization failed: {error}") from error
    try:
        yield
    finally:
        if initialized:
            try:
                comtypes.CoUninitialize()
            except Exception as error:
                log_output(
                    f"COM uninitialization failed: {error}",
                    "error",
                    logger_name="dialAudioMixer",
                )

# Flaskの各エンドポイントをcommon server.pyへ登録するためのBlueprint。
blueprint = Blueprint("dialAudioMixer", __name__)

# 除外リストファイルの固定場所: 共通サーバー側で管理
SERVER_ROOT = os.path.abspath(os.path.dirname(__file__))
EXCLUDE_FILE = os.path.join(SERVER_ROOT, 'exclude.json')

# 初期化: 除外リストファイルが無ければ作成
if not os.path.exists(EXCLUDE_FILE):
    try:
        with open(EXCLUDE_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    except Exception as e:
        log_output(f"failed to create exclude file: {e}", "error", logger_name="dialAudioMixer")

# =======================
# 除外リスト読み込み/保存
# =======================
def load_excluded():
# Stream Deck一覧に表示しないアプリ名をJSONから読み込む。
    with open(EXCLUDE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_excluded(lst):
# 除外リストをJSONへ保存する。
    with open(EXCLUDE_FILE, "w", encoding="utf-8") as f:
        json.dump(lst, f, indent=2)


# =======================
# /excluded : 除外リストの取得
# =======================
@blueprint.get("/excluded")
def get_excluded():
# 除外リストをRESTクライアントへ返す。
    try:
        return jsonify(load_excluded())
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# =======================
# /apps : 音声セッションのあるアプリ一覧取得
# =======================
@blueprint.get("/apps")
def list_audio_apps():
    # アクティブな音声セッションをアプリ名ごとに集約して返す。
    excluded = load_excluded()
    result = []
    seen_names = set()
    try:
        with com_apartment():
            if PYCAW_AVAILABLE:
                # pycawからPID、音量、ミュート状態を取得し、同名プロセスの重複を除外する。
                try:
                    sessions = AudioUtilities.GetAllSessions()

                    for session in sessions:
                        try:
                            ctl = session._ctl
                            p = psutil.Process(session.Process.pid)
                            name, ext = os.path.splitext(session.Process.name())

                            volume = ctl.QueryInterface(ISimpleAudioVolume)

                            try:
                                current_volume = volume.GetMasterVolume()
                                current_mute = volume.GetMute()
                            except Exception:
                                current_volume = 0.0
                                current_mute = False

                            final_volume = min(1.0, max(0.0, current_volume))
                            log_output(
                                f"pid={session.Process.pid}, name={name}, vol={final_volume}, mute={current_mute}",
                                logger_name="dialAudioMixer",
                            )
                            if name not in excluded and name not in seen_names:
                                result.append({"pid": session.Process.pid, "mute": current_mute, "name": name, "volume": final_volume})
                                seen_names.add(name)
                        except Exception:
                            pass
                except Exception as e:
                    log_output(f"ERROR: {e}", "error", logger_name="dialAudioMixer")
            else:
                # pycawが利用できない場合は全プロセスを返す（重複除去）
                for p in psutil.process_iter(["pid", "name"]):
                    name = p.info["name"]
                    if name not in excluded and name not in seen_names:
                        result.append({
                            "pid": p.info["pid"],
                            "name": name,
                            "volume": 0.0,
                            "mute": False,
                        })
                        seen_names.add(name)
    except RuntimeError as e:
        log_output(str(e), "error", logger_name="dialAudioMixer")
        return jsonify({"status": "error", "message": str(e)}), 503
    return jsonify(result)


# =======================
# /exclude : アプリ名を除外リストに追加
# =======================
@blueprint.get("/exclude")
def add_exclude():
    # 指定アプリを除外リストへ追加する。重複登録は行わない。
    name = request.args.get("name")
    if not name:
        return jsonify({"status": "error", "message": "missing name"}), 400
    excluded = load_excluded()
    if name not in excluded:
        excluded.append(name)
        save_excluded(excluded)
    return jsonify({"status": "ok"})

# =======================
# /unexclude : アプリ名を除外リストから削除
# =======================
@blueprint.get("/unexclude")
def remove_exclude():
    # 指定アプリを除外リストから削除する。
    name = request.args.get("name")
    if not name:
        return jsonify({"status": "error", "message": "missing name"}), 400
    excluded = load_excluded()
    if name in excluded:
        excluded.remove(name)
        save_excluded(excluded)
    return jsonify({"status": "ok"})


# =======================
# /mute : ミュート設定・解除
# =======================
@blueprint.get("/mute_set")
def set_mute_absolute():
    # 同名の全プロセスセッションへミュート状態を一括設定する。
    if not PYCAW_AVAILABLE:
        return jsonify({"status": "error", "message": "pycaw not installed"}), 500

    name_arg = request.args.get("name")
    mute_arg = request.args.get("mute")
    if not name_arg or mute_arg is None:
        return jsonify({"status": "error", "message": "missing name or mute"}), 400
    mute = mute_arg.lower() in ("1", "true", "yes")

    try:
        with com_apartment():
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                try:
                    ctl = session._ctl
                    name, ext = os.path.splitext(session.Process.name())
                except Exception:
                    continue
                if name == name_arg:
                    volctl = ctl.QueryInterface(ISimpleAudioVolume)
                    volctl.SetMute(mute, None)
    except Exception as e:
        log_output(f"mute_set COM error: {e}", "error", logger_name="dialAudioMixer")
        return jsonify({"status": "error", "message": "Windows audio session is temporarily unavailable"}), 503

    return jsonify({"status": "ok", "mute": mute})


# =======================
# /volume_set : 絶対値で音量設定
# =======================
@blueprint.get("/volume_set")
def set_volume_absolute():
    # 同名の全プロセスセッションへ0.0～1.0の絶対音量を設定する。
    if not PYCAW_AVAILABLE:
        return jsonify({"status": "error", "message": "pycaw not installed"}), 500
    name_arg = request.args.get("name")
    vol_arg = request.args.get("vol")
    try:
        vol = float(vol_arg)
    except Exception:
        return jsonify({"status": "error", "message": "invalid pid or vol"}), 400

    vol = min(1.0, max(0.0, vol))
    try:
        with com_apartment():
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                try:
                    ctl = session._ctl
                    name, ext = os.path.splitext(session.Process.name())
                except Exception:
                    continue
                if name == name_arg:
                    volctl = ctl.QueryInterface(ISimpleAudioVolume)
                    volctl.SetMasterVolume(vol, None)
    except Exception as e:
        log_output(f"volume_set COM error: {e}", "error", logger_name="dialAudioMixer")
        return jsonify({"status": "error", "message": "Windows audio session is temporarily unavailable"}), 503

    return jsonify({"status": "ok", "volume": vol})

# =======================
# /_log : デバッグログ受信
# =======================
@blueprint.get("/_log")
def receive_log():
    # main.jsから送られるデバッグログをサーバーコンソールへ出力する。
    m = request.args.get("m")
    try:
        log_output(f"{m}", "debug", logger_name="dialAudioMixer")
    except Exception:
        log_output("<unprintable message>", "error", logger_name="dialAudioMixer")
    return jsonify({"status": "ok"})

# =======================
# /icon : プロセスのアイコン取得
# =======================
@blueprint.get("/icon")
def get_icon():
    # 実行中プロセスのEXEからアイコンを抽出し、ブラウザ表示用PNGへ変換する。
    pid_arg = request.args.get('pid')
    if not pid_arg:
        return jsonify({"status": "error", "message": "missing pid"}), 400
    try:
        pid = int(pid_arg)
    except Exception:
        return jsonify({"status": "error", "message": "invalid pid"}), 400

    try:
        p = psutil.Process(pid)
        exe_path = p.exe()
    except Exception as e:
        log_output(f"process lookup error: {e}", "error", logger_name="dialAudioMixer")
        return jsonify({"status": "error", "message": "process not found"}), 404

    tmp = None
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        tmp.close()
        ok = extract_icon(exe_path, tmp.name)
        if not ok:
            try: os.remove(tmp.name)
            except Exception: pass
            return jsonify({"status": "error", "message": "icon extraction failed"}), 500
        with open(tmp.name, 'rb') as f:
            b = f.read()
        data_url = 'data:image/png;base64,' + base64.b64encode(b).decode('ascii')

        try: os.remove(tmp.name)
        except Exception: pass
        return jsonify({"status": "ok", "data_url": data_url})
    except Exception as e:
        log_output(f"ERROR: {e}", "error", logger_name="dialAudioMixer")
        if tmp:
            try: os.remove(tmp.name)
            except Exception: pass
        return jsonify({"status": "error", "message": str(e)}), 500

# =======================
# 登録
# =======================
def register(app):
    app.register_blueprint(blueprint)
