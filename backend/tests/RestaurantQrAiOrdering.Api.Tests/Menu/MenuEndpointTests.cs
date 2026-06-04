using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.AspNetCore.Mvc.Testing;

namespace RestaurantQrAiOrdering.Api.Tests.Menu;

public sealed class MenuEndpointTests
{
    [Fact]
    public async Task GetMenu_ReturnsCategoriesAndAvailabilityState()
    {
        await using var factory = new WebApplicationFactory<Program>();
        using var client = factory.CreateClient();

        using var response = await client.GetAsync("/api/menu");
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        var root = body.RootElement;
        var items = root.GetProperty("items").EnumerateArray().ToList();

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.NotEmpty(root.GetProperty("categories").EnumerateArray());
        Assert.Contains(items, item => item.GetProperty("isAvailable").GetBoolean());
        Assert.Contains(items, item => !item.GetProperty("isAvailable").GetBoolean());
        Assert.Contains(items, item => item.GetProperty("id").GetString() == "m_004");
    }

    [Fact]
    public async Task AdminCategoryCrud_CreatesUpdatesAndDeletesCategory()
    {
        await using var factory = new WebApplicationFactory<Program>();
        using var client = factory.CreateClient();

        using var createResponse = await client.PostAsJsonAsync("/api/admin/categories", new
        {
            name = "Mon dac biet",
            displayOrder = 90,
            isActive = true
        });

        using var createdBody = await JsonDocument.ParseAsync(await createResponse.Content.ReadAsStreamAsync());
        var categoryId = createdBody.RootElement.GetProperty("categoryId").GetString();

        Assert.Equal(HttpStatusCode.Created, createResponse.StatusCode);
        Assert.False(string.IsNullOrWhiteSpace(categoryId));

        using var updateResponse = await client.PutAsJsonAsync($"/api/admin/categories/{categoryId}", new
        {
            name = "Mon dac biet hom nay",
            displayOrder = 91,
            isActive = true
        });

        using var updatedBody = await JsonDocument.ParseAsync(await updateResponse.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, updateResponse.StatusCode);
        Assert.Equal("Mon dac biet hom nay", updatedBody.RootElement.GetProperty("name").GetString());
        Assert.Equal(91, updatedBody.RootElement.GetProperty("displayOrder").GetInt32());

        using var deleteResponse = await client.DeleteAsync($"/api/admin/categories/{categoryId}");

        Assert.Equal(HttpStatusCode.NoContent, deleteResponse.StatusCode);
    }

    [Fact]
    public async Task AdminMenuItemCrud_CreatesUpdatesTogglesAvailabilityAndDeletesItem()
    {
        await using var factory = new WebApplicationFactory<Program>();
        using var client = factory.CreateClient();

        var categoryId = await CreateCategoryAsync(client);

        using var createResponse = await client.PostAsJsonAsync("/api/admin/menu-items", new
        {
            categoryId,
            name = "Banh mi bo kho",
            description = "Banh mi nong an kem bo kho sot sanh.",
            price = 58000,
            imageUrl = "https://example.com/images/banh-mi-bo-kho.jpg",
            isAvailable = true,
            tags = new[] { "bo kho", "dac biet" }
        });

        using var createdBody = await JsonDocument.ParseAsync(await createResponse.Content.ReadAsStreamAsync());
        var itemId = createdBody.RootElement.GetProperty("id").GetString();

        Assert.Equal(HttpStatusCode.Created, createResponse.StatusCode);
        Assert.True(createdBody.RootElement.GetProperty("isAvailable").GetBoolean());

        using var updateResponse = await client.PutAsJsonAsync($"/api/admin/menu-items/{itemId}", new
        {
            categoryId,
            name = "Banh mi bo kho dac biet",
            description = "Banh mi nong, bo kho va rau thom.",
            price = 62000,
            imageUrl = "https://example.com/images/banh-mi-bo-kho.jpg",
            isAvailable = true,
            tags = new[] { "bo kho" }
        });

        using var updatedBody = await JsonDocument.ParseAsync(await updateResponse.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, updateResponse.StatusCode);
        Assert.Equal("Banh mi bo kho dac biet", updatedBody.RootElement.GetProperty("name").GetString());
        Assert.Equal(62000, updatedBody.RootElement.GetProperty("price").GetDecimal());

        using var toggleResponse = await client.PatchAsJsonAsync($"/api/admin/menu-items/{itemId}/availability", new
        {
            isAvailable = false
        });

        using var toggledBody = await JsonDocument.ParseAsync(await toggleResponse.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, toggleResponse.StatusCode);
        Assert.False(toggledBody.RootElement.GetProperty("isAvailable").GetBoolean());

        using var deleteItemResponse = await client.DeleteAsync($"/api/admin/menu-items/{itemId}");
        using var deleteCategoryResponse = await client.DeleteAsync($"/api/admin/categories/{categoryId}");

        Assert.Equal(HttpStatusCode.NoContent, deleteItemResponse.StatusCode);
        Assert.Equal(HttpStatusCode.NoContent, deleteCategoryResponse.StatusCode);
    }

    [Fact]
    public async Task AdminCreateMenuItem_RejectsInvalidPriceAndCategory()
    {
        await using var factory = new WebApplicationFactory<Program>();
        using var client = factory.CreateClient();

        using var response = await client.PostAsJsonAsync("/api/admin/menu-items", new
        {
            categoryId = "cat_missing",
            name = "Mon loi",
            description = "",
            price = 0,
            imageUrl = "",
            isAvailable = true,
            tags = Array.Empty<string>()
        });

        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("CATEGORY_INVALID", body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    private static async Task<string> CreateCategoryAsync(HttpClient client)
    {
        using var createCategoryResponse = await client.PostAsJsonAsync("/api/admin/categories", new
        {
            name = "Mon test",
            displayOrder = 95,
            isActive = true
        });

        using var createCategoryBody = await JsonDocument.ParseAsync(await createCategoryResponse.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.Created, createCategoryResponse.StatusCode);

        return createCategoryBody.RootElement.GetProperty("categoryId").GetString()!;
    }
}
