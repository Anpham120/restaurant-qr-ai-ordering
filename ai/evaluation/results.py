# -*- coding: utf-8 -*-
"""Ghi và đọc kết quả của những phép đo KHÔNG tính lại được trong notebook.

Vấn đề mà mô-đun này giải
-------------------------
Notebook tính lại được gần hết số của nó ngay trong ô mã: nạp thực đơn, chấm tập trả lời, dựng chỉ
mục, so ba bộ truy hồi. Nhưng hai phép đo thì không:

    golden qua HTTP thật   cần backend + Postgres + dịch vụ AI đang chạy
    LLM+RAG loại C         cần `LLM_API_KEY` thật; mỗi lần chạy tốn tiền và vài phút

Nên hai con số đó bị VIẾT TAY vào notebook — và đúng những chỗ viết tay là chỗ đã trôi. Notebook
từng in "tất định 122/122" (nay 140 ca), "kho 84 tài liệu / 303 đoạn" (nay 108 / 449), "embedding
Hit@5 0,921" (đo kho cũ 303 đoạn). Ba con số, cả ba từng đúng, cả ba sai đi lặng lẽ.

Quy tắc số 3 của chính notebook viết: *"Không viết số vào tài liệu — số phải tính được, nếu không nó
sẽ trôi."* Notebook vi phạm nó ở đúng những chỗ nó không tính lại được.

Cách sửa không phải "nhớ cập nhật"
----------------------------------
Nhớ cập nhật là cách sửa đã thất bại ba lần ở trên. Cách sửa bằng cấu trúc: bộ chạy GHI ra tệp, và
notebook ĐỌC tệp. Khi ai đó chạy lại phép đo, con số trong notebook đổi theo mà không ai phải sửa
chữ nào.

Và `doc()` **báo lỗi to** khi thiếu tệp thay vì trả số cũ hay số mặc định. Thiếu số thì nói thiếu —
in một số không rõ đo lúc nào tệ hơn không in gì.

Vì sao `dieu_kien` là bắt buộc
------------------------------
"84/103" không so được với "67/103" nếu không biết lần nào bật đường sinh, lần nào dùng bộ truy hồi
nào, và mỗi lần chạy mã của ngày nào. Điều kiện của lần chạy là phần đầu tiên bị bỏ và là phần khiến
con số vô dụng khi bị bỏ. Nên nó là tham số bắt buộc, không phải tham số tùy chọn.

Vì sao thư mục tên `measurements/` chứ không `results/`
-----------------------------------------------------
`ai/evaluation/measurements/` — tên đầu tiên em chọn — nằm trong `.gitignore` dòng 24, vì nó là chỗ đầu ra
TẠM của bản cũ. Ghi vào đó thì tệp KHÔNG BAO GIỜ vào git, và notebook trên máy người khác báo
`FileNotFoundError` cho một phép đo đã chạy xong.

Lỗi im lặng theo cách khó thấy nhất: mọi thứ hoạt động hoàn hảo trên máy đã chạy phép đo. Chỉ người
thứ hai clone repo mới gặp.

Tên `measurements/` nói đúng bản chất: đây là BẢN GHI của phép đo, không phải đầu ra tạm — và nhờ
vậy nó không rơi vào một mẫu ignore viết cho đầu ra tạm.

Tệp kết quả CÓ vào git — chúng là bằng chứng của phép đo, và CI không dựng nổi stack có `LLM_API_KEY`
thật để sinh lại chúng.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS_DIR = HERE / "measurements"


def ghi(ten: str, so: dict, dieu_kien: dict) -> Path:
    """Ghi một phép đo kèm điều kiện của lần chạy. Trả về đường dẫn đã ghi."""
    if not dieu_kien:
        raise ValueError(
            "`dieu_kien` rỗng. Một con số không có điều kiện của lần chạy thì không so được với "
            "con số sau, nên nó gần như vô dụng — xem docstring của mô-đun."
        )
    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / f"{ten}.json"
    path.write_text(
        json.dumps({"so": so, "dieu_kien": dieu_kien}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def doc(ten: str) -> dict:
    """Đọc một phép đo. BÁO LỖI khi thiếu, không trả số mặc định.

    Lỗi phải nói ra CÁCH sinh lại tệp, vì người đọc notebook thường không phải người chạy phép đo.
    """
    path = RESULTS_DIR / f"{ten}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Chưa có kết quả `{ten}`.\n"
            f"  Phép đo này cần stack thật hoặc mô hình thật nên notebook không tính lại được.\n"
            f"  Sinh lại: xem {RESULTS_DIR.relative_to(HERE.parent.parent)}/README.md\n"
            f"  KHÔNG điền số bằng tay vào chỗ này — đó chính là cách ba con số cũ đã trôi."
        )
    return json.loads(path.read_text(encoding="utf-8-sig"))
