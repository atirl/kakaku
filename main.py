# 価格.com検索ツール
# 同じフォルダにconfig.txtを置いてください。
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

    config["TargetPrice"] = int(config["TargetPrice"])
    config["Trigger"] = config["Trigger"].upper()

    if config["Trigger"] not in ("ON", "OFF"):
        raise ValueError("TriggerはONまたはOFFにしてください。")

    return config


def make_search_url(base_url, target_price):
    """検索URLに価格上限を設定する。"""
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