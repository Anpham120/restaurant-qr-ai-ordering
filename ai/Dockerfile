FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/.cache/huggingface

WORKDIR /app

COPY ai/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        torch==2.13.0+cpu \
    && pip install --no-cache-dir -r requirements.txt
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-small', revision='fd1525a9fd15316a2d503bf26ab031a61d056e98', trust_remote_code=False)"

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --create-home app \
    && chown -R app:app /app

COPY --chown=app:app ai ./ai

# Dịch vụ AI đọc hai tệp trong `backend/data/` lúc chạy, và chúng PHẢI có trong ảnh:
#
#   restaurant-facts.json   answer.py — 24 chủ đề chính sách, trả nguyên văn cho khách
#   menu-tags.json          llm_understand.py — từ điển nhãn để kiểm nhãn mô hình trả về
#
# Trước đây dòng này không có, nên `/app/backend/` không tồn tại trong ảnh. Và cả hai chỗ đọc
# đều thoái hóa IM LẶNG khi thiếu tệp (`load_facts()` trả `{}`), nên hậu quả là toàn bộ 24 chủ
# đề chính sách trả "mình chưa có dữ liệu" — không lỗi, không log. Khách hỏi giờ mở cửa và AI
# nói không biết, dù dữ liệu nằm trong repo.
#
# Bất biến này được ép trong `ai/app/test_packaging.py`: test đọc chính Dockerfile này và đối
# chiếu với đường dẫn mà mã lúc chạy thật sự dùng, nên xóa dòng dưới là test đỏ ngay.
#
# Hai tệp này thuộc về backend (chúng seed cơ sở dữ liệu qua migration EF), nên copy vào là
# đúng. Riêng `restaurant-facts.json` thì chỉ Python đọc — nếu sau này gộp nó vào
# `ai/knowledge/` thì phụ thuộc đó tự mất.
COPY --chown=app:app backend/data ./backend/data

WORKDIR /app/ai

ENV AI_SERVICE_HOST=0.0.0.0
ENV AI_SERVICE_PORT=8001
ENV HF_HUB_OFFLINE=1

USER app
CMD ["sh", "-c", "uvicorn app.main:app --host ${AI_SERVICE_HOST:-127.0.0.1} --port ${AI_SERVICE_PORT:-8001}"]
