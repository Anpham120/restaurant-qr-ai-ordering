<div align="center">
  <img src="frontend/src/mocks/images/logo.png" alt="Logo CMC Restaurant" width="220" />
  <h1>CMC Restaurant — QR AI Ordering</h1>
  <p><strong>Quét QR, gọi món, phối hợp vận hành và tư vấn món ăn bằng AI trên một nền tảng thống nhất.</strong></p>
  <p>
    <a href="https://cmcrestaurant.app">Trải nghiệm khách hàng</a> ·
    <a href="https://admin.cmcrestaurant.app">Cổng vận hành</a> ·
    <a href="docs/BA_SA_SYSTEM_DESIGN.md">Kiến trúc</a> ·
    <a href="docs/API_CONTRACT.md">API</a> ·
    <a href="#bắt-đầu-phát-triển">Bắt đầu phát triển</a>
  </p>
  <p>
    <a href="https://github.com/Anpham120/restaurant-qr-ai-ordering/actions/workflows/ci.yml"><img src="https://github.com/Anpham120/restaurant-qr-ai-ordering/actions/workflows/ci.yml/badge.svg?branch=develop" alt="CI" /></a>
    <a href="https://github.com/Anpham120/restaurant-qr-ai-ordering/actions/workflows/security.yml"><img src="https://github.com/Anpham120/restaurant-qr-ai-ordering/actions/workflows/security.yml/badge.svg?branch=develop" alt="Security" /></a>
    <a href="https://github.com/Anpham120/restaurant-qr-ai-ordering/actions/workflows/deploy-production.yml"><img src="https://github.com/Anpham120/restaurant-qr-ai-ordering/actions/workflows/deploy-production.yml/badge.svg" alt="Production Deployment" /></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-c9a227.svg" alt="License: MIT" /></a>
  </p>
</div>

---

## Sản phẩm giải quyết điều gì?

CMC Restaurant số hóa toàn bộ hành trình phục vụ tại bàn: khách mở menu bằng QR mà không cần cài ứng dụng, tự chọn món và theo dõi đơn; nhân viên và bếp nhận cùng một trạng thái vận hành; quản trị viên kiểm soát menu, bàn và đơn hàng từ một hệ thống duy nhất.

AI được đặt trong đúng vai trò hỗ trợ: tư vấn dựa trên menu và kho tri thức của nhà hàng, giải thích lựa chọn và chuyển tiếp cho nhân viên khi câu hỏi vượt phạm vi. AI không tự tạo đơn, thêm món hoặc thực hiện thanh toán.

| Khả năng | Giá trị nhận được |
| --- | --- |
| **QR ordering tại bàn** | Giảm thời gian chờ gọi món, tránh nhầm bàn và không yêu cầu cài app |
| **Điều phối theo thời gian thực** | Nhân viên, bếp và khách nhìn thấy tiến độ đơn nhất quán |
| **Không gian làm việc theo vai trò** | Customer, ordering, staff, kitchen và admin có giao diện đúng nhiệm vụ |
| **AI tư vấn có grounding** | Câu trả lời dựa trên menu/knowledge base, có guardrail và fallback được kiểm soát |
| **Vận hành có thể kiểm chứng** | CI, security checks, health checks, staging, production và rollback được quản lý bằng workflow |

## Trải nghiệm theo vai trò

| Vai trò | Trải nghiệm chính |
| --- | --- |
| **Khách hàng** | Khám phá nhà hàng, xem menu và bắt đầu hành trình gọi món |
| **Khách tại bàn** | Quét QR, chọn món, chat với AI, gửi đơn và theo dõi trạng thái |
| **Nhân viên** | Theo dõi bàn, tiếp nhận đơn và hỗ trợ khách trong quá trình phục vụ |
| **Bếp** | Xem hàng đợi món, cập nhật tiến độ chuẩn bị và phối hợp giao món |
| **Quản trị viên** | Quản lý menu, bàn, mã QR, đơn hàng và số liệu vận hành |

```mermaid
flowchart LR
  Scan["Khách quét QR tại bàn"] --> Menu["Xem menu điện tử"]
  Menu --> Cart["Chọn món và kiểm tra giỏ"]
  Menu -. "Cần gợi ý" .-> AI["AI tư vấn theo menu"]
  AI -.-> Cart
  Cart --> Order["Gửi đơn"]
  Order --> Staff["Nhân viên tiếp nhận"]
  Staff --> Kitchen["Bếp chuẩn bị món"]
  Kitchen --> Ready["Món sẵn sàng"]
  Ready --> Served["Phục vụ tại bàn"]
  Order -. "SignalR" .-> Track["Khách theo dõi trạng thái"]
  Staff -. "SignalR" .-> Track
  Kitchen -. "SignalR" .-> Track
```

