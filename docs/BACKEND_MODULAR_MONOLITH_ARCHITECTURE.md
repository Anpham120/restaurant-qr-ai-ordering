# Backend Modular Monolith Architecture

## 1. Current Structure Overview

Backend sử dụng kiến trúc **Modular Monolith** với các module được tổ chức theo feature/capability.

```
backend/
├── src/RestaurantQrAiOrdering.Api/
│   ├── Program.cs                    # Composition root - đăng ký tất cả modules
│   ├── Auth/                         # Authentication & Authorization
│   ├── Users/                        # User management
│   ├── Menu/                         # Menu & Category management
│   ├── Tables/                       # Restaurant table & QR management
│   ├── Orders/                       # Order lifecycle
│   ├── Payments/                     # Payment transactions (VietQR)
│   ├── Chat/                         # AI Chat assistant
│   ├── Realtime/                     # SignalR notifications
│   ├── Categories/                   # Category management (legacy - see Menu)
│   ├── Data/                         # Data stores & seeding
│   ├── Errors/                       # Error handling
│   ├── Common/                       # (reserved for future shared code)
│   ├── Features/                     # (reserved for future feature folders)
│   ├── Infrastructure/               # (reserved for cross-cutting concerns)
│   └── Entities/                     # Domain entities (shared across modules)
├── Entities/                         # Root domain entities
│   ├── Order.cs
│   ├── OrderItem.cs
│   ├── Payment.cs
│   ├── Category.cs
│   ├── MenuItem.cs
│   ├── RestaurantTable.cs
│   ├── ChatSession.cs
│   ├── ChatMessage.cs
│   └── KnowledgeEntry.cs
└── Enums/                            # Shared enumerations
    ├── OrderStatus.cs
    ├── OrderType.cs
    ├── OrderItemStatus.cs
    ├── PaymentStatus.cs
    └── PaymentMethod.cs
```

## 2. Module Boundaries

### 2.1 Auth Module (`Auth/`)

**Trách nhiệm**: Authentication và JWT token management

**Public API**:
- `IAuthService` - login, validate, generate tokens
- `HmacJwtAuthenticationHandler` - JWT authentication middleware
- Registration: `AddRestaurantAuth()`, `MapAuthEndpoints()`

**Dependencies**: Không phụ thuộc module khác

**Key files**:
- `AuthEndpoints.cs` - API endpoints
- `JwtTokenService.cs` - JWT generation/validation
- `HmacJwtAuthenticationHandler.cs` - Auth middleware
- `AuthServiceRegistration.cs` - DI registration

### 2.2 Users Module (`Users/`)

**Trách nhiệm**: User account management, password hashing, role catalog

**Public API**:
- `IUserStore` - user registration, credential validation
- `IRoleCatalog` - role management
- `IPasswordHasher` - password hashing

**Dependencies**: Không phụ thuộc module khác

**Key files**:
- `UserStore.cs` - user CRUD operations
- `UserAccount.cs` - user entity
- `PasswordHasher.cs` - password hashing
- `RoleCatalog.cs` - predefined roles

### 2.3 Menu Module (`Menu/`)

**Trách nhiệm**: Menu items và categories management

**Public API**:
- `RestaurantDataStore` - category & menu item CRUD
- Registration: `AddRestaurantMenuTableApis()`, `MapRestaurantMenuTableApis()`

**Dependencies**: Không phụ thuộc module khaca

**Key files**:
- `MenuEndpoints.cs` - API endpoints
- `MenuContracts.cs` - request/response DTOs
- `Data/RestaurantDataStore.cs` - data access

**NOTE**: Hiện tại categories được quản lý qua `Data/RestaurantDataStore` cùng với menu items. Đây là một violation nhẹ - nên có `ICategoryStore` riêng.

### 2.4 Tables Module (`Tables/`)

**Trách nhiệm**: Restaurant table và QR code management

**Public API**:
- `RestaurantDataStore.GetActiveTable()` - get table by code
- Registration: `AddRestaurantMenuTableApis()`, `MapRestaurantMenuTableApis()`

