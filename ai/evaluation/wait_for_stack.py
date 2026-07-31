# -*- coding: utf-8 -*-
"""Chờ backend và dịch vụ AI sẵn sàng, rồi NÓI RÕ trạng thái mô hình.

    python ai/evaluation/wait_for_stack.py
    python ai/evaluation/wait_for_stack.py --api http://127.0.0.1:5000 --giay 180

Tồn tại thành tệp riêng thay vì một dòng shell trong CI vì hai lý do:

1. Một vòng `curl` trong YAML im lặng khi hết hạn, và lúc đó bước sau đỏ với lý do sai ("không gọi
   được stack" thay vì "stack không lên"). Tệp này in ra ĐIỀU GÌ chưa lên.
2. Nó in `model_configured` và số món. Golden có thể chạy không cần mô hình — và khi nó chạy không
   mô hình thì bản ghi CI phải nói ra, chứ không để người đọc tưởng mô hình đã được kiểm.

Mã thoát: 0 khi cả hai sẵn sàng, 1 khi hết hạn.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def thu(url: str, timeout: float = 3.0) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            raw = r.read().decode()
        return json.loads(raw) if raw else {}
    except (urllib.error.URLError, OSError, ValueError):
        return None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--api", default="http://127.0.0.1:5000")
    p.add_argument("--ai", default="http://127.0.0.1:8001")
    p.add_argument("--giay", type=int, default=180, help="hết hạn, đơn vị giây")
    args = p.parse_args(argv)

    han = time.monotonic() + args.giay
    api_ok = ai = None
    while time.monotonic() < han:
        if api_ok is None:
            api_ok = thu(f"{args.api}/api/health")
        if ai is None or not ai.get("ready"):
            ai = thu(f"{args.ai}/ready")
        if api_ok is not None and ai is not None and ai.get("ready"):
            print(f"backend  : {api_ok.get('status', '?')}")
            print(f"dịch vụ AI: {ai['menu_items']} món, {ai.get('knowledge_docs')} tài liệu, "
                  f"{ai.get('knowledge_chunks')} đoạn")
            # NÓI RÕ trạng thái mô hình. Golden chạy được không cần mô hình, nhưng bản ghi CI phải
            # nói ra điều đó — nếu không thì người đọc tưởng mô hình đã được kiểm.
            if ai.get("model_configured"):
                print(f"mô hình  : {ai.get('model')} (đã cấu hình)")
            else:
                print("mô hình  : KHÔNG cấu hình — golden chạy trên đường TẤT ĐỊNH. "
                      "Đó là đường đã đạt 140/140 ca, nhưng nó không kiểm lớp mô hình.")
            return 0
        time.sleep(2)

    print(f"HẾT HẠN sau {args.giay}s:")
    print(f"  backend {args.api}/api/health : {'lên' if api_ok is not None else 'CHƯA'}")
    print(f"  dịch vụ AI {args.ai}/ready    : "
          f"{'lên' if (ai and ai.get('ready')) else f'CHƯA ({ai})'}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