## Giao diện sản phẩm

Ảnh chụp trực tiếp từ các ứng dụng production ngày **17/07/2026**. Gallery này phản ánh giao diện hiện hành, không dùng lại ảnh từ các báo cáo issue cũ.

<table>
  <tr>
    <td width="50%" align="center">
      <img src="docs/assets/readme/customer-home-2026-07-17.png" alt="Trang giới thiệu CMC Restaurant trên production" />
      <br /><strong>Website nhà hàng</strong>
    </td>
    <td width="50%" align="center">
      <img src="docs/assets/readme/customer-menu-2026-07-17.png" alt="Menu CMC Restaurant trên production" />
      <br /><strong>Menu ẩm thực hiện hành</strong>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center">
      <img src="docs/assets/readme/order-scan-2026-07-17.png" alt="Trang quét QR để gọi món tại bàn" />
      <br /><strong>Điểm vào gọi món bằng QR</strong>
    </td>
    <td width="50%" align="center">
      <img src="docs/assets/readme/operations-login-2026-07-17.png" alt="Cổng đăng nhập vận hành CMC Restaurant" />
      <br /><strong>Cổng vận hành</strong>
    </td>
  </tr>
</table>

## Kiến trúc

```mermaid
flowchart TB
  subgraph Clients["React 19 + TypeScript + Vite"]
    Customer["Customer Web"]
    Ordering["Ordering Web"]
    Staff["Staff Web"]
    Kitchen["Kitchen Web"]
    Admin["Admin Web"]
  end

  Customer --> API
  Ordering --> API
  Staff --> API
  Kitchen --> API
  Admin --> API

  subgraph Backend["ASP.NET Core API"]
    API["REST API"]
    Auth["JWT & Role-based Access"]
    Orders["Menu · Tables · Orders · Payments"]
    Hub["SignalR Order Hub"]
  end

  API --> Auth
  API --> Orders
  API <--> Hub
  Orders --> DB[("PostgreSQL 16")]
  API --> AI["FastAPI AI Service"]

  subgraph Intelligence["Grounded AI/RAG"]
    AI --> Retriever["Retriever & Query Filters"]
    Retriever --> KB["Restaurant Knowledge Base"]
    AI --> Guardrails["Grounding · Guardrails · Fallback"]
    Guardrails --> LLM["Google Gemini"]
  end
```

Backend nghiệp vụ được tổ chức như một modular monolith để giữ transaction và luồng order/payment nhất quán. AI/RAG là service độc lập vì có vòng đời dependency, evaluation và khả năng mở rộng khác với nghiệp vụ nhà hàng.

### Công nghệ chính

| Lớp | Công nghệ |
| --- | --- |
| Frontend | React 19, TypeScript, Vite, React Router, SignalR client |
| Backend | ASP.NET Core, EF Core, SignalR, JWT |
| Data | PostgreSQL 16 |
| AI service | Python 3.12, FastAPI, RAG, sentence-transformers, Gemini |
| Testing | Vitest, .NET integration tests, Python unittest/evaluation |
| Delivery | GitHub Actions, Docker Compose, Nginx, HTTPS, staging/production |

### AI, bảo mật và độ tin cậy

- **Grounded AI:** truy xuất menu và knowledge base trước khi tạo câu trả lời; filter loại món, ràng buộc và menu exclusions được kiểm thử riêng.
- **Guardrails:** AI không được phép tự tạo đơn, thay đổi giỏ hoặc thanh toán; câu hỏi ngoài phạm vi có fallback/escalation.
- **Session tại bàn:** QR token và table session được backend xác thực, xoay vòng và không được tin cậy chỉ từ client.
- **Phân quyền:** JWT và role-based authorization tách quyền customer, staff, kitchen và admin.
- **Secrets:** khóa AI, signing key và database credentials chỉ được cấu hình phía server qua environment/secrets.
- **Reliability:** health checks cho PostgreSQL, API, AI và frontend; migration tách riêng; deployment có staging, promotion và rollback.
- **Verification:** CI build/test frontend, backend, AI/RAG và kiểm tra Docker Compose trên pull request/push.

