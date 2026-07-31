import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const frontendRoot = new URL("../../", import.meta.url);
const dockerfilePath = fileURLToPath(new URL("Dockerfile", frontendRoot));
const aiDockerfilePath = fileURLToPath(new URL("../ai/Dockerfile", frontendRoot));
const aiRequirementsPath = fileURLToPath(new URL("../ai/requirements.txt", frontendRoot));
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
  // LỊCH SỬ CỦA HÀNG RÀO NÀY — nó đã đảo chiều HAI lần, và cả hai lần đều theo một phép ĐO.
  //
  // Lần 1: test đòi ảnh Docker cài `torch==2.13.0+cpu`. Bước dựng lại BỎ torch và
  //   sentence-transformers khỏi ảnh sau khi đo rằng truy hồi tri thức lúc đó là TRA KHÓA trên 24
  //   chủ đề `verbatim` — chính xác tuyệt đối, 0ms, không xếp hạng. Test được ĐẢO CHIỀU thành "giữ
  //   thư viện nặng NGOÀI ảnh", kèm điều kiện để đảo lại: *khi đường `synthesize` được dựng*.
  //
  // Lần 2 (đây): điều kiện đó ĐÃ XẢY RA. Kho nay có 84 chủ đề `synthesize` và **74 trong số đó
  //   không có cụm từ vựng nào**, nên truy hồi là đường DUY NHẤT tới chúng. Embedding thắng ở cả
  //   hai bài toán và cả hai tập niêm phong, nên nó vào `ai/requirements.txt`.
  //
  // Vì sao vẫn giữ test thay vì xóa: rủi ro chỉ ĐỔI CHỖ, không mất. Trước đây rủi ro là "ai đó
  // lặng lẽ thêm 3GB vào ảnh". Nay rủi ro là **mất dòng ghim bản CPU**, và nó đắt hơn nhiều:
  //
  //     có `--extra-index-url .../whl/cpu`   ảnh 2,74GB
  //     thiếu nó                             ảnh 9,29GB  (pip lấy torch bản CUDA + gói NVIDIA)
  //
  // 6,55GB cho một dịch vụ chạy CPU và không có GPU nào. Và nó IM LẶNG: build vẫn thành công, dịch
  // vụ vẫn chạy đúng, chỉ ảnh to gấp 3,4 lần. Đúng loại lỗi chỉ người deploy phát hiện.
  //
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

  it("pins torch to the CPU wheel index whenever torch is a dependency", () => {
    // Bất biến ĐẮT NHẤT của tệp này: mất dòng index là +6,55GB, im lặng.
    const requirements = instructionLines(readFileSync(aiRequirementsPath, "utf8"));
    if (!requirements.includes("torch")) return; // không có torch thì không có gì để ghim

    expect(
      requirements,
      "ai/requirements.txt có torch mà THIẾU `--extra-index-url https://download.pytorch.org/whl/cpu`"
        + " — pip sẽ lấy bản CUDA và ảnh phình từ 2,74GB lên 9,29GB, im lặng",
    ).toContain("--extra-index-url https://download.pytorch.org/whl/cpu");
  });

  it("bakes the embedding model into the image and blocks network at runtime", () => {
    // Tải mô hình lúc CHẠY có hai hậu quả và cả hai chỉ hiện ở môi trường thật: khách ĐẦU TIÊN chờ
    // tải ~500MB, và dịch vụ phụ thuộc mạng ra Hugging Face SAU KHI `/ready` đã báo sẵn sàng.
    const dockerfile = instructionLines(readFileSync(aiDockerfilePath, "utf8"));
    const requirements = instructionLines(readFileSync(aiRequirementsPath, "utf8"));
    if (!requirements.includes("sentence-transformers")) return;

    expect(dockerfile, "ai/Dockerfile phải TẢI SẴN mô hình lúc build").toContain(
      "SentenceTransformer(",
    );
    expect(dockerfile, "thiếu HF_HUB_OFFLINE=1 — container sẽ gọi mạng lúc chạy").toContain(
      "HF_HUB_OFFLINE=1",
    );
    // Vector của kho phải được tính SẴN: đo được là mã hóa 370 đoạn mất 61,7s, tức 64% thời gian
    // khởi động, và nó tính đi tính lại cùng một kết quả mỗi lần container lên.
    expect(dockerfile, "thiếu bước tính sẵn vector — khởi động mất thêm ~62 giây mỗi lần").toContain(
      "rag.precompute",
    );
  });

  it("gives the AI healthcheck a start period long enough for model load", () => {
    // 97,3 giây khởi động với `start-period=15s`, `interval=30s`, `retries=3` làm lần kiểm thứ ba
    // rơi vào ~105s — dịch vụ SUÝT bị đánh `unhealthy`. Và `api` chờ `service_healthy`, nên hậu quả
    // không phải một cảnh báo mà là CẢ STACK KHÔNG LÊN trên máy chậm hơn 8%.
    const dockerfile = instructionLines(readFileSync(aiDockerfilePath, "utf8"));
    const requirements = instructionLines(readFileSync(aiRequirementsPath, "utf8"));
    if (!requirements.includes("sentence-transformers")) return;

    const match = dockerfile.match(/--start-period=(\d+)s/);
    expect(match, "ai/Dockerfile không có --start-period").not.toBeNull();
    expect(
      Number(match![1]),
      "start-period quá ngắn cho việc nạp mô hình — đo được 97,3s trước khi có đệm vector",
    ).toBeGreaterThanOrEqual(60);
  });
});

describe("production health check retries", () => {
  it("retries transient TLS errors while nginx certificates reload", () => {
    const healthCheck = readFileSync(healthCheckPath, "utf8");

    expect(healthCheck).toContain("--retry-all-errors");
  });
});
