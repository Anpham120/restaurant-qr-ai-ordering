using RestaurantQrAiOrdering.Api.Chat;
using Xunit;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class ChatMenuGroundingTests
{
    [Fact]
    public void TestV34_SeafoodCategoryRequest_OnlyReturnsSeafoodCandidates()
    {
        var candidates = ChatMenuGrounding.Select(
            "Cho tôi các món hải sản",
            [
                Item("sea_1", "Nghêu hấp sả", "Hải sản", ["Hấp", "Nhậu"]),
                Item("sea_2", "Tôm rang muối", "Hải sản", ["Tôm", "Chia sẻ"]),
                Item("main_1", "Cơm cá kho tộ", "Món chính", ["Bữa chính"])
            ]);

        Assert.Equal(["sea_1", "sea_2"], candidates.Select(item => item.Id).OrderBy(id => id));
        Assert.All(candidates, item => Assert.Equal("Hải sản", item.CategoryName));
    }

    [Fact]
    public void TestV34_TagRequest_OnlyReturnsMatchingCandidates()
    {
        var candidates = ChatMenuGrounding.Select(
            "Tôi muốn món hấp",
            [
                Item("sea_1", "Nghêu hấp sả", "Hải sản", ["Hấp", "Nhậu"]),
                Item("sea_2", "Tôm rang muối", "Hải sản", ["Tôm"]),
                Item("main_1", "Cơm cá kho tộ", "Món chính", ["Bữa chính"])
            ]);

        Assert.Single(candidates);
        Assert.Equal("sea_1", candidates[0].Id);
    }

    [Fact]
    public void TestV35_ExplicitCategory_IsReportedAsHardConstraint()
    {
        var result = ChatMenuGrounding.SelectWithConstraints(
            "đề xuất cho tôi các món hải sản cơ mà",
            [
                Item("sea_1", "Nghêu hấp sả", "Hải sản", ["Hấp"]),
                Item("main_1", "Cơm cá kho tộ", "Món chính", ["Bữa chính"])
            ]);

        Assert.True(result.HasExplicitConstraint);
        Assert.Equal(["Hải sản"], result.MatchedCategoryNames);
        Assert.All(result.Candidates, item => Assert.Equal("Hải sản", item.CategoryName));
    }

    private static ChatMenuItemContext Item(string id, string name, string categoryName, IReadOnlyList<string> tags) =>
        new(id, name, string.Empty, 65_000m, $"cat_{id}", categoryName, tags, true);
}