Tài liệu chuyên sâu: [modular monolith](docs/BACKEND_MODULAR_MONOLITH_ARCHITECTURE.md), [AI/RAG architecture](docs/AI_RAG_ARCHITECTURE.md), [security policy](SECURITY.md) và [production operations](docs/PRODUCTION_OPERATIONS.md).

## Bắt đầu phát triển

### Yêu cầu

- Node.js 24 và npm.
- .NET SDK 10.
- Python 3.12.
- PostgreSQL 16 hoặc Docker/Docker Compose.

Sao chép các tệp `.env.example` tương ứng và chỉ dùng secret dành cho môi trường local.

### Frontend

```powershell
cd frontend
npm ci
npm run dev
```

Các workspace khác:

```powershell
npm run dev:ordering
npm run dev:admin
npm run dev:kitchen
npm run dev:staff
```

### Backend

```powershell
dotnet run --project backend/src/RestaurantQrAiOrdering.Api/RestaurantQrAiOrdering.Api.csproj
```

Thiết lập PostgreSQL và migration: [Backend Database Setup](docs/BACKEND_DATABASE_SETUP.md).

### AI/RAG service

```powershell
cd ai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

AI service vẫn có fallback có kiểm soát khi chưa cấu hình `GEMINI_API_KEY`; xem [AI Chatbot](docs/AI_CHATBOT.md) và [AI Knowledge Base Guide](docs/AI_KNOWLEDGE_BASE_GUIDE.md).

### Kiểm chứng

```powershell
npm --prefix frontend test
npm --prefix frontend run build
dotnet test backend/RestaurantQrAiOrdering.sln --configuration Release
$env:PYTHONPATH = "ai"
python -m unittest discover -s ai/tests
python -m compileall ai/app
docker compose -f deploy/docker-compose.yml config
```

## Cấu trúc repository

```text
.
├── frontend/   # 5 React/Vite apps, shared packages và frontend tests
├── backend/    # ASP.NET Core API, domain modules và integration tests
├── ai/         # FastAPI service, RAG pipeline, knowledge base và evaluation
├── deploy/     # Docker Compose và cấu hình triển khai
├── docs/       # Product, architecture, API, quality và operations
└── .github/    # CI/CD, security, issue và pull request templates
```

## Tài liệu

Điểm bắt đầu đầy đủ: **[Documentation Hub](docs/README.md)**. Hub chỉ quảng bá các tài liệu đang được dùng làm điểm vào hiện hành; kế hoạch và bằng chứng lịch sử vẫn được giữ trong repository để truy vết nhưng không được xem là mô tả trạng thái mới nhất.

| Chủ đề | Tài liệu chính |
| --- | --- |
| Product & system design | [BA/SA System Design](docs/BA_SA_SYSTEM_DESIGN.md) · [SPEC](SPEC.md) |
| API & architecture | [API Contract](docs/API_CONTRACT.md) · [Backend Architecture](docs/BACKEND_MODULAR_MONOLITH_ARCHITECTURE.md) |
| AI & RAG | [AI/RAG Architecture](docs/AI_RAG_ARCHITECTURE.md) · [Evaluation Runbook](docs/AI_EVALUATION_RUNBOOK.md) · [Retriever ADR](docs/ai/ADR_RETRIEVER_SELECTION.md) |
| Verification | [E2E Multi-device Checklist](docs/E2E_MULTI_DEVICE_CHECKLIST.md) |
| Delivery & operations | [Deployment](docs/DEPLOYMENT.md) · [Production Operations](docs/PRODUCTION_OPERATIONS.md) |

## Trạng thái và định hướng

Dự án đang ở giai đoạn MVP/demo đã triển khai trực tuyến. Các luồng QR table session, menu, order, payment, realtime, role-based operations và AI/RAG đều có implementation cùng test/evidence trong repository; độ sẵn sàng production tiếp tục được củng cố qua evaluation, observability và security hardening.

Ưu tiên tiếp theo:

- Mở rộng regression/E2E coverage cho hành trình đa thiết bị.
- Theo dõi chất lượng retrieval và grounded response bằng bộ evaluation tái lập.
- Hoàn thiện accessibility, performance budget và trải nghiệm mobile.
- Tăng cường observability, backup/restore và operational readiness.

## Đóng góp

Đọc [CONTRIBUTING.md](CONTRIBUTING.md), tạo branch từ `develop` và dùng pull request template của dự án. Quy ước nhánh, review và release nằm trong [Documentation Hub](docs/README.md).

## Giấy phép

Dự án được phát hành theo [MIT License](LICENSE).

---

<div align="center">
  Built for a faster, clearer and more reliable restaurant service flow.
</div>
