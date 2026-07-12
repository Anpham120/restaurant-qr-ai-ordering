import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const repositoryRoot = new URL("../../../", import.meta.url);

const readRepositoryFile = (path: string) =>
  readFileSync(fileURLToPath(new URL(path, repositoryRoot)), "utf8");

describe("deployment workflow environment", () => {
  it("supplies every variable required by the VPS deploy script", () => {
    const deployScript = readRepositoryFile("deploy/scripts/deploy-vps.sh");
    const requiredBlock = deployScript.match(/required_vars=\(\s*([\s\S]*?)\s*\)/)?.[1];

    expect(requiredBlock).toBeTruthy();
    const requiredVariables = requiredBlock!.trim().split(/\s+/);

    for (const workflowPath of [
      ".github/workflows/deploy-production.yml",
      ".github/workflows/deploy-staging.yml",
    ]) {
      const workflow = readRepositoryFile(workflowPath);
      for (const variable of requiredVariables) {
        expect(workflow, `${workflowPath} must supply ${variable}`).toMatch(
          new RegExp(`^\\s+${variable}:`, "m"),
        );
      }
    }
  });
});
