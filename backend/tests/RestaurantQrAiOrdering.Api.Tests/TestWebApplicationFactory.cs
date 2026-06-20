using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Api.Realtime;
using RestaurantQrAiOrdering.Api.Users;
using RestaurantQrAiOrdering.Entities;

namespace RestaurantQrAiOrdering.Api.Tests;

public class TestWebApplicationFactory : WebApplicationFactory<Program>
{
    private readonly RecordingOrderRealtimeNotifier _realtimeNotifier = new();
    private readonly string _dbName = $"TestDb_{Guid.NewGuid():N}";
    private bool _seeded;

    public TestWebApplicationFactory()
    {
        _seeded = false;
    }

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.ConfigureServices(services =>
        {
            var removeTypes = new[]
            {
                typeof(DbContextOptions<RestaurantDbContext>),
                typeof(DbContextOptions),
                typeof(RestaurantDbContext),
            };

            foreach (var type in removeTypes)
            {
                var descriptors = services.Where(d => d.ServiceType == type).ToList();
                foreach (var d in descriptors)
                {
                    services.Remove(d);
                }
            }

            services.AddSingleton<DbContextOptions<RestaurantDbContext>>(
                new DbContextOptionsBuilder<RestaurantDbContext>()
                    .UseInMemoryDatabase(_dbName)
                    .Options);

            services.AddScoped<RestaurantDbContext>(sp =>
            {
                var options = sp.GetRequiredService<DbContextOptions<RestaurantDbContext>>();
                return new TestRestaurantDbContext(options);
            });

            var realtimeDescriptors = services.Where(
                d => d.ServiceType == typeof(IOrderRealtimeNotifier)).ToList();
            foreach (var d in realtimeDescriptors)
            {
                services.Remove(d);
            }
            services.AddSingleton<IOrderRealtimeNotifier>(_realtimeNotifier);
        });
    }

    public RecordingOrderRealtimeNotifier GetRealtimeNotifier() => _realtimeNotifier;

    public async Task SeedDatabaseAsync()
    {
        if (_seeded) return;
        _seeded = true;

        using var scope = Services.CreateScope();
        var db = (TestRestaurantDbContext)scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
        await db.SeedDataAsync();
    }
}

internal sealed class TestRestaurantDbContext : RestaurantDbContext
{
    public TestRestaurantDbContext(DbContextOptions<RestaurantDbContext> options)
        : base(options)
    {
    }

    // EF InMemory ignores xmin, so tests toggle this to exercise the
    // DbUpdateConcurrencyException handling in the store/endpoints.
    public bool ThrowConcurrencyOnSave { get; set; }

    // EF InMemory can't run the Postgres nextval sequence; derive a sequential
    // order-code number from the shared in-memory store instead.
    public override long NextOrderCodeNumber()
    {
        return Orders.Count() + 1001;
    }