**Dependencies**: `Menu` module (share `RestaurantDataStore`)

**Key files**:
- `TableEndpoints.cs` - API endpoints
- `TableContracts.cs` - request/response DTOs

**NOTE**: Tables data cũng nằm trong `RestaurantDataStore`. Nên tách thành `ITableStore` riêng.

### 2.5 Orders Module (`Orders/`)

**Trách nhiệm**: Order lifecycle management

**Public API**:
- `IOrderStore` - order CRUD, status transitions
- Registration: `AddRestaurantOrderApis()`, `MapOrderEndpoints()`

**Dependencies**: `Menu` module (để validate menu items)

**Key files**:
- `OrderStore.cs` - order business logic
- `OrderEndpoints.cs` - API endpoints
- `OrderContracts.cs` - request/response DTOs
- `OrderSnapshots.cs` - read models

**Domain Rules**:
- Order không được cancel khi đã ở trạng thái `Preparing`, `Ready`, `Served`, `Delivering`, `Delivered`, `Completed`
- Order items không được cancel riêng lẻ khi đã `Preparing`, `Ready`, `Served`

### 2.6 Chat Module (`Chat/`)

**Trách nhiệm**: AI-powered chat assistant

**Public API**:
- `IChatStore` - chat session/message CRUD
- `IChatAiProvider` - AI provider abstraction
- `IChatAssistantService` - chat business logic
- Registration: `AddRestaurantChatApis()`, `MapRestaurantChatApis()`

**Dependencies**: `Menu` module (để lấy menu items context)

**Key files**:
- `ChatEndpoints.cs` - API endpoints
- `ChatStore.cs` - session/message storage
- `ChatAiProvider.cs` - AI integration (9router, Python RAG)
- `ChatContracts.cs` - request/response DTOs

**AI Providers Supported**:
- `9router` - OpenAI-compatible API
- `python-rag` - Custom Python RAG service

### 2.7 Realtime Module (`Realtime/`)

**Trách nhiệm**: Real-time notifications via SignalR

**Public API**:
- `IOrderRealtimeNotifier` - order update notifications
- Registration: `AddRestaurantRealtimeApis()`, `MapRestaurantRealtimeApis()`

**Dependencies**: Không phụ thuộc module khác

**Key files**:
- `OrderUpdatesHub.cs` - SignalR hub
- `SignalROrderRealtimeNotifier.cs` - SignalR implementation
- `OrderRealtimeContracts.cs` - notification DTOs

### 2.8 Payments Module (`Payments/`)

**Trách nhiệm**: Payment transactions và VietQR integration

**Public API**:
- Registration: `AddRestaurantPaymentApis(config)`
- VietQR payload generation và payment status tracking

**Dependencies**: `Orders` module (gắn payment vào order)

**Key files**:
- `PaymentEndpoints.cs` - API endpoints
- Migration `AddPaymentTransactions` - bảng `payment_transactions`

## 3. Dependency Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      Program.cs                              │
│              (Composition Root - DI Container)               │
└────────────────────────────┬────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Auth Module    │ │  Users Module   │ │  Menu Module    │
│  - JWT          │ │  - UserStore     │ │  - DataStore    │
│  - AuthService  │ │  - PasswordHash  │ │  - MenuItems    │
└─────────────────┘ └─────────────────┘ │  - Categories   │
                                        └────────┬─────────┘
                                                 │
                         ┌───────────────────────┼───────────────────────┐
                         │                       │                       │
                         ▼                       ▼                       ▼
              ┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
              │ Tables Module   │       │ Orders Module   │       │  Chat Module    │
              │  - TableStore   │       │  - OrderStore   │       │  - ChatStore    │
              │  - QR codes     │       │  - OrderStatus  │       │  - AI Provider  │
              └─────────────────┘       └─────────────────┘       └────────┬────────┘
                                                                            │
                                                                            ▼
                                                              ┌─────────────────────────┐
                                                              │  Realtime Module         │
                                                              │  - SignalR Hub          │
                                                              │  - OrderRealtimeNotifier│
                                                              └─────────────────────────┘
