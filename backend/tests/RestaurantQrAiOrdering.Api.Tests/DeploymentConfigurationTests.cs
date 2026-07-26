using Xunit;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class DeploymentConfigurationTests
{
    [Fact]
    public void DockerCompose_AllowsPythonRequestBudgetToFinishBeforeBackendTimeout()
    {
        var compose = File.ReadAllText(
            Path.Combine(FindRepositoryRoot(), "deploy", "docker-compose.yml"));

        Assert.Contains(
            "BACKEND_AI_TIMEOUT_SECONDS: ${BACKEND_AI_TIMEOUT_SECONDS:-18}",
            compose,
            StringComparison.Ordinal);
        Assert.Contains(
            "AI_REQUEST_BUDGET_SECONDS: ${AI_REQUEST_BUDGET_SECONDS:-14}",
            compose,
            StringComparison.Ordinal);
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

    [Theory]
    [InlineData("deploy-staging.yml")]
    [InlineData("deploy-production.yml")]
    public void Deployment_UsesApprovedResearchArtifactWithoutRerunningDeepSeek(string workflowName)
    {
        var workflow = File.ReadAllText(
            Path.Combine(FindRepositoryRoot(), ".github", "workflows", workflowName));

        Assert.Contains(
            "ai/evaluation/approved/pipeline_selection.json",
            workflow,
            StringComparison.Ordinal);
        Assert.Contains(
            "--verify-current-research-inputs",
            workflow,
            StringComparison.Ordinal);
        Assert.DoesNotContain(
            "run_pipeline_profile_eval.py",
            workflow,
            StringComparison.Ordinal);
        Assert.DoesNotContain(
            "Open secure 9router tunnel",
            workflow,
            StringComparison.Ordinal);
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
