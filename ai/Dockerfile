FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Chỉ bốn gói cho tầng HTTP. Phần dữ liệu, thước đo và tập đánh giá dùng thư viện chuẩn của Python.
#
# Ba dòng của bản cũ đã bị bỏ ở đây, và cả ba đều sẽ làm BUILD THẤT BẠI:
#
#   pip install torch==2.13.0+cpu               phiên bản đó không tồn tại (torch mới nhất ~2.x
#                                               thấp hơn nhiều), và không tệp nào trong `ai/`
#                                               import torch
#   python -c "from sentence_transformers ..."  gói đó đã bị bỏ khỏi requirements.txt ở bước 5,
#                                               sau khi đo rằng 24 chủ đề chính sách tra khóa
#                                               đúng 100% nên tầng embedding là 3GB cho 0 lợi ích
#   ENV HF_HOME / HF_HUB_OFFLINE                biến cho model không còn tải nữa
#
# Không test nào bắt được ba dòng đó, vì test chạy từ mã nguồn chứ không build ảnh. Cùng lớp lỗi
# với `CMD` trỏ vào `app.main:app` — một module không tồn tại. Xem `test_packaging.py`.
COPY ai/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --create-home app \
    && chown -R app:app /app

COPY --chown=app:app ai ./ai

# Dịch vụ AI đọc hai tệp trong `backend/data/` lúc chạy, và chúng PHẢI có trong ảnh:
#
#   menu-dataset.json   service.py — 91 món, là dữ liệu để lọc và nêu giá
#   menu-tags.json      llm_understand.py — từ điển nhãn để kiểm nhãn mô hình trả về
#
# Trước đây dòng này không có, nên `/app/backend/` không tồn tại trong ảnh. Và chỗ đọc thoái hóa
# IM LẶNG khi thiếu tệp, nên hậu quả là toàn bộ chủ đề chính sách trả "mình chưa có dữ liệu" —
# không lỗi, không log. Khách hỏi giờ mở cửa và AI nói không biết, dù dữ liệu nằm trong repo.
#
# Bất biến này được ép trong `ai/app/test_packaging.py`: test đọc chính Dockerfile này và đối
# chiếu với đường dẫn mà mã lúc chạy thật sự dùng, nên xóa dòng dưới là test đỏ ngay.
#
# Hai tệp này thuộc về backend (chúng seed cơ sở dữ liệu qua migration EF) nên copy vào là đúng.
# Kho tri thức thì KHÔNG cần dòng này — nó đã được gộp vào `ai/knowledge/`, tức nằm trong phạm vi
# `COPY ai` ở trên. Đó là cách sửa bằng cấu trúc, không phải bằng việc nhớ thêm một dòng COPY.
COPY --chown=app:app backend/data ./backend/data

WORKDIR /app/ai

ENV AI_SERVICE_HOST=0.0.0.0
ENV AI_SERVICE_PORT=8001

USER app

# Kiểm tra sức khỏe dùng `/health` chứ không dùng `/ready`. Hai endpoint khác nhau có chủ ý:
# `/health` chỉ nói tiến trình còn sống, `/ready` mới kiểm dữ liệu. Nếu healthcheck dùng `/ready`
# thì một lỗi dữ liệu sẽ làm orchestrator khởi động lại container liên tục — mà khởi động lại
# không sửa được lỗi dữ liệu.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,os,sys; \
sys.exit(0 if b'\"ok\":true' in urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('AI_SERVICE_PORT','8001')+'/health', timeout=3).read().replace(b' ',b'') else 1)"

# Điểm vào là `app/service.py`, và `--app-dir app` là BẮT BUỘC — không phải tùy chọn cho gọn.
#
# Mọi mô-đun trong `ai/app` dùng import PHẲNG (`from answer import ...`, `from understand import
# ...`), nên `ai/app` phải nằm trong `sys.path`. Test qua được vì chúng tự thêm đường dẫn đó;
# uvicorn thì không. Gọi `uvicorn app.service:app` từ `/app/ai` cho:
#
#     ModuleNotFoundError: No module named 'answer'
#
# Tức container KHỞI ĐỘNG THẤT BẠI, và ba dòng trước đó (torch, sentence_transformers, app.main)
# cũng vậy. Phát hiện được chỉ vì chạy uvicorn thật, không phải vì test — `test_packaging.py` nay
# CHẠY THỬ IMPORT trong tiến trình riêng với đúng `sys.path` mà container có.
CMD ["sh", "-c", "uvicorn service:app --app-dir app --host ${AI_SERVICE_HOST:-0.0.0.0} --port ${AI_SERVICE_PORT:-8001}"]