```

### Dependency Rules (đúng):
- Auth, Users, Menu, Realtime không phụ thuộc module khác
- Orders phụ thuộc Menu (để validate menu items)
- Chat phụ thuộc Menu (để lấy menu context)
- Tables chia sẻ `RestaurantDataStore` với Menu

### Dependency Violations (cần fix):
1. **Orders → Menu**: Nên qua interface (`IMenuItemValidator`) thay vì trực tiếp vào `RestaurantDataStore`
2. **Chat → Menu**: Nên qua interface (`IMenuItemProvider`) thay vì trực tiếp vào `RestaurantDataStore`
3. **Tables + Menu share DataStore**: Nên có `ITableStore` và `IMenuStore` riêng

## 4. Data Layer

### 4.1 In-Memory Stores (mặc định khi chưa cấu hình DB)

Khi `ConnectionStrings:DefaultConnection` trống, app chạy bằng các in-memory store dưới đây. Khi có connection string, EF Core + PostgreSQL (xem 4.3) được kích hoạt.

| Store | Module | Entity | Thread-Safe | Notes |
|-------|--------|--------|-------------|-------|
| `RestaurantDataStore` | Menu, Tables | Category, MenuItem, RestaurantTable | Yes (lock) | Seed data cứng |
| `OrderStore` | Orders | Order, OrderItem, Payment | Yes (lock) | Không có seed |
| `ChatStore` | Chat | ChatSession, ChatMessage | Yes (lock) | Không có seed |
| `UserStore` | Users | UserAccount | Yes (lock) | Không có seed |

### 4.2 Seed Data

Seed data được định nghĩa trong `RestaurantDataStore`:

```csharp
// Categories: 6 danh mục (Khai vi, Mon chinh, Pho va bun, Hai san, Do uong, Trang mieng)
// MenuItems: 12 món mẫu
// Tables: 8 bàn (T01 - T08) với QR tokens cứng
```

**NOTE**: Seed data này là **initial data for development/demo only**. Khi có database thật, seed sẽ được thay thế bằng migration seed hoặc database seeding.

### 4.3 EF Core + PostgreSQL (đã triển khai, tùy chọn)

Lớp database đã có sẵn và được kích hoạt khi cấu hình `ConnectionStrings:DefaultConnection` (xem `BACKEND_DATABASE_SETUP.md`):

- EF Core + Npgsql, `RestaurantDbContext`.
- Migrations: `InitialCreate`, `AddUsers`, `AddTableSessions`, `AddPaymentTransactions`.
- Seed bằng `HasData` (categories, menu items, tables, demo users).
- `DbUserStore` thay cho `UserStore` in-memory khi dùng DB.

## 5. Cross-Cutting Concerns

### 5.1 Error Handling

- `ApiErrorFactory` - tạo standardized error responses
- Middleware trong `Program.cs` - handle `BadHttpRequestException`, `JsonException`
- HTTP status codes chuẩn: 400 (validation), 401 (auth), 403 (forbidden), 404 (not found)

### 5.2 CORS

- Policy name: `CmcRestaurantCors`
- Allowed origins từ config `CORS_ALLOWED_ORIGINS` hoặc hardcoded defaults
- Cho phép any header và method

### 5.3 Authentication

- HMAC + JWT hybrid
- `HmacJwtAuthenticationHandler` - validates HMAC signature
- `JwtTokenService` - generates JWT tokens
- Role-based authorization: `Customer`, `CounterStaff`, `KitchenStaff`, `Manager`, `Admin`

## 6. API Organization

### 6.1 Endpoint Registration Pattern

Mỗi module có extension methods để đăng ký DI và map endpoints:

```csharp
// DI Registration (trong Program.cs)
builder.Services.AddRestaurantAuth(config);
builder.Services.AddRestaurantMenuTableApis();
builder.Services.AddRestaurantOrderApis();
builder.Services.AddRestaurantRealtimeApis();
builder.Services.AddRestaurantChatApis();

