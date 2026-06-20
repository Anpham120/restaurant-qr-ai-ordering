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
    public DbSet<Payment> Payments => Set<Payment>();
    public DbSet<PaymentTransaction> PaymentTransactions => Set<PaymentTransaction>();
    public DbSet<ChatSession> ChatSessions => Set<ChatSession>();
    public DbSet<ChatMessage> ChatMessages => Set<ChatMessage>();
    public DbSet<KnowledgeEntry> KnowledgeEntries => Set<KnowledgeEntry>();
    public DbSet<User> Users => Set<User>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        ConfigureCategory(modelBuilder);
        ConfigureMenuItem(modelBuilder);
        ConfigureRestaurantTable(modelBuilder);
        ConfigureTableSession(modelBuilder);
        ConfigureOrder(modelBuilder);
        ConfigureOrderItem(modelBuilder);
        ConfigurePayment(modelBuilder);
        ConfigurePaymentTransaction(modelBuilder);
        ConfigureChatSession(modelBuilder);
        ConfigureChatMessage(modelBuilder);
        ConfigureKnowledgeEntry(modelBuilder);
        ConfigureUser(modelBuilder);

        // Postgres sequence backing the human-facing order code (ORD-1001, 1002, ...).
        // Atomic nextval removes the Count()+1 race that could mint duplicate codes.
        modelBuilder.HasSequence<long>("orders_order_code_seq")
            .StartsAt(1001)
            .IncrementsBy(1);
    }

    // Atomically reserves the next order-code number from the Postgres sequence.
    // Overridden by the test context (EF InMemory can't run raw SQL).
    public virtual long NextOrderCodeNumber()
    {
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

            entity.HasData(
                new Category { Id = "cat_appetizer", Name = "Khai vi", DisplayOrder = 10, IsActive = true, CreatedAt = now, UpdatedAt = now },
                new Category { Id = "cat_main", Name = "Mon chinh", DisplayOrder = 20, IsActive = true, CreatedAt = now, UpdatedAt = now },
                new Category { Id = "cat_noodle", Name = "Pho va bun", DisplayOrder = 30, IsActive = true, CreatedAt = now, UpdatedAt = now },
                new Category { Id = "cat_seafood", Name = "Hai san", DisplayOrder = 40, IsActive = true, CreatedAt = now, UpdatedAt = now },
                new Category { Id = "cat_drink", Name = "Do uong", DisplayOrder = 50, IsActive = true, CreatedAt = now, UpdatedAt = now },
                new Category { Id = "cat_dessert", Name = "Trang mieng", DisplayOrder = 60, IsActive = true, CreatedAt = now, UpdatedAt = now }
            );
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

            entity.HasData(
                new MenuItem { Id = "m_001", CategoryId = "cat_main", Name = "Com ga xoi mo", Description = "Ga chien gion, com thom, dua chua.", Price = 45000, ImageUrl = "https://example.com/images/com-ga-xoi-mo.jpg", IsAvailable = true, Tags = new List<string> { "pho bien", "mon chinh", "signature" }, CreatedAt = now, UpdatedAt = now },
                new MenuItem { Id = "m_002", CategoryId = "cat_main", Name = "Com suon nuong", Description = "Suon uop mat ong nuong than, an kem rau chua.", Price = 52000, ImageUrl = "https://example.com/images/com-suon-nuong.jpg", IsAvailable = true, Tags = new List<string> { "pho bien", "nuong" }, CreatedAt = now, UpdatedAt = now },
                new MenuItem { Id = "m_003", CategoryId = "cat_noodle", Name = "Pho bo tai", Description = "Pho bo nuoc dung trong, bo tai mem, rau thom.", Price = 55000, ImageUrl = "https://example.com/images/pho-bo-tai.jpg", IsAvailable = true, Tags = new List<string> { "nong", "pho", "bo" }, CreatedAt = now, UpdatedAt = now },
                new MenuItem { Id = "m_004", CategoryId = "cat_noodle", Name = "Bun bo Hue", Description = "Nuoc dung dam vi sa te, bo, cha cua va rau song.", Price = 60000, ImageUrl = "https://example.com/images/bun-bo-hue.jpg", IsAvailable = false, Tags = new List<string> { "cay", "het hang", "unavailable-demo" }, CreatedAt = now, UpdatedAt = now },
                new MenuItem { Id = "m_005", CategoryId = "cat_appetizer", Name = "Goi cuon tom thit", Description = "Goi cuon tuoi kem nuoc cham dau phong.", Price = 39000, ImageUrl = "https://example.com/images/goi-cuon.jpg", IsAvailable = true, Tags = new List<string> { "fresh", "light" }, CreatedAt = now, UpdatedAt = now },
                new MenuItem { Id = "m_006", CategoryId = "cat_appetizer", Name = "Cha gio hai san", Description = "Cha gio gion nhan hai san, sot mayo cay.", Price = 42000, ImageUrl = "https://example.com/images/cha-gio-hai-san.jpg", IsAvailable = true, Tags = new List<string> { "chien gion", "seafood" }, CreatedAt = now, UpdatedAt = now },
                new MenuItem { Id = "m_007", CategoryId = "cat_seafood", Name = "Tom rang muoi", Description = "Tom tuoi rang muoi ot, an kem rau thom.", Price = 185000, ImageUrl = "https://example.com/images/tom-rang-muoi.jpg", IsAvailable = true, Tags = new List<string> { "seafood", "share" }, CreatedAt = now, UpdatedAt = now },
                new MenuItem { Id = "m_008", CategoryId = "cat_seafood", Name = "Lau Thai hai san", Description = "Lau Thai chua cay voi tom, muc, ca va rau tuoi.", Price = 345000, ImageUrl = "https://example.com/images/lau-thai-hai-san.jpg", IsAvailable = true, Tags = new List<string> { "spicy", "seafood", "share" }, CreatedAt = now, UpdatedAt = now },
                new MenuItem { Id = "m_009", CategoryId = "cat_drink", Name = "Tra dao cam sa", Description = "Tra dao mat lanh voi cam vang va sa tuoi.", Price = 55000, ImageUrl = "https://example.com/images/tra-dao-cam-sa.jpg", IsAvailable = true, Tags = new List<string> { "drink", "fresh" }, CreatedAt = now, UpdatedAt = now },
                new MenuItem { Id = "m_010", CategoryId = "cat_drink", Name = "Ca phe sua da", Description = "Ca phe rang xay pha phin, sua dac va da vien.", Price = 45000, ImageUrl = "https://example.com/images/ca-phe-sua-da.jpg", IsAvailable = false, Tags = new List<string> { "drink", "coffee", "unavailable-demo" }, CreatedAt = now, UpdatedAt = now },
                new MenuItem { Id = "m_011", CategoryId = "cat_dessert", Name = "Che khuc bach", Description = "Khuc bach beo nhe, vai, hanh nhan va siro duong phen.", Price = 55000, ImageUrl = "https://example.com/images/che-khuc-bach.jpg", IsAvailable = true, Tags = new List<string> { "sweet", "cool" }, CreatedAt = now, UpdatedAt = now },
                new MenuItem { Id = "m_012", CategoryId = "cat_dessert", Name = "Banh flan caramel", Description = "Banh flan min, caramel thom, dung lanh.", Price = 35000, ImageUrl = "https://example.com/images/banh-flan.jpg", IsAvailable = true, Tags = new List<string> { "sweet", "classic" }, CreatedAt = now, UpdatedAt = now }
            );
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

            entity.HasData(
                new RestaurantTable { Id = "tbl_01", TableCode = "T01", DisplayName = "Ban 01", IsActive = true, QrToken = "cmc-table-t01-qr", CreatedAt = now, UpdatedAt = now },
                new RestaurantTable { Id = "tbl_02", TableCode = "T02", DisplayName = "Ban 02", IsActive = true, QrToken = "cmc-table-t02-qr", CreatedAt = now, UpdatedAt = now },
                new RestaurantTable { Id = "tbl_03", TableCode = "T03", DisplayName = "Ban 03", IsActive = true, QrToken = "cmc-table-t03-qr", CreatedAt = now, UpdatedAt = now },
                new RestaurantTable { Id = "tbl_04", TableCode = "T04", DisplayName = "Ban 04", IsActive = true, QrToken = "cmc-table-t04-qr", CreatedAt = now, UpdatedAt = now },
                new RestaurantTable { Id = "tbl_05", TableCode = "T05", DisplayName = "Ban 05", IsActive = true, QrToken = "cmc-table-t05-qr", CreatedAt = now, UpdatedAt = now },
                new RestaurantTable { Id = "tbl_06", TableCode = "T06", DisplayName = "Ban 06", IsActive = true, QrToken = "cmc-table-t06-qr", CreatedAt = now, UpdatedAt = now },
                new RestaurantTable { Id = "tbl_07", TableCode = "T07", DisplayName = "Ban 07", IsActive = true, QrToken = "cmc-table-t07-qr", CreatedAt = now, UpdatedAt = now },
                new RestaurantTable { Id = "tbl_08", TableCode = "T08", DisplayName = "Ban 08", IsActive = true, QrToken = "cmc-table-t08-qr", CreatedAt = now, UpdatedAt = now }
            );
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
            entity.Property(e => e.DeliveryRecipientName)
                .HasColumnName("delivery_recipient_name")
                .HasMaxLength(200);
            entity.Property(e => e.DeliveryPhoneNumber)
                .HasColumnName("delivery_phone_number")
                .HasMaxLength(20);
            entity.Property(e => e.DeliveryAddress)
                .HasColumnName("delivery_address")
                .HasMaxLength(500);
            entity.Property(e => e.DeliveryNote)
                .HasColumnName("delivery_note")
                .HasMaxLength(500);
            entity.Property(e => e.SubtotalAmount)
                .HasColumnName("subtotal_amount")
                .HasPrecision(18, 2)
                .IsRequired();
            entity.Property(e => e.TotalAmount)
                .HasColumnName("total_amount")
                .HasPrecision(18, 2)
                .IsRequired();
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

            entity.HasIndex(e => e.OrderCode).IsUnique();
            entity.HasIndex(e => e.Status);
            entity.HasIndex(e => e.RestaurantTableId);
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

            entity.HasIndex(e => e.Email).IsUnique();
        });
    }
}
