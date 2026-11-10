"""PCゲームプレイ用 自動スクリーンショットツール (screenshotter)

要件定義書に基づく実装:
- 低負荷・高速動作 (mss + Pillow WebP)
- メインディスプレイのみキャプチャ
- 前回到達終了時点から + n秒後の実行制御 (詰まり防止)
- yyyymmddhhmmss.webp 形式で無条件上書き保存
- config.json による設定管理
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import mss
from PIL import Image


def load_config(config_path: Path) -> dict:
    """設定ファイルを読み込み、検証する。"""
    if not config_path.exists():
        sys.exit(
            f"[ERROR] 設定ファイルが見つかりません: {config_path}\n"
            f"ヒント: 'config.sample.json' をコピーして 'config.json' を作成してください。"
        )

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        sys.exit(f"[ERROR] 設定ファイルの読み込みに失敗しました: {e}")

    interval = config.get("interval_seconds", 5.0)
    save_dir = config.get("save_directory", "./screenshots")
    quality = config.get("quality", 80)

    if not isinstance(interval, (int, float)) or interval <= 0:
        sys.exit(f"[ERROR] interval_seconds は 0 より大きい数値である必要があります: {interval}")

    if not isinstance(quality, int) or not (1 <= quality <= 100):
        sys.exit(f"[ERROR] quality は 1 から 100 の整数である必要があります: {quality}")

    if not isinstance(save_dir, str) or not save_dir.strip():
        sys.exit(f"[ERROR] save_directory が不正です: {save_dir}")

    return {
        "interval_seconds": float(interval),
        "save_directory": save_dir,
        "quality": quality,
    }


def main():
    base_dir = Path(__file__).resolve().parent
    config_file = base_dir / "config.json"

    config = load_config(config_file)
    interval = config["interval_seconds"]
    quality = config["quality"]

    # 保存先ディレクトリのパス解決
    save_dir_path = Path(config["save_directory"])
    if not save_dir_path.is_absolute():
        save_dir_path = (base_dir / save_dir_path).resolve()

    # 起動時に1回だけディレクトリを作成（撮影ごとの存在確認I/Oを省くため）
    try:
        save_dir_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        sys.exit(f"[ERROR] 保存先ディレクトリの作成に失敗しました: {e}")

    save_dir_str = str(save_dir_path)

    try:
        with mss.MSS() as sct:
            # monitors[1] がプライマリ（メイン）ディスプレイ
            if len(sct.monitors) < 2:
                sys.exit("[ERROR] モニターが検出されませんでした。")
            primary_monitor = sct.monitors[1]

            print(
                f"[screenshotter] 実行中... (間隔: {interval}s, 品質: {quality}, "
                f"保存先: {save_dir_str})\n"
                f"[screenshotter] 停止するには Ctrl+C を押してください。"
            )

            once_mode = "--once" in sys.argv

            while True:
                # 1. 画面キャプチャ取得
                sct_img = sct.grab(primary_monitor)

                # 2. 高速バッファ変換 (BGRA raw -> RGB)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

                # 3. yyyymmddhhmmss.webp 命名で無条件保存 (標準出力なしで負荷を抑制)
                timestamp = datetime.now()
                filename = f"{timestamp.strftime('%Y%m%d%H%M%S')}.webp"
                file_path = os.path.join(save_dir_str, filename)

                img.save(file_path, format="WEBP", quality=quality)

                if once_mode:
                    break

                # 4. 詰まり防止: 処理終了時点から指定間隔スリープ
                time.sleep(interval)

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
