using Xunit;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class DeploymentConfigurationTests
{
    /// <summary>
    /// Dịch vụ AI phải hết hạn TRƯỚC backend, để backend còn nhận được câu thoái hóa thay vì tự hết
    /// hạn rồi trả lỗi cho khách đang ngồi ở bàn.
    ///
    /// Vì sao test này phải VIẾT LẠI chứ không xóa: nó từng canh `AI_REQUEST_BUDGET_SECONDS` (45) —
    /// một biến của hệ thống AI cũ mà bản dựng lại **không đọc**. Tức nó canh một bất biến CHẾT:
    /// đổi giá trị đó không đổi hành vi nào, và test vẫn xanh.
    ///
    /// Quan hệ đáng canh vẫn còn, chỉ đổi tên biến: `LLM_TIMEOUT_SECONDS` (30) là thứ dịch vụ AI
    /// thật sự đọc (`llm_understand.ENV_KEYS`), và nó phải nhỏ hơn `BACKEND_AI_TIMEOUT_SECONDS`
    /// (50) mà `ChatAiProvider.ReadPositiveInt` đọc.
    ///
    /// So SỐ chứ không so chuỗi: một test so chuỗi `"...:-30}"` sẽ xanh nếu ai đó đổi 30 thành 60
    /// bằng cách viết khác đi, và đỏ vì lý do vô hại khi chỉ đổi cách viết.
    /// </summary>
    [Fact]
    public void DockerCompose_LetsTheAiServiceTimeOutBeforeTheBackendDoes()
    {
        var compose = File.ReadAllText(
            Path.Combine(FindRepositoryRoot(), "deploy", "docker-compose.yml"));

        var backendTimeout = ReadComposeDefault(compose, "BACKEND_AI_TIMEOUT_SECONDS");
        var aiTimeout = ReadComposeDefault(compose, "LLM_TIMEOUT_SECONDS");

        Assert.True(
            aiTimeout < backendTimeout,
            $"LLM_TIMEOUT_SECONDS ({aiTimeout}) phải nhỏ hơn BACKEND_AI_TIMEOUT_SECONDS "
                + $"({backendTimeout}); nếu không backend hết hạn trước và khách nhận lỗi thay vì "
                + "câu thoái hóa");
    }

    private static int ReadComposeDefault(string compose, string name)
    {
        var match = System.Text.RegularExpressions.Regex.Match(
            compose,
            $@"{System.Text.RegularExpressions.Regex.Escape(name)}:\s*\$\{{{System.Text.RegularExpressions.Regex.Escape(name)}:-(\d+)\}}");

        Assert.True(
            match.Success,
            $"không tìm thấy `{name}: ${{{name}:-<số>}}` trong docker-compose.yml — biến này là "
                + "một đầu của bất biến hết hạn, nên nó biến mất là điều phải biết");
        return int.Parse(match.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture);
    }

    [Fact]
    public void HealthCheck_ExercisesTheBrowserFacingBackendAiPath()
    {
        var script = File.ReadAllText(
            Path.Combine(FindRepositoryRoot(), "deploy", "scripts", "health-check.sh"));

        Assert.Contains("Running backend-integrated AI smoke request", script, StringComparison.Ordinal);
        Assert.Contains("/api/chat/sessions", script, StringComparison.Ordinal);
        Assert.Contains("/messages/stream", script, StringComparison.Ordinal);
        Assert.Contains("X-Chat-Session-Token", script, StringComparison.Ordinal);
        Assert.Contains("AI_UPSTREAM_CONTRACT_ERROR", script, StringComparison.Ordinal);
        Assert.Contains("AI_PROVIDER_UNAVAILABLE", script, StringComparison.Ordinal);
    }

    /// <summary>
    /// Deploy phải đi qua một CỔNG đối chiếu cấu hình với bằng chứng đã đo, và KHÔNG được tự chạy
    /// lại phép đo trong bước deploy.
    ///
    /// Test này canh ba điều, và cả ba vẫn đáng canh sau khi phần AI được dựng lại — chỉ CƠ CHẾ đổi:
    ///
    ///   1. có một cổng đối chiếu bằng chứng   trước: verify_pipeline_selection.py + approved/…json
    ///                                        nay:   verify_deploy_config.py + measurements/…json
    ///   2. KHÔNG chạy lại phép đo trong deploy  (một bước deploy phụ thuộc mô hình ngoài là một
    ///                                          bước deploy đỏ vì lý do không liên quan)
    ///   3. KHÔNG mở đường hầm tới nhà cung cấp mô hình trong deploy
    ///
    /// Vì sao test này TỪNG ĐỎ và đó là điều đúng: nhánh dựng lại xóa
    /// `ai/evaluation/verify_pipeline_selection.py` cùng hệ thống AI cũ, nên hai workflow deploy gọi
    /// một tệp không còn tồn tại — tức merge được nhưng deploy hỏng. Test này là **đầu thứ hai** của
    /// bất biến, và nó bắt đúng chuyện đó. Đây là lần thứ sáu trong dự án mà một bất biến có hai đầu
    /// ở hai ngôn ngữ khác nhau.
    /// </summary>
    [Theory]
    [InlineData("deploy-staging.yml")]
    [InlineData("deploy-production.yml")]
    public void Deployment_VerifiesConfigAgainstRecordedEvidenceWithoutRerunningTheModel(
        string workflowName)
    {
        var repositoryRoot = FindRepositoryRoot();
        var workflow = File.ReadAllText(
            Path.Combine(repositoryRoot, ".github", "workflows", workflowName));

        // 1. Cổng đối chiếu phải có mặt, và script nó gọi phải TỒN TẠI.
        //
        // Kiểm sự tồn tại chứ không chỉ kiểm chuỗi: bước cũ đỏ vì tệp bị xóa mà workflow vẫn gọi, và
        // một phép kiểm chỉ so chuỗi sẽ xanh với đúng lỗi đó.
        Assert.Contains(
            "ai/evaluation/verify_deploy_config.py",
            workflow,
            StringComparison.Ordinal);
        Assert.True(
            File.Exists(Path.Combine(repositoryRoot, "ai", "evaluation", "verify_deploy_config.py")),
            "workflow gọi verify_deploy_config.py nhưng tệp đó không tồn tại — đúng lỗi đã làm "
                + "deploy hỏng ở bản trước");

        // 2. KHÔNG chạy lại phép đo trong bước deploy.
        Assert.DoesNotContain("run_pipeline_profile_eval.py", workflow, StringComparison.Ordinal);
        Assert.DoesNotContain("run_golden_e2e.py", workflow, StringComparison.Ordinal);
        Assert.DoesNotContain("run_llm_rag_eval.py", workflow, StringComparison.Ordinal);

        // 3. KHÔNG mở đường hầm tới nhà cung cấp mô hình trong deploy.
        Assert.DoesNotContain("Open secure 9router tunnel", workflow, StringComparison.Ordinal);
    }

    /// <summary>
    /// Cổng deploy phải có BẰNG CHỨNG để đối chiếu. Không có tệp bằng chứng thì cổng chỉ là một bước
    /// luôn đỏ, và người sau sẽ bỏ nó đi cho qua.
    /// </summary>
    [Fact]
    public void DeployGate_HasRecordedEvidenceForTheDefaultProductionConfiguration()
    {
        var evidence = Path.Combine(
            FindRepositoryRoot(), "ai", "evaluation", "measurements", "golden_e2e.json");

        Assert.True(
            File.Exists(evidence),
            "thiếu ai/evaluation/measurements/golden_e2e.json — cổng deploy không có gì để đối chiếu");
        Assert.Contains("\"do\": 0", File.ReadAllText(evidence), StringComparison.Ordinal);
    }

    private static string FindRepositoryRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            if (File.Exists(Path.Combine(directory.FullName, "deploy", "docker-compose.yml")))
            {
                return directory.FullName;
            }

            directory = directory.Parent;
        }

        throw new InvalidOperationException("Could not locate repository root.");
    }
}