// Endpoint Mapping
app.MapAuthEndpoints();
app.MapRestaurantMenuTableApis();
app.MapOrderEndpoints();
app.MapRestaurantRealtimeApis();
app.MapRestaurantChatApis();
```

### 6.2 Module Registration Files

| File | Module | Extension Methods |
|------|--------|-------------------|
| `AuthServiceRegistration.cs` | Auth | `AddRestaurantAuth()` |
| `MenuTableApiRegistration.cs` | Menu, Tables | `AddRestaurantMenuTableApis()`, `MapRestaurantMenuTableApis()` |
| `OrderApiRegistration.cs` | Orders | `AddRestaurantOrderApis()` |
| `RealtimeApiRegistration.cs` | Realtime | `AddRestaurantRealtimeApis()`, `MapRestaurantRealtimeApis()` |
| `ChatApiRegistration.cs` | Chat | `AddRestaurantChatApis()`, `MapRestaurantChatApis()` |
| `UserServiceRegistration.cs` | Users | `AddRestaurantUserServices()` |

## 7. Testing Strategy

Tests được đặt trong `tests/RestaurantQrAiOrdering.Api.Tests/`:

```
tests/
├── Auth/AuthEndpointTests.cs
├── Orders/OrderEndpointTests.cs
├── Payments/PaymentEndpointTests.cs
├── Tables/TableEndpointTests.cs
├── Menu/MenuEndpointTests.cs
├── Chat/ChatEndpointTests.cs
├── Realtime/OrderHubEndpointTests.cs
├── E2E/MultiDeviceE2ETests.cs
├── HealthEndpointTests.cs
└── CorsEndpointTests.cs
```

## 8. Known Issues & Technical Debt

### 8.1 Mock/Demo Logic

1. **`Order.MockDeliveryFee`** (line 39 in `Entities/Order.cs`)
   - Giá trị fixed 0 - chỉ là placeholder
   - Cần thay bằng calculated delivery fee (đã có `Payments/` module để mở rộng)

2. **Seed Data Hardcoded**
   - Menu items, categories, tables đều là sample data
   - Cần database thật để replace

### 8.2 Architectural Violations

1. **Cross-Module Data Access**: Orders/Chat endpoints inject `RestaurantDataStore` directly
   - `OrderEndpoints.cs` validates menu items by calling `RestaurantDataStore` directly
   - `ChatAssistantService` calls `GetMenuItems()` for AI context
   - Fix: Tạo interfaces `IMenuItemValidator`, `IMenuItemProvider`

2. **Shared God Object DataStore**: `RestaurantDataStore` holds Categories, MenuItems, Tables
   - Shared as singleton across all modules
   - Fix: Tách thành `IMenuStore`, `ICategoryStore`, và `ITableStore`

3. **Order Contains Embedded Payment**: `Order.cs` has embedded `Payment` entity
   - Tight coupling between Order và Payment bounded contexts
   - Đã có `Payments/` module (PaymentEndpoints + `payment_transactions`); cần tách dần `Payment` entity nhúng trong `Order` ra khỏi Order context

4. **Thread-Safety Duplication**: Mỗi store re-implements `lock`-based thread safety
   - Fix: Extract thành shared `SynchronizedCollection<T>` hoặc `ThreadSafeStore` base class

5. **Flat Entities**: Tất cả entities trong `Entities/`
   - Fix: Tổ chức entities theo module thay vì để phẳng trong `Entities/`

### 8.3 Reserved Folders

- `Common/` - chưa sử dụng (reserved for shared utilities)
- `Features/` - chưa sử dụng (reserved for feature-based organization)
- `Infrastructure/` - chưa sử dụng (reserved for cross-cutting concerns)

## 9. References

- [BACKEND_DATABASE_SETUP.md](./BACKEND_DATABASE_SETUP.md) - Hướng dẫn cấu hình PostgreSQL + EF Core migrations
- [API_CONTRACT.md](./API_CONTRACT.md) - API specification
- [AI_CHATBOT.md](./AI_CHATBOT.md) - AI integration details
