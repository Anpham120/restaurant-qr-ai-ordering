import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const frontendRoot = new URL("../../", import.meta.url);
const dockerfilePath = fileURLToPath(new URL("Dockerfile", frontendRoot));
const aiDockerfilePath = fileURLToPath(new URL("../ai/Dockerfile", frontendRoot));
const aiRequirementsPath = fileURLToPath(new URL("../ai/requirements.txt", frontendRoot));
const aiRagRequirementsPath = fileURLToPath(
  new URL("../ai/requirements-rag.txt", frontendRoot),
);
const healthCheckPath = fileURLToPath(
  new URL("../deploy/scripts/health-check.sh", frontendRoot),
);

describe("frontend Dockerfile workspace manifests", () => {
  it("copies only package manifests that exist in the build context", () => {
    const dockerfile = readFileSync(dockerfilePath, "utf8");
    const manifestPaths = [...dockerfile.matchAll(/^COPY frontend\/(\S*package\.json)\s/mg)]
      .map((match) => match[1]!);

    expect(manifestPaths.length).toBeGreaterThan(0);
    for (const manifestPath of manifestPaths) {
      expect(existsSync(fileURLToPath(new URL(manifestPath, frontendRoot))), manifestPath).toBe(true);
    }
  });
});

describe("AI Docker production dependencies", () => {
  // Test này TỪNG đòi ảnh Docker cài `torch==2.13.0+cpu`. Bản dựng lại phần AI đã BỎ torch và
  // sentence-transformers khỏi ảnh sau khi ĐO được là không cần: truy hồi tri thức lúc đó là
  // TRA KHÓA trên 24 chủ đề `answer_mode: verbatim` — chính xác tuyệt đối, 0ms, không xếp hạng.
  //
  // Phép so ba cách truy hồi (`ai/evaluation/run_retrieval_comparison.py`) cho thấy embedding
  // THẮNG trên tập niêm phong (Hit@5 0,921 so với BM25 0,711). Nhưng nó vẫn không vào ảnh, vì
  // đường `synthesize` mà nó phục vụ CHƯA CÓ AI GỌI ở runtime — thêm 2–3GB cho một khả năng
  // chưa có ai gọi là chi phí không có lợi ích.
  //
  // Nên hàng rào được ĐẢO CHIỀU thay vì xóa. Xóa test thì mất luôn thứ chặn việc ai đó lặng lẽ
  // thêm lại 3GB vào ảnh sản phẩm; đảo chiều thì hàng rào vẫn còn, chỉ canh quyết định mới.
  //
  // Điều kiện để đảo lại: khi đường `synthesize` được dựng. Lúc đó +21 điểm Hit@5 thành lợi ích
  // thật, và test này phải được sửa CÙNG với việc đó — xem `ai/requirements-rag.txt`.
  // Chỉ quét DÒNG LỆNH, bỏ dòng chú thích. Bản đầu của test này quét cả tệp và đỏ ngay — vì
  // `ai/Dockerfile` có chữ "torch" trong một CHÚ THÍCH nói rằng torch đã được bỏ.
  //
  // Đây là lớp lỗi thứ tư cùng loại trong dự án: phép quét chuỗi khớp vào chính lời giải thích của
  // nó. Ba lần trước là phép kiểm điểm vào Dockerfile đọc `uvicorn` từ một comment, phép kiểm
  // schema khớp tên trường bên trong `description`, và phép kiểm "không dùng random.shuffle" khớp
  // đúng câu chú thích giải thích vì sao không dùng.
  const instructionLines = (text: string): string =>
    text
      .split("\n")
      .filter((line) => !line.trimStart().startsWith("#"))
      .join("\n");

  it("keeps heavy ML dependencies OUT of the runtime image", () => {
    const dockerfile = instructionLines(readFileSync(aiDockerfilePath, "utf8"));
    const requirements = instructionLines(readFileSync(aiRequirementsPath, "utf8"));

    for (const heavy of ["torch", "sentence-transformers", "sentence_transformers"]) {
      expect(dockerfile, `ai/Dockerfile không được cài ${heavy}`).not.toContain(heavy);
      expect(requirements, `ai/requirements.txt không được có ${heavy}`).not.toContain(heavy);
    }
  });

  it("keeps the embedding capability reachable for measurement", () => {
    // Bỏ khỏi ảnh KHÔNG được bằng bỏ khả năng đo. Nếu tệp này mất thì phép so ba cách truy hồi
    // im lặng chỉ còn BM25, và bảng kết quả vẫn trông như một phép so đầy đủ.
    const ragRequirements = instructionLines(readFileSync(aiRagRequirementsPath, "utf8"));

    expect(ragRequirements).toMatch(/^sentence-transformers/m);
  });
});

describe("production health check retries", () => {
  it("retries transient TLS errors while nginx certificates reload", () => {
    const healthCheck = readFileSync(healthCheckPath, "utf8");

    expect(healthCheck).toContain("--retry-all-errors");
  });
});
