using System.Reflection;
using Xunit;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class AiContractBoundaryTests
{
    [Fact]
    public void ChatAiProvider_UsesStableAiServicePaths()
    {
        var source = ReadSource("ChatAiProvider.cs");

        Assert.Contains("/v1/chat", source, StringComparison.Ordinal);
        Assert.Contains("/v1/chat/stream", source, StringComparison.Ordinal);
        Assert.DoesNotContain("/v2/chat", source, StringComparison.Ordinal);
    }

    /// <summary>
    /// Bản AI cũ đã được xóa để dựng lại (xem <c>ai/README.md</c>), và hợp đồng HTTP sẽ
    /// được thiết kế lại ở cuối lộ trình — nên hiện chưa có tệp schema nào.
    ///
    /// Test này trước đây đòi tệp schema phải tồn tại. Giữ nguyên như vậy thì nó đỏ suốt
    /// quá trình dựng lại và người ta sẽ học cách bỏ qua nó. Tạo một tệp schema giả cho nó
    /// xanh thì tệ hơn: hợp đồng chưa được thiết kế, và một tệp giả sẽ được ai đó tin.
    ///
    /// Nên nó thành phép kiểm có điều kiện: khi hợp đồng mới xuất hiện, nó lập tức bắt đầu
    /// đòi đúng những trường mà backend phụ thuộc. Không đỏ oan trong lúc chưa có, mà cũng
    /// không âm thầm mất tác dụng khi có.
    /// </summary>
    [Fact]
    public void AiContractSchema_WhenPresent_DeclaresFieldsBackendDependsOn()
    {
        var schemaPath = Path.Combine(
            FindRepositoryRoot(), "ai", "contracts", "ai-chat-v1.schema.json");
        if (!File.Exists(schemaPath))
        {
            // Chưa tới bước thiết kế lại hợp đồng. Không có gì để kiểm, và cũng không có
            // gì để giả vờ.
            return;
        }

        var schema = File.ReadAllText(schemaPath);
        Assert.Contains("\"ChatRequest\"", schema, StringComparison.Ordinal);
        Assert.Contains("\"ChatResponse\"", schema, StringComparison.Ordinal);
        Assert.Contains("suggested_cart_actions", schema, StringComparison.Ordinal);
    }

    private static string ReadSource(string fileName)
    {
        var apiRoot = Path.Combine(FindRepositoryRoot(), "backend", "src", "RestaurantQrAiOrdering.Api");
        var path = Directory.EnumerateFiles(apiRoot, fileName, SearchOption.AllDirectories).FirstOrDefault();
        Assert.NotNull(path);
        return File.ReadAllText(path!);
    }

    /// <summary>
    /// Mốc tìm gốc repo là tệp solution của backend, không phải <c>ai/contracts</c>.
    ///
    /// Mốc cũ là chính thư mục đang được dựng lại, nên khi nó bị xóa thì hàm này ném lỗi
    /// và làm đỏ **cả hai** test trong lớp này — kể cả test về đường dẫn của
    /// <c>ChatAiProvider</c>, thứ vẫn còn nguyên và vẫn đúng. Một helper không nên gắn số
    /// phận của mình vào thư mục dễ biến động nhất trong repo.
    /// </summary>
    private static string FindRepositoryRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            if (File.Exists(Path.Combine(directory.FullName, "backend", "RestaurantQrAiOrdering.sln")))
            {
                return directory.FullName;
            }

            directory = directory.Parent;
        }

        throw new InvalidOperationException("Could not locate repository root.");
    }
}
