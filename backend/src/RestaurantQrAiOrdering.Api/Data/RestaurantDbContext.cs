#nullable enable

using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Entities;
using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Api.Data;

public class RestaurantDbContext : DbContext
{
    private static readonly DateTimeOffset CategorySeededAt = new(
        new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638),
        TimeSpan.Zero);
    private static readonly DateTimeOffset MenuItemSeededAt = new(
        new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968),
        TimeSpan.Zero);
    private static readonly DateTimeOffset TableSeededAt = new(
        new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629),
        TimeSpan.Zero);

    public RestaurantDbContext(DbContextOptions<RestaurantDbContext> options)
        : base(options)
    {
    }

    public DbSet<Category> Categories => Set<Category>();
    public DbSet<MenuItem> MenuItems => Set<MenuItem>();
    public DbSet<RestaurantTable> RestaurantTables => Set<RestaurantTable>();
    public DbSet<TableSession> TableSessions => Set<TableSession>();
    public DbSet<Order> Orders => Set<Order>();
    public DbSet<OrderItem> OrderItems => Set<OrderItem>();
    public DbSet<OrderStatusHistory> OrderStatusHistories => Set<OrderStatusHistory>();
    public DbSet<Payment> Payments => Set<Payment>();
    public DbSet<PaymentTransaction> PaymentTransactions => Set<PaymentTransaction>();
    public DbSet<ChatSession> ChatSessions => Set<ChatSession>();
    public DbSet<ChatMessage> ChatMessages => Set<ChatMessage>();
    public DbSet<KnowledgeEntry> KnowledgeEntries => Set<KnowledgeEntry>();
    public DbSet<User> Users => Set<User>();
    public DbSet<Promotion> Promotions => Set<Promotion>();
    public DbSet<LoyaltyMember> LoyaltyMembers => Set<LoyaltyMember>();
    public DbSet<LoyaltyReward> LoyaltyRewards => Set<LoyaltyReward>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        ConfigureCategory(modelBuilder);
        ConfigureMenuItem(modelBuilder);
        ConfigureRestaurantTable(modelBuilder);
        ConfigureTableSession(modelBuilder);
        ConfigureOrder(modelBuilder);
        ConfigureOrderItem(modelBuilder);
        ConfigureOrderStatusHistory(modelBuilder);
        ConfigurePayment(modelBuilder);
        ConfigurePaymentTransaction(modelBuilder);
        ConfigureChatSession(modelBuilder);
        ConfigureChatMessage(modelBuilder);
        ConfigureKnowledgeEntry(modelBuilder);
        ConfigureUser(modelBuilder);
        ConfigurePromotion(modelBuilder);
        ConfigureLoyaltyMember(modelBuilder);
        ConfigureLoyaltyReward(modelBuilder);

        // Postgres sequence backing the human-facing order code (ORD-1001, 1002, ...).
        // Atomic nextval removes the Count()+1 race that could mint duplicate codes.
        modelBuilder.HasSequence<long>("orders_order_code_seq")
            .StartsAt(1001)
            .IncrementsBy(1);
    }

    // Atomically reserves the next order-code number from the Postgres sequence.
    // Falls back to a simple counter for InMemory provider.
    private static long _inMemoryOrderCodeCounter = 1000;
    public virtual long NextOrderCodeNumber()
    {
        if (Database.IsInMemory())
        {
            return Interlocked.Increment(ref _inMemoryOrderCodeCounter);
        }

        return Database
            .SqlQueryRaw<long>("SELECT nextval('orders_order_code_seq') AS \"Value\"")
            .AsEnumerable()
            .First();
    }

    private static void ConfigureCategory(ModelBuilder modelBuilder)
    {
        var now = CategorySeededAt;
        modelBuilder.Entity<Category>(entity =>
        {
            entity.ToTable("categories");

            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id)
                .HasColumnName("id")
                .HasMaxLength(50);
            entity.Property(e => e.Name)
                .HasColumnName("name")
                .HasMaxLength(200)
                .IsRequired();
            entity.Property(e => e.DisplayOrder)
                .HasColumnName("display_order")
                .IsRequired();
            entity.Property(e => e.IsActive)
                .HasColumnName("is_active")
                .IsRequired();
            entity.Property(e => e.CreatedAt)
                .HasColumnName("created_at")
                .IsRequired();
            entity.Property(e => e.UpdatedAt)
                .HasColumnName("updated_at")
                .IsRequired();

            entity.HasIndex(e => e.IsActive);
            entity.HasIndex(e => e.DisplayOrder);

            entity.HasData(RestaurantMenuSeed.CreateCategories(now).ToArray());
        });
    }

    private static void ConfigureMenuItem(ModelBuilder modelBuilder)
    {
        var now = MenuItemSeededAt;
        modelBuilder.Entity<MenuItem>(entity =>
        {
            entity.ToTable("menu_items");

            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id)
                .HasColumnName("id")
                .HasMaxLength(50);
            entity.Property(e => e.CategoryId)
                .HasColumnName("category_id")
                .HasMaxLength(50)
                .IsRequired();
            entity.Property(e => e.Name)
                .HasColumnName("name")
                .HasMaxLength(300)
                .IsRequired();
            entity.Property(e => e.Description)
                .HasColumnName("description")
                .HasMaxLength(1000);
            entity.Property(e => e.Price)
                .HasColumnName("price")
                .HasPrecision(18, 2)
                .IsRequired();
            entity.Property(e => e.ImageUrl)
                .HasColumnName("image_url")
                .HasMaxLength(500);
            entity.Property(e => e.IsAvailable)
                .HasColumnName("is_available")
                .IsRequired();
            entity.Property(e => e.Tags)
                .HasColumnName("tags")
                .HasColumnType("text[]");
            entity.Property(e => e.CreatedAt)
                .HasColumnName("created_at")
                .IsRequired();
            entity.Property(e => e.UpdatedAt)
                .HasColumnName("updated_at")
                .IsRequired();

            entity.HasOne(e => e.Category)
                .WithMany(c => c.MenuItems)
                .HasForeignKey(e => e.CategoryId)
                .OnDelete(DeleteBehavior.Restrict);

            entity.HasIndex(e => e.CategoryId);
            entity.HasIndex(e => e.IsAvailable);

            entity.HasData(RestaurantMenuSeed.CreateMenuItems(now).ToArray());
        });
    }

    private static void ConfigureRestaurantTable(ModelBuilder modelBuilder)
    {
        var now = TableSeededAt;
        modelBuilder.Entity<RestaurantTable>(entity =>
        {
            entity.ToTable("restaurant_tables");

            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id)
                .HasColumnName("id")
                .HasMaxLength(50);
            entity.Property(e => e.TableCode)
                .HasColumnName("table_code")
                .HasMaxLength(20)
                .IsRequired();
            entity.Property(e => e.DisplayName)
                .HasColumnName("display_name")
                .HasMaxLength(100)
                .IsRequired();
            entity.Property(e => e.IsActive)
                .HasColumnName("is_active")
                .IsRequired();
            entity.Property(e => e.QrToken)
                .HasColumnName("qr_token")
                .HasMaxLength(100);
            entity.Property(e => e.CreatedAt)
                .HasColumnName("created_at")
                .IsRequired();
            entity.Property(e => e.UpdatedAt)
                .HasColumnName("updated_at")
                .IsRequired();

            entity.HasIndex(e => e.TableCode).IsUnique();
            entity.HasIndex(e => e.QrToken).IsUnique();
            entity.HasIndex(e => e.IsActive);

            entity.HasData(RestaurantTableSeed.CreateTables(now).ToArray());
        });
    }

    private static void ConfigureTableSession(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<TableSession>(entity =>
        {
            entity.ToTable("table_sessions");

            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id)
                .HasColumnName("id")
                .HasMaxLength(50);
            entity.Property(e => e.RestaurantTableId)
                .HasColumnName("restaurant_table_id")
                .HasMaxLength(50);
            entity.Property(e => e.TableCode)
                .HasColumnName("table_code")
                .HasMaxLength(20);
            entity.Property(e => e.QrToken)
                .HasColumnName("qr_token")
                .HasMaxLength(100);
            entity.Property(e => e.OrderType)
                .HasColumnName("order_type")
                .HasConversion<string>()
                .HasMaxLength(20)
                .IsRequired();
            entity.Property(e => e.Status)
                .HasColumnName("status")
                .HasConversion<string>()
                .HasMaxLength(20)
                .IsRequired();
            entity.Property(e => e.OpenedAt)
                .HasColumnName("opened_at")
                .IsRequired();
            entity.Property(e => e.ExpiresAt)
                .HasColumnName("expires_at")
                .IsRequired();
            entity.Property(e => e.ClosedAt)
                .HasColumnName("closed_at");
            entity.Property(e => e.CreatedAt)
                .HasColumnName("created_at")
                .IsRequired();
            entity.Property(e => e.UpdatedAt)
                .HasColumnName("updated_at")
                .IsRequired();

            entity.HasOne(e => e.RestaurantTable)
                .WithMany(t => t.TableSessions)
                .HasForeignKey(e => e.RestaurantTableId)
                .OnDelete(DeleteBehavior.SetNull);

            entity.HasIndex(e => e.RestaurantTableId);
            entity.HasIndex(e => e.TableCode);
            entity.HasIndex(e => e.QrToken);
            entity.HasIndex(e => e.Status);
            entity.HasIndex(e => e.ExpiresAt);
        });
    }

    private static void ConfigureOrder(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Order>(entity =>
        {
            entity.ToTable("orders");

            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id)
                .HasColumnName("id")
                .HasMaxLength(50);
            entity.Property(e => e.OrderCode)
                .HasColumnName("order_code")
                .HasMaxLength(50)
                .IsRequired();
            entity.Property(e => e.CustomerAccessToken)
                .HasColumnName("customer_access_token")
                .HasMaxLength(64);
            entity.Property(e => e.OrderType)
                .HasColumnName("order_type")
                .HasConversion<string>()
                .HasMaxLength(20)
                .IsRequired();
            entity.Property(e => e.Status)
                .HasColumnName("status")
                .HasConversion<string>()
                .HasMaxLength(20)
                .IsRequired();
            entity.Property(e => e.RestaurantTableId)
                .HasColumnName("restaurant_table_id")
                .HasMaxLength(50);
            entity.Property(e => e.TableCode)
                .HasColumnName("table_code")
                .HasMaxLength(20);
            entity.Property(e => e.PickupCustomerName)
                .HasColumnName("pickup_customer_name")
                .HasMaxLength(200);
            entity.Property(e => e.PickupCustomerPhoneNumber)
                .HasColumnName("pickup_customer_phone")
                .HasMaxLength(20);
            entity.Property(e => e.PickupRequestedAt)
                .HasColumnName("pickup_requested_at");
            entity.Property(e => e.TableSessionId)
                .HasColumnName("table_session_id")
                .HasMaxLength(50);
            entity.Property(e => e.SubtotalAmount)
                .HasColumnName("subtotal_amount")
                .HasPrecision(18, 2)
                .IsRequired();
            entity.Property(e => e.DiscountAmount)
                .HasColumnName("discount_amount")
                .HasPrecision(18, 2)
                .IsRequired();
            entity.Property(e => e.TotalAmount)
                .HasColumnName("total_amount")
                .HasPrecision(18, 2)
                .IsRequired();
            entity.Property(e => e.PromotionId)
                .HasColumnName("promotion_id")
                .HasMaxLength(50);
            entity.Property(e => e.PromotionCode)
                .HasColumnName("promotion_code")
                .HasMaxLength(50);
            entity.Property(e => e.CustomerPhoneNumber)
                .HasColumnName("customer_phone_number")
                .HasMaxLength(20);
            entity.Property(e => e.CreatedAt)
                .HasColumnName("created_at")
                .IsRequired();
            entity.Property(e => e.UpdatedAt)
                .HasColumnName("updated_at")
                .IsRequired();

            entity.HasOne(e => e.RestaurantTable)
                .WithMany(t => t.Orders)
                .HasForeignKey(e => e.RestaurantTableId)
                .OnDelete(DeleteBehavior.SetNull);

            entity.HasOne(e => e.TableSession)
                .WithMany()
                .HasForeignKey(e => e.TableSessionId)
                .OnDelete(DeleteBehavior.SetNull);

            entity.HasOne(e => e.Promotion)
                .WithMany()
                .HasForeignKey(e => e.PromotionId)
                .OnDelete(DeleteBehavior.SetNull);

            entity.HasIndex(e => e.OrderCode).IsUnique();
            entity.HasIndex(e => e.PromotionId);
            entity.HasIndex(e => e.Status);
            entity.HasIndex(e => e.RestaurantTableId);
            entity.HasIndex(e => e.TableSessionId);
            entity.HasIndex(e => e.CreatedAt);

            // Optimistic concurrency via the Postgres xmin system column, guarding
            // against lost updates when two requests mutate the same order at once.
            // The helper is deprecated but is the only mapping that emits no migration
            // DDL (a manual xmin property generates an invalid AddColumn).
#pragma warning disable CS0618
            entity.UseXminAsConcurrencyToken();
#pragma warning restore CS0618
        });
    }

    private static void ConfigureOrderItem(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<OrderItem>(entity =>
        {
            entity.ToTable("order_items");

            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id)
                .HasColumnName("id")
                .HasMaxLength(50);
            entity.Property(e => e.OrderId)
                .HasColumnName("order_id")
                .HasMaxLength(50)
                .IsRequired();
            entity.Property(e => e.MenuItemId)
                .HasColumnName("menu_item_id")
                .HasMaxLength(50)
                .IsRequired();
            entity.Property(e => e.MenuItemName)
                .HasColumnName("menu_item_name")
                .HasMaxLength(300)
                .IsRequired();
            entity.Property(e => e.UnitPrice)
                .HasColumnName("unit_price")
                .HasPrecision(18, 2)
                .IsRequired();
            entity.Property(e => e.Quantity)
                .HasColumnName("quantity")
                .IsRequired();
            entity.Property(e => e.Note)
                .HasColumnName("note")
                .HasMaxLength(500);
            entity.Property(e => e.Status)
                .HasColumnName("status")
                .HasConversion<string>()
                .HasMaxLength(20)
                .IsRequired();
            entity.Property(e => e.CreatedAt)
                .HasColumnName("created_at")
                .IsRequired();
            entity.Property(e => e.UpdatedAt)
                .HasColumnName("updated_at")
                .IsRequired();

            entity.HasOne(e => e.Order)
                .WithMany(o => o.OrderItems)
                .HasForeignKey(e => e.OrderId)
                .OnDelete(DeleteBehavior.Cascade);

            entity.HasOne(e => e.MenuItem)
                .WithMany()
                .HasForeignKey(e => e.MenuItemId)
                .OnDelete(DeleteBehavior.SetNull);

            entity.HasIndex(e => e.OrderId);
            entity.HasIndex(e => e.MenuItemId);
        });
    }

    private static void ConfigureOrderStatusHistory(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<OrderStatusHistory>(entity =>
        {
            entity.ToTable("order_status_history");

            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id)
                .HasColumnName("id")
                .HasMaxLength(50);
            entity.Property(e => e.OrderId)
                .HasColumnName("order_id")
                .HasMaxLength(50)
                .IsRequired();
            entity.Property(e => e.FromStatus)
                .HasColumnName("from_status")
                .HasConversion<string>()
                .HasMaxLength(20);
            entity.Property(e => e.ToStatus)
                .HasColumnName("to_status")
                .HasConversion<string>()
                .HasMaxLength(20)
                .IsRequired();
            entity.Property(e => e.Source)
                .HasColumnName("source")
                .HasConversion<string>()
                .HasMaxLength(20)
                .IsRequired();
            entity.Property(e => e.ChangedByUserId)
                .HasColumnName("changed_by_user_id")
                .HasMaxLength(50);
            entity.Property(e => e.ChangedByRole)
                .HasColumnName("changed_by_role")
                .HasMaxLength(20);
            entity.Property(e => e.Note)
                .HasColumnName("note")
                .HasMaxLength(500);
            entity.Property(e => e.CreatedAt)
                .HasColumnName("created_at")
                .IsRequired();

            entity.HasOne(e => e.Order)
                .WithMany(o => o.StatusHistory)
                .HasForeignKey(e => e.OrderId)
                .OnDelete(DeleteBehavior.Cascade);

            entity.HasIndex(e => e.OrderId);
            entity.HasIndex(e => e.CreatedAt);
        });
    }

    private static void ConfigurePayment(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Payment>(entity =>
        {
            entity.ToTable("payments");

            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id)
                .HasColumnName("id")
                .HasMaxLength(50);
            entity.Property(e => e.OrderId)
                .HasColumnName("order_id")
                .HasMaxLength(50)
                .IsRequired();
            entity.Property(e => e.Method)
                .HasColumnName("method")
                .HasConversion<string>()
                .HasMaxLength(20)
                .IsRequired();
            entity.Property(e => e.Status)
                .HasColumnName("status")
                .HasConversion<string>()
                .HasMaxLength(20)
                .IsRequired();
            entity.Property(e => e.Amount)
                .HasColumnName("amount")
                .HasPrecision(18, 2)
                .IsRequired();
            entity.Property(e => e.ProviderTransactionId)
                .HasColumnName("provider_transaction_id")
                .HasMaxLength(200);
            entity.Property(e => e.CreatedAt)
                .HasColumnName("created_at")
                .IsRequired();
            entity.Property(e => e.PaidAt)
                .HasColumnName("paid_at");
            entity.Property(e => e.UpdatedAt)
                .HasColumnName("updated_at")
                .IsRequired();

            entity.HasOne(e => e.Order)
                .WithOne(o => o.Payment)
                .HasForeignKey<Payment>(e => e.OrderId)
                .OnDelete(DeleteBehavior.Cascade);

            entity.HasIndex(e => e.OrderId).IsUnique();
            entity.HasIndex(e => e.Status);

            // Optimistic concurrency via xmin: guard against two staff confirming or
            // failing the same payment at once. Deprecated helper, but emits no DDL.
#pragma warning disable CS0618
            entity.UseXminAsConcurrencyToken();
#pragma warning restore CS0618
        });
    }

    private static void ConfigurePaymentTransaction(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<PaymentTransaction>(entity =>
        {
            entity.ToTable("payment_transactions");

            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id)
                .HasColumnName("id")
                .HasMaxLength(50);
            entity.Property(e => e.PaymentId)
                .HasColumnName("payment_id")
                .HasMaxLength(50)
                .IsRequired();
            entity.Property(e => e.Method)
                .HasColumnName("method")
                .HasConversion<string>()
                .HasMaxLength(20)
                .IsRequired();
            entity.Property(e => e.Status)
                .HasColumnName("status")
                .HasConversion<string>()
                .HasMaxLength(20)
                .IsRequired();
            entity.Property(e => e.Amount)
                .HasColumnName("amount")
                .HasPrecision(18, 2)
                .IsRequired();
            entity.Property(e => e.Provider)
                .HasColumnName("provider")
                .HasMaxLength(50)
                .IsRequired();
            entity.Property(e => e.ProviderTransactionId)
                .HasColumnName("provider_transaction_id")
                .HasMaxLength(200);
            entity.Property(e => e.Note)
                .HasColumnName("note")
                .HasMaxLength(500);
            entity.Property(e => e.CreatedAt)
                .HasColumnName("created_at")
                .IsRequired();

            entity.HasOne(e => e.Payment)
                .WithMany(p => p.Transactions)
                .HasForeignKey(e => e.PaymentId)
                .OnDelete(DeleteBehavior.Cascade);

            entity.HasIndex(e => e.PaymentId);
            entity.HasIndex(e => e.Status);
            entity.HasIndex(e => e.ProviderTransactionId);
        });
    }

    private static void ConfigureChatSession(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<ChatSession>(entity =>
        {
            entity.ToTable("chat_sessions");

            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id)
                .HasColumnName("id")
                .HasMaxLength(50);
            entity.Property(e => e.RestaurantTableId)
                .HasColumnName("restaurant_table_id")
                .HasMaxLength(50);
            entity.Property(e => e.TableCode)
                .HasColumnName("table_code")
                .HasMaxLength(20);
            entity.Property(e => e.TableSessionId)
                .HasColumnName("table_session_id")
                .HasMaxLength(50);
            entity.Property(e => e.OrderId)
                .HasColumnName("order_id")
                .HasMaxLength(50);
            entity.Property(e => e.IsClosed)
                .HasColumnName("is_closed")
                .IsRequired();
            entity.Property(e => e.CreatedAt)
                .HasColumnName("created_at")
                .IsRequired();
            entity.Property(e => e.UpdatedAt)
                .HasColumnName("updated_at")
                .IsRequired();

            entity.HasOne(e => e.RestaurantTable)
                .WithMany()
                .HasForeignKey(e => e.RestaurantTableId)
                .OnDelete(DeleteBehavior.SetNull);

            entity.HasOne(e => e.Order)
                .WithMany()
                .HasForeignKey(e => e.OrderId)
                .OnDelete(DeleteBehavior.SetNull);

            entity.HasIndex(e => e.RestaurantTableId);
            entity.HasIndex(e => e.OrderId);
            entity.HasIndex(e => e.IsClosed);
            entity.HasIndex(e => e.TableSessionId);
        });
    }

    private static void ConfigureChatMessage(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<ChatMessage>(entity =>
        {
            entity.ToTable("chat_messages");

            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id)
                .HasColumnName("id")
                .HasMaxLength(50);
            entity.Property(e => e.ChatSessionId)
                .HasColumnName("chat_session_id")
                .HasMaxLength(50)
                .IsRequired();
            entity.Property(e => e.Role)
                .HasColumnName("role")
                .HasMaxLength(20)
                .IsRequired();
            entity.Property(e => e.Content)
                .HasColumnName("content")
                .IsRequired();
            entity.Property(e => e.SuggestedCartActionsJson)
                .HasColumnName("suggested_cart_actions_json")
                .HasColumnType("jsonb");
            entity.Property(e => e.CreatedAt)
                .HasColumnName("created_at")
                .IsRequired();

            entity.HasOne(e => e.ChatSession)
                .WithMany(s => s.Messages)
                .HasForeignKey(e => e.ChatSessionId)
                .OnDelete(DeleteBehavior.Cascade);

            entity.HasIndex(e => e.ChatSessionId);
        });
    }

    private static void ConfigureKnowledgeEntry(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<KnowledgeEntry>(entity =>
        {
            entity.ToTable("knowledge_entries");

            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id)
                .HasColumnName("id")
                .HasMaxLength(50);
            entity.Property(e => e.Title)
                .HasColumnName("title")
                .HasMaxLength(300)
                .IsRequired();
            entity.Property(e => e.Content)
                .HasColumnName("content")
                .IsRequired();
            entity.Property(e => e.SourceType)
                .HasColumnName("source_type")
                .HasMaxLength(50)
                .IsRequired();
            entity.Property(e => e.MenuItemId)
                .HasColumnName("menu_item_id")
                .HasMaxLength(50);
            entity.Property(e => e.Tags)
                .HasColumnName("tags")
                .HasColumnType("text[]");
            entity.Property(e => e.Embedding)
                .HasColumnName("embedding")
                .HasColumnType("jsonb")
                .HasConversion(
                    v => JsonSerializer.Serialize(v, (JsonSerializerOptions?)null),
                    v => JsonSerializer.Deserialize<float[]>(v, (JsonSerializerOptions?)null) ?? Array.Empty<float>());
            entity.Property(e => e.IsActive)
                .HasColumnName("is_active")
                .IsRequired();
            entity.Property(e => e.CreatedAt)
                .HasColumnName("created_at")
                .IsRequired();
            entity.Property(e => e.UpdatedAt)
                .HasColumnName("updated_at")
                .IsRequired();

            entity.HasOne(e => e.MenuItem)
                .WithMany()
                .HasForeignKey(e => e.MenuItemId)
                .OnDelete(DeleteBehavior.SetNull);

            entity.HasIndex(e => e.IsActive);
            entity.HasIndex(e => e.MenuItemId);
        });
    }

    private static void ConfigureUser(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<User>(entity =>
        {
            entity.ToTable("users");

            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id)
                .HasColumnName("id")
                .HasMaxLength(50);
            entity.Property(e => e.FullName)
                .HasColumnName("full_name")
                .HasMaxLength(200)
                .IsRequired();
            entity.Property(e => e.Email)
                .HasColumnName("email")
                .HasMaxLength(255)
                .IsRequired();
            entity.Property(e => e.PasswordHash)
                .HasColumnName("password_hash")
                .HasMaxLength(200)
                .IsRequired();
            entity.Property(e => e.Role)
                .HasColumnName("role")
                .HasMaxLength(20)
                .IsRequired();
            entity.Property(e => e.CreatedAt)
                .HasColumnName("created_at")
                .IsRequired();
            entity.Property(e => e.UpdatedAt)
                .HasColumnName("updated_at")
                .IsRequired();
            entity.Property(e => e.FailedLoginCount)
                .HasColumnName("failed_login_count")
                .HasDefaultValue(0);
            entity.Property(e => e.LockoutEndAt)
                .HasColumnName("lockout_end_at");

            entity.HasIndex(e => e.Email).IsUnique();
        });
    }

    private static void ConfigurePromotion(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Promotion>(entity =>
        {
            entity.ToTable("promotions");

            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id)
                .HasColumnName("id")
                .HasMaxLength(50);
            entity.Property(e => e.Code)
                .HasColumnName("code")
                .HasMaxLength(50)
                .IsRequired();
            entity.Property(e => e.Name)
                .HasColumnName("name")
                .HasMaxLength(200)
                .IsRequired();
            entity.Property(e => e.Description)
                .HasColumnName("description")
                .HasMaxLength(1000);
            entity.Property(e => e.Type)
                .HasColumnName("type")
                .HasConversion<string>()
                .HasMaxLength(20)
                .IsRequired();
            entity.Property(e => e.DiscountValue)
                .HasColumnName("discount_value")
                .HasPrecision(18, 2)
                .IsRequired();
            entity.Property(e => e.MinOrderAmount)
                .HasColumnName("min_order_amount")
                .HasPrecision(18, 2);
            entity.Property(e => e.MaxDiscountAmount)
                .HasColumnName("max_discount_amount")
                .HasPrecision(18, 2);
            entity.Property(e => e.IsFlashSale)
                .HasColumnName("is_flash_sale")
                .IsRequired();
            entity.Property(e => e.StartsAt)
                .HasColumnName("starts_at");
            entity.Property(e => e.EndsAt)
                .HasColumnName("ends_at");
            entity.Property(e => e.IsActive)
                .HasColumnName("is_active")
                .IsRequired();
            entity.Property(e => e.CreatedAt)
                .HasColumnName("created_at")
                .IsRequired();
            entity.Property(e => e.UpdatedAt)
                .HasColumnName("updated_at")
                .IsRequired();

            entity.HasIndex(e => e.Code).IsUnique();
            entity.HasIndex(e => e.IsActive);
        });
    }

    private static void ConfigureLoyaltyMember(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<LoyaltyMember>(entity =>
        {
            entity.ToTable("loyalty_members");

            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id)
                .HasColumnName("id")
                .HasMaxLength(50);
            entity.Property(e => e.PhoneNumber)
                .HasColumnName("phone_number")
                .HasMaxLength(20)
                .IsRequired();
            entity.Property(e => e.FullName)
                .HasColumnName("full_name")
                .HasMaxLength(200);
            entity.Property(e => e.Points)
                .HasColumnName("points")
                .IsRequired();
            entity.Property(e => e.LifetimeSpend)
                .HasColumnName("lifetime_spend")
                .HasPrecision(18, 2)
                .IsRequired();
            entity.Property(e => e.CreatedAt)
                .HasColumnName("created_at")
                .IsRequired();
            entity.Property(e => e.UpdatedAt)
                .HasColumnName("updated_at")
                .IsRequired();

            entity.HasIndex(e => e.PhoneNumber).IsUnique();
        });
    }

    private static void ConfigureLoyaltyReward(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<LoyaltyReward>(entity =>
        {
            entity.ToTable("loyalty_rewards");

            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id)
                .HasColumnName("id")
                .HasMaxLength(50);
            entity.Property(e => e.Name)
                .HasColumnName("name")
                .HasMaxLength(200)
                .IsRequired();
            entity.Property(e => e.Description)
                .HasColumnName("description")
                .HasMaxLength(1000);
            entity.Property(e => e.PointsRequired)
                .HasColumnName("points_required")
                .IsRequired();
            entity.Property(e => e.IsActive)
                .HasColumnName("is_active")
                .IsRequired();
            entity.Property(e => e.CreatedAt)
                .HasColumnName("created_at")
                .IsRequired();
            entity.Property(e => e.UpdatedAt)
                .HasColumnName("updated_at")
                .IsRequired();

            entity.HasIndex(e => e.IsActive);
            entity.HasIndex(e => e.PointsRequired);
        });
    }
}
