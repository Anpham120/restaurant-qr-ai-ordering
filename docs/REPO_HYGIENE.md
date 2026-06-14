# Repo hygiene and production cleanup

## Mục tiêu

Repo chỉ chứa source code, migration, cấu hình mẫu và tài liệu cần thiết để review, build, test và deploy. File sinh tự động, log, output demo, secret thật và file scratch khi làm GitHub evidence không được commit.

## Quy tắc ignore

- .NET: không commit `bin/`, `obj/`, `*.csproj.user`.
- Frontend: không commit `node_modules/`, `dist/`, `*.tsbuildinfo`, `coverage/`.
- Python/AI: không commit `__pycache__/`, `*.pyc`, `.pytest_cache/`, virtual environment.
- Local evidence/demo: không commit `output/`, `site-demo/`, `coursework/`, `tools/`, `commit_msg.txt`, `issue_comment.txt`, `pr*_body.txt`.
- Secrets: chỉ commit file mẫu như `.env.example`; không commit `.env`, `.env.*`, private key, token hoặc log chứa secret.

## Mock và demo data

- Production build không được phụ thuộc mock/localStorage để che lỗi backend thật.
- Demo data được phép tồn tại khi phục vụ dev/staging, nhưng phải được bật rõ bằng môi trường dev/staging hoặc seed/migration có kiểm soát.
- Nếu cần mock cho test hoặc story nội bộ, đặt trong test/dev-only path và ghi rõ cách bật. Không render payload debug hoặc JSON mẫu lên giao diện production.

## Checklist trước khi tạo PR

1. Chạy `git status --short --ignored` và xác nhận PR không chứa build output, log, secret hoặc file tạm.
2. Chạy scan cơ bản cho production UI: `rg -n "mock|payload|debug|JSON.stringify|localStorage" frontend/src backend/src`.
3. Chạy build/test liên quan trước khi merge.