    public override int SaveChanges()
    {
        if (ThrowConcurrencyOnSave)
        {
            throw new DbUpdateConcurrencyException("Simulated concurrent update.");
        }

        return base.SaveChanges();
    }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        ConfigureCategoryForTest(modelBuilder);
        ConfigureMenuItemForTest(modelBuilder);
        ConfigureRestaurantTableForTest(modelBuilder);
        ConfigureTableSessionForTest(modelBuilder);
        ConfigureOrderForTest(modelBuilder);
        ConfigureOrderItemForTest(modelBuilder);
        ConfigurePaymentForTest(modelBuilder);
        ConfigurePaymentTransactionForTest(modelBuilder);
        ConfigureChatSessionForTest(modelBuilder);
        ConfigureChatMessageForTest(modelBuilder);
        ConfigureKnowledgeEntryForTest(modelBuilder);
        ConfigureUserForTest(modelBuilder);
    }

    private static void ConfigureCategoryForTest(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Category>(entity =>
        {
            entity.ToTable("categories");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id).HasColumnName("id").HasMaxLength(50);
            entity.Property(e => e.Name).HasColumnName("name").HasMaxLength(200).IsRequired();
            entity.Property(e => e.DisplayOrder).HasColumnName("display_order").IsRequired();
            entity.Property(e => e.IsActive).HasColumnName("is_active").IsRequired();
            entity.Property(e => e.CreatedAt).HasColumnName("created_at").IsRequired();
            entity.Property(e => e.UpdatedAt).HasColumnName("updated_at").IsRequired();
            entity.HasIndex(e => e.IsActive);
            entity.HasIndex(e => e.DisplayOrder);
        });
    }

    private static void ConfigureMenuItemForTest(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<MenuItem>(entity =>
        {
            entity.ToTable("menu_items");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id).HasColumnName("id").HasMaxLength(50);
            entity.Property(e => e.CategoryId).HasColumnName("category_id").HasMaxLength(50).IsRequired();
            entity.Property(e => e.Name).HasColumnName("name").HasMaxLength(300).IsRequired();
            entity.Property(e => e.Description).HasColumnName("description").HasMaxLength(1000);
            entity.Property(e => e.Price).HasColumnName("price").HasPrecision(18, 2).IsRequired();
            entity.Property(e => e.ImageUrl).HasColumnName("image_url").HasMaxLength(500);
            entity.Property(e => e.IsAvailable).HasColumnName("is_available").IsRequired();
            entity.Property(e => e.Tags).HasColumnName("tags").HasConversion(
                v => string.Join(",", v),
                v => string.IsNullOrEmpty(v) ? new List<string>() : v.Split(',', StringSplitOptions.RemoveEmptyEntries).ToList());
            entity.Property(e => e.CreatedAt).HasColumnName("created_at").IsRequired();
            entity.Property(e => e.UpdatedAt).HasColumnName("updated_at").IsRequired();
            entity.HasOne(e => e.Category).WithMany(c => c.MenuItems).HasForeignKey(e => e.CategoryId).OnDelete(DeleteBehavior.Restrict);
            entity.HasIndex(e => e.CategoryId);
            entity.HasIndex(e => e.IsAvailable);
        });
    }

    private static void ConfigureRestaurantTableForTest(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<RestaurantTable>(entity =>
        {
            entity.ToTable("restaurant_tables");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id).HasColumnName("id").HasMaxLength(50);
            entity.Property(e => e.TableCode).HasColumnName("table_code").HasMaxLength(20).IsRequired();
            entity.Property(e => e.DisplayName).HasColumnName("display_name").HasMaxLength(100).IsRequired();
            entity.Property(e => e.IsActive).HasColumnName("is_active").IsRequired();
            entity.Property(e => e.QrToken).HasColumnName("qr_token").HasMaxLength(100);
            entity.Property(e => e.CreatedAt).HasColumnName("created_at").IsRequired();
            entity.Property(e => e.UpdatedAt).HasColumnName("updated_at").IsRequired();
            entity.HasIndex(e => e.TableCode).IsUnique();
            entity.HasIndex(e => e.QrToken).IsUnique();
            entity.HasIndex(e => e.IsActive);
        });
    }

    private static void ConfigureTableSessionForTest(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<TableSession>(entity =>
        {
            entity.ToTable("table_sessions");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id).HasColumnName("id").HasMaxLength(50);
            entity.Property(e => e.RestaurantTableId).HasColumnName("restaurant_table_id").HasMaxLength(50);
            entity.Property(e => e.TableCode).HasColumnName("table_code").HasMaxLength(20);
            entity.Property(e => e.QrToken).HasColumnName("qr_token").HasMaxLength(100);
            entity.Property(e => e.OrderType).HasColumnName("order_type").HasConversion<string>().HasMaxLength(20).IsRequired();
            entity.Property(e => e.Status).HasColumnName("status").HasConversion<string>().HasMaxLength(20).IsRequired();
            entity.Property(e => e.OpenedAt).HasColumnName("opened_at").IsRequired();
            entity.Property(e => e.ExpiresAt).HasColumnName("expires_at").IsRequired();
            entity.Property(e => e.ClosedAt).HasColumnName("closed_at");
            entity.Property(e => e.CreatedAt).HasColumnName("created_at").IsRequired();
            entity.Property(e => e.UpdatedAt).HasColumnName("updated_at").IsRequired();
            entity.HasOne(e => e.RestaurantTable).WithMany(t => t.TableSessions).HasForeignKey(e => e.RestaurantTableId).OnDelete(DeleteBehavior.SetNull);
            entity.HasIndex(e => e.RestaurantTableId);
            entity.HasIndex(e => e.TableCode);
            entity.HasIndex(e => e.QrToken);
            entity.HasIndex(e => e.Status);
            entity.HasIndex(e => e.ExpiresAt);
        });
    }

    private static void ConfigureOrderForTest(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Order>(entity =>
        {
            entity.ToTable("orders");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id).HasColumnName("id").HasMaxLength(50);
            entity.Property(e => e.OrderCode).HasColumnName("order_code").HasMaxLength(50).IsRequired();
            entity.Property(e => e.OrderType).HasColumnName("order_type").HasConversion<string>().HasMaxLength(20).IsRequired();
            entity.Property(e => e.Status).HasColumnName("status").HasConversion<string>().HasMaxLength(20).IsRequired();
            entity.Property(e => e.RestaurantTableId).HasColumnName("restaurant_table_id").HasMaxLength(50);
            entity.Property(e => e.TableCode).HasColumnName("table_code").HasMaxLength(20);
            entity.Property(e => e.PickupCustomerName).HasColumnName("pickup_customer_name").HasMaxLength(200);
            entity.Property(e => e.PickupCustomerPhoneNumber).HasColumnName("pickup_customer_phone").HasMaxLength(20);
            entity.Property(e => e.PickupRequestedAt).HasColumnName("pickup_requested_at");
            entity.Property(e => e.TableSessionId).HasColumnName("table_session_id").HasMaxLength(50);
            entity.Property(e => e.SubtotalAmount).HasColumnName("subtotal_amount").HasPrecision(18, 2).IsRequired();
            entity.Property(e => e.TotalAmount).HasColumnName("total_amount").HasPrecision(18, 2).IsRequired();
            entity.Property(e => e.CreatedAt).HasColumnName("created_at").IsRequired();
            entity.Property(e => e.UpdatedAt).HasColumnName("updated_at").IsRequired();
            entity.HasOne(e => e.RestaurantTable).WithMany(t => t.Orders).HasForeignKey(e => e.RestaurantTableId).OnDelete(DeleteBehavior.SetNull);
            entity.HasIndex(e => e.OrderCode).IsUnique();
            entity.HasIndex(e => e.Status);
            entity.HasIndex(e => e.RestaurantTableId);
            entity.HasIndex(e => e.CreatedAt);
        });
    }

    private static void ConfigureOrderItemForTest(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<OrderItem>(entity =>
        {
            entity.ToTable("order_items");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id).HasColumnName("id").HasMaxLength(50);
            entity.Property(e => e.OrderId).HasColumnName("order_id").HasMaxLength(50).IsRequired();
            entity.Property(e => e.MenuItemId).HasColumnName("menu_item_id").HasMaxLength(50).IsRequired();
            entity.Property(e => e.MenuItemName).HasColumnName("menu_item_name").HasMaxLength(300).IsRequired();
            entity.Property(e => e.UnitPrice).HasColumnName("unit_price").HasPrecision(18, 2).IsRequired();
            entity.Property(e => e.Quantity).HasColumnName("quantity").IsRequired();
            entity.Property(e => e.Note).HasColumnName("note").HasMaxLength(500);
            entity.Property(e => e.Status).HasColumnName("status").HasConversion<string>().HasMaxLength(20).IsRequired();
            entity.Property(e => e.CreatedAt).HasColumnName("created_at").IsRequired();
            entity.Property(e => e.UpdatedAt).HasColumnName("updated_at").IsRequired();
            entity.HasOne(e => e.Order).WithMany(o => o.OrderItems).HasForeignKey(e => e.OrderId).OnDelete(DeleteBehavior.Cascade);
            entity.HasOne(e => e.MenuItem).WithMany().HasForeignKey(e => e.MenuItemId).OnDelete(DeleteBehavior.SetNull);
            entity.HasIndex(e => e.OrderId);
            entity.HasIndex(e => e.MenuItemId);
        });
    }

    private static void ConfigurePaymentForTest(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Payment>(entity =>
        {
            entity.ToTable("payments");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id).HasColumnName("id").HasMaxLength(50);
            entity.Property(e => e.OrderId).HasColumnName("order_id").HasMaxLength(50).IsRequired();
            entity.Property(e => e.Method).HasColumnName("method").HasConversion<string>().HasMaxLength(20).IsRequired();
            entity.Property(e => e.Status).HasColumnName("status").HasConversion<string>().HasMaxLength(20).IsRequired();
            entity.Property(e => e.Amount).HasColumnName("amount").HasPrecision(18, 2).IsRequired();
            entity.Property(e => e.ProviderTransactionId).HasColumnName("provider_transaction_id").HasMaxLength(200);
            entity.Property(e => e.CreatedAt).HasColumnName("created_at").IsRequired();
            entity.Property(e => e.PaidAt).HasColumnName("paid_at");
            entity.Property(e => e.UpdatedAt).HasColumnName("updated_at").IsRequired();
            entity.HasOne(e => e.Order).WithOne(o => o.Payment).HasForeignKey<Payment>(e => e.OrderId).OnDelete(DeleteBehavior.Cascade);
            entity.HasIndex(e => e.OrderId).IsUnique();
            entity.HasIndex(e => e.Status);
        });
    }

    private static void ConfigurePaymentTransactionForTest(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<PaymentTransaction>(entity =>
        {
            entity.ToTable("payment_transactions");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id).HasColumnName("id").HasMaxLength(50);
            entity.Property(e => e.PaymentId).HasColumnName("payment_id").HasMaxLength(50).IsRequired();
            entity.Property(e => e.Method).HasColumnName("method").HasConversion<string>().HasMaxLength(20).IsRequired();
            entity.Property(e => e.Status).HasColumnName("status").HasConversion<string>().HasMaxLength(20).IsRequired();
            entity.Property(e => e.Amount).HasColumnName("amount").HasPrecision(18, 2).IsRequired();
            entity.Property(e => e.Provider).HasColumnName("provider").HasMaxLength(50).IsRequired();
            entity.Property(e => e.ProviderTransactionId).HasColumnName("provider_transaction_id").HasMaxLength(200);
            entity.Property(e => e.Note).HasColumnName("note").HasMaxLength(500);
            entity.Property(e => e.CreatedAt).HasColumnName("created_at").IsRequired();
            entity.HasOne(e => e.Payment).WithMany(p => p.Transactions).HasForeignKey(e => e.PaymentId).OnDelete(DeleteBehavior.Cascade);
            entity.HasIndex(e => e.PaymentId);
            entity.HasIndex(e => e.Status);
            entity.HasIndex(e => e.ProviderTransactionId);
        });
    }

    private static void ConfigureChatSessionForTest(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<ChatSession>(entity =>
        {
            entity.ToTable("chat_sessions");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id).HasColumnName("id").HasMaxLength(50);
            entity.Property(e => e.RestaurantTableId).HasColumnName("restaurant_table_id").HasMaxLength(50);
            entity.Property(e => e.TableCode).HasColumnName("table_code").HasMaxLength(20);
            entity.Property(e => e.OrderId).HasColumnName("order_id").HasMaxLength(50);
            entity.Property(e => e.IsClosed).HasColumnName("is_closed").IsRequired();
            entity.Property(e => e.CreatedAt).HasColumnName("created_at").IsRequired();
            entity.Property(e => e.UpdatedAt).HasColumnName("updated_at").IsRequired();
            entity.HasOne(e => e.RestaurantTable).WithMany().HasForeignKey(e => e.RestaurantTableId).OnDelete(DeleteBehavior.SetNull);
            entity.HasOne(e => e.Order).WithMany().HasForeignKey(e => e.OrderId).OnDelete(DeleteBehavior.SetNull);
            entity.HasIndex(e => e.RestaurantTableId);
            entity.HasIndex(e => e.OrderId);
            entity.HasIndex(e => e.IsClosed);
        });
    }

    private static void ConfigureChatMessageForTest(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<ChatMessage>(entity =>
        {
            entity.ToTable("chat_messages");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id).HasColumnName("id").HasMaxLength(50);
            entity.Property(e => e.ChatSessionId).HasColumnName("chat_session_id").HasMaxLength(50).IsRequired();
            entity.Property(e => e.Role).HasColumnName("role").HasMaxLength(20).IsRequired();
            entity.Property(e => e.Content).HasColumnName("content").IsRequired();
            entity.Property(e => e.SuggestedCartActionsJson).HasColumnName("suggested_cart_actions_json").HasColumnType("jsonb");
            entity.Property(e => e.CreatedAt).HasColumnName("created_at").IsRequired();
            entity.HasOne(e => e.ChatSession).WithMany(s => s.Messages).HasForeignKey(e => e.ChatSessionId).OnDelete(DeleteBehavior.Cascade);
            entity.HasIndex(e => e.ChatSessionId);
        });
    }

    private static void ConfigureKnowledgeEntryForTest(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<KnowledgeEntry>(entity =>
        {
            entity.ToTable("knowledge_entries");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id).HasColumnName("id").HasMaxLength(50);
            entity.Property(e => e.Title).HasColumnName("title").HasMaxLength(300).IsRequired();
            entity.Property(e => e.Content).HasColumnName("content").IsRequired();
            entity.Property(e => e.SourceType).HasColumnName("source_type").HasMaxLength(50).IsRequired();
            entity.Property(e => e.MenuItemId).HasColumnName("menu_item_id").HasMaxLength(50);
            entity.Property(e => e.Tags).HasColumnName("tags").HasConversion(
                v => string.Join(",", v),
                v => string.IsNullOrEmpty(v) ? new List<string>() : v.Split(',', StringSplitOptions.RemoveEmptyEntries).ToList());
            entity.Property(e => e.Embedding).HasColumnName("embedding").HasColumnType("jsonb");
            entity.Property(e => e.IsActive).HasColumnName("is_active").IsRequired();
            entity.Property(e => e.CreatedAt).HasColumnName("created_at").IsRequired();
            entity.Property(e => e.UpdatedAt).HasColumnName("updated_at").IsRequired();
            entity.HasOne(e => e.MenuItem).WithMany().HasForeignKey(e => e.MenuItemId).OnDelete(DeleteBehavior.SetNull);
            entity.HasIndex(e => e.IsActive);
            entity.HasIndex(e => e.MenuItemId);
        });
    }

    private static void ConfigureUserForTest(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<User>(entity =>
        {
            entity.ToTable("users");
            entity.HasKey(e => e.Id);
            entity.Property(e => e.Id).HasColumnName("id").HasMaxLength(50);
            entity.Property(e => e.FullName).HasColumnName("full_name").HasMaxLength(200).IsRequired();
            entity.Property(e => e.Email).HasColumnName("email").HasMaxLength(255).IsRequired();
            entity.Property(e => e.PasswordHash).HasColumnName("password_hash").HasMaxLength(200).IsRequired();
            entity.Property(e => e.Role).HasColumnName("role").HasMaxLength(20).IsRequired();
            entity.Property(e => e.CreatedAt).HasColumnName("created_at").IsRequired();
            entity.Property(e => e.UpdatedAt).HasColumnName("updated_at").IsRequired();
            entity.HasIndex(e => e.Email).IsUnique();
        });
    }

    public async Task SeedDataAsync()
    {
        await Database.EnsureDeletedAsync();
        await Database.EnsureCreatedAsync();

        if (await Categories.AnyAsync())
        {
            return;
        }

        var now = DateTimeOffset.UtcNow;
        var passwordHasher = new PasswordHasher();

        Users.Add(new User
        {
            Id = "usr_test_admin",
            FullName = "Quan Tri Test",
            Email = "admin@restaurant.local",
            PasswordHash = passwordHasher.HashPassword("Admin@1234"),
            Role = UserRole.Admin,
            CreatedAt = now,
            UpdatedAt = now
        });

        Categories.AddRange(
            new Category { Id = "cat_appetizer", Name = "Khai vi", DisplayOrder = 10, IsActive = true, CreatedAt = now, UpdatedAt = now },
            new Category { Id = "cat_main", Name = "Mon chinh", DisplayOrder = 20, IsActive = true, CreatedAt = now, UpdatedAt = now },
            new Category { Id = "cat_noodle", Name = "Pho va bun", DisplayOrder = 30, IsActive = true, CreatedAt = now, UpdatedAt = now },
            new Category { Id = "cat_seafood", Name = "Hai san", DisplayOrder = 40, IsActive = true, CreatedAt = now, UpdatedAt = now },
            new Category { Id = "cat_drink", Name = "Do uong", DisplayOrder = 50, IsActive = true, CreatedAt = now, UpdatedAt = now },
            new Category { Id = "cat_dessert", Name = "Trang mieng", DisplayOrder = 60, IsActive = true, CreatedAt = now, UpdatedAt = now }
        );

        MenuItems.AddRange(
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

        RestaurantTables.AddRange(Enumerable.Range(1, 8).Select(number => new RestaurantTable
        {
            Id = $"tbl_{number:00}",
            TableCode = $"T{number:00}",
            DisplayName = $"Ban {number:00}",
            IsActive = true,
            QrToken = $"cmc-table-t{number:00}-qr",
            CreatedAt = now,
            UpdatedAt = now
        }));

        await SaveChangesAsync();
    }
}

public sealed class RecordingOrderRealtimeNotifier : IOrderRealtimeNotifier
{
    public List<OrderCreatedEvent> Created { get; } = [];
    public List<(OrderStatusChangedEvent Payload, string? TableCode)> StatusChanged { get; } = [];
    public List<(OrderItemStatusChangedEvent Payload, string? TableCode)> ItemStatusChanged { get; } = [];

    public void Clear()
    {
        Created.Clear();
        StatusChanged.Clear();
        ItemStatusChanged.Clear();
    }

    public Task OrderCreatedAsync(OrderCreatedEvent payload, CancellationToken cancellationToken)
    {
        Created.Add(payload);
        return Task.CompletedTask;
    }

    public Task OrderStatusChangedAsync(
        OrderStatusChangedEvent payload,
        string? tableCode,
        CancellationToken cancellationToken)
    {
        StatusChanged.Add((payload, tableCode));
        return Task.CompletedTask;
    }

    public Task OrderItemStatusChangedAsync(
        OrderItemStatusChangedEvent payload,
        string? tableCode,
        CancellationToken cancellationToken)
    {
        ItemStatusChanged.Add((payload, tableCode));
        return Task.CompletedTask;
    }
}
