import logging
import re
import tkinter as tk
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

import requests
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.txt"


def read_config():
    config = {}

    with CONFIG_FILE.open("r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or "=" not in line:
                continue

            key, value = line.split("=", 1)
            config[key.strip()] = value.strip()

    for key in ("SearchUrl", "TargetPrice", "LogFile", "Trigger"):
        if key not in config:
            raise ValueError(f"config.txtに{key}がありません。")

    #TargetPrice が空の場合に対応
    value = config["TargetPrice"].strip()
    config["TargetPrice"] = int(value) if value else None
    config["Trigger"] = config["Trigger"].upper()

    if config["Trigger"] not in ("ON", "OFF"):
        raise ValueError("TriggerはONまたはOFFにしてください。")

    return config


def make_search_url(base_url, target_price):
    """検索URLに価格を設定する。TargetPriceが空白なら元のURLを返す。"""
    if target_price is None:
        return base_url
    
    parts = urlsplit(base_url)

    params = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key != "pdf_pr"
    ]
    params.append(("pdf_pr", f"-{target_price}"))

    return urlunsplit((
        parts.scheme,
        parts.netloc,
        parts.path,
        urlencode(params),
        parts.fragment,
    ))


def get_product_count(url):
    """検索結果ページから「○製品」の件数を取得する。"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/130.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code == 404:
        #Sec-Fetchを送っていないせい？手動だと普通に表示されるのに、検索結果ゼロのとき404を返される
        return 0

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = soup.get_text(" ", strip=True)

    match = re.search(r"([\d,]+)\s*製品", page_text)

    if not match:
        raise ValueError(
            "製品件数を取得できません。ページ構造を確認してください。"
        )

    return int(match.group(1).replace(",", ""))


def show_notification(count, target_price, search_url):
    """最前面に通知ウィンドウを表示する。"""
    root = tk.Tk()
    root.title("価格.com 価格通知")
    root.geometry("460x200")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    root.lift()
    root.focus_force()

    tk.Label(
        root,
        text=f"希望価格以下の商品が、{count}個見つかりました！",
        font=("Meiryo UI", 14, "bold"),
        wraplength=430,
        pady=20,
    ).pack()

    if target_price is None:
        price_text = "設定価格：指定なし"
    else:
        price_text = f"設定価格：{target_price:,}円以下"

    tk.Label(
        root,
        text=price_text,
        font=("Meiryo UI", 11),
    ).pack()

    buttons = tk.Frame(root)
    buttons.pack(pady=15)

    def open_search():
        import webbrowser
        webbrowser.open(search_url)

    tk.Button(
        buttons,
        text="検索結果を開く",
        command=open_search,
        width=15,
    ).pack(side="left", padx=5)

    tk.Button(
        buttons,
        text="閉じる",
        command=root.destroy,
        width=10,
    ).pack(side="left", padx=5)

    root.mainloop()


def main():
    config = read_config()

    # ログ初期化（Trigger より前に移動）
    log_path = Path(config["LogFile"])
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        filename=str(log_path),
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        encoding="utf-8",
        force=True,
    )

    logging.getLogger().addHandler(logging.StreamHandler())

    # Trigger=OFF の場合でもログを出す
    if config["Trigger"] == "OFF":
        logging.info("TriggerがOFFなので終了します。")
        return

    # ここから通常処理
    try:
        search_url = make_search_url(
            config["SearchUrl"],
            config["TargetPrice"],
        )

        count = get_product_count(search_url)

        logging.info(
            "検索結果=%s製品 / 設定価格=%s円以下 / URL=%s",
            count,
            config["TargetPrice"],
            search_url,
        )

        if count >= 1:
            show_notification(
                count,
                config["TargetPrice"],
                search_url,
            )
        else:
            logging.info("該当商品なし。通知せず終了。")

    except Exception:
        logging.exception("価格チェックに失敗しました。")



if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("エラーです:", e)
        raise
