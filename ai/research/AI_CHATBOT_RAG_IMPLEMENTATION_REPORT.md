# Báo cáo nghiên cứu, đánh giá và triển khai AI Chatbot RAG

**Phạm vi:** nhánh AI hiện tại, dựa trên mã nguồn, notebook, artifact nghiên cứu và test có trong repository.  
**Ngày soạn:** 2026-07-11.  
**Mức chứng cứ:** đây là báo cáo kỹ thuật có truy vết nguồn; không thay thế kết quả chạy lại pipeline hoặc kiểm thử CI tại thời điểm merge.

## 1. Kết luận điều hành

Hệ thống hiện tại là một **chatbot tra cứu được grounding bởi retrieval, có khả năng dùng LLM để sinh câu trả lời**:

- Khi điều kiện gọi provider thỏa mãn, LLM nhận context đã truy xuất, sáu lượt chat gần nhất và bộ nhớ phiên bàn bị giới hạn; đây là luồng LLM + RAG đúng nghĩa.
- Khi câu hỏi thuộc fast path (giá, chính sách, món hết, yêu cầu đặt món) hoặc provider không khả dụng, hệ thống trả lời có kiểm soát bằng dữ liệu retrieval mà không gọi LLM. Vì vậy, cách gọi chính xác nhất là **retrieval-grounded chatbot với LLM tùy chọn**, không phải một chatbot luôn luôn sinh câu trả lời bằng LLM.
- RAG không bắt buộc phải dùng vector database. Runtime đọc phương án production từ production_config.json của artifact fresh; retrieval vẫn được đưa vào prompt/context cho LLM khi LLM được gọi. Dense embedding và hybrid vẫn được cài đặt, chạy đánh giá và giữ trong study.
- Nhánh đã có năm phương án retrieval được triển khai và đánh giá: TF-IDF, BM25, dense embedding đa ngôn ngữ, BM25+dense weighted RRF và TF-IDF+dense weighted RRF. Cross-encoder/reranker **chưa** được triển khai hoặc đánh giá, không được mô tả là đã có.

Notebook có cấu trúc tuần tự, học thuật và có thể tái chạy: câu hỏi nghiên cứu → provenance → EDA/dữ liệu → tiền xử lý → phương án retrieval → protocol → chạy lại → tuning → test/statistics → demo → generation/safety. Xem [academic_retrieval_study.ipynb](../notebooks/academic_retrieval_study.ipynb).

Protocol chọn model hiện đã được ràng buộc đúng theo thứ tự khoa học:

1. [run_experiments.py](run_experiments.py) chọn winner bằng development macro slice nDCG@10; phương án trong tolerance 0.005 dùng development P95 latency làm tie-breaker.
2. Production selection rule ghi rõ frozen test chỉ dùng để đánh giá sau khi chọn.
3. [test_research_artifacts.py](../tests/test_research_artifacts.py) có test cô lập chứng minh winner development không thể bị thay đổi bởi metric test tốt hơn.

Một audit trước merge từng phát hiện implementation cũ chọn bằng test; source hiện tại đã được sửa. Vì sửa logic experiment làm thay đổi provenance, tất cả artifact và notebook phải được regenerate trước khi ghi nhận metric cuối cùng của bản sửa.

## 2. Bản đồ chứng cứ

| Nội dung | Nguồn chính |
|---|---|
| Notebook nghiên cứu tuần tự | [ai/notebooks/academic_retrieval_study.ipynb](../notebooks/academic_retrieval_study.ipynb) |
| Tạo dataset, split, provenance | [build_dataset.py](build_dataset.py), [run_experiments.py](run_experiments.py), [artifacts](artifacts) |
| RAG runtime và schema | [ai/app/services/assistant.py](../app/services/assistant.py), [ai/app/retrieval](../app/retrieval), [ai/app/schemas.py](../app/schemas.py) |
| API chat và compact memory | [ChatEndpoints.cs](../../backend/src/RestaurantQrAiOrdering.Api/Chat/ChatEndpoints.cs), [ChatAiProvider.cs](../../backend/src/RestaurantQrAiOrdering.Api/Chat/ChatAiProvider.cs) |
| Lưu session/chat trong database | [DbChatStore.cs](../../backend/src/RestaurantQrAiOrdering.Api/Chat/DbChatStore.cs) |
| Vòng đời phiên bàn/QR | [TableEndpoints.cs](../../backend/src/RestaurantQrAiOrdering.Api/Tables/TableEndpoints.cs) |
| Khôi phục lịch sử ở frontend | [useRestaurantChat.ts](../../frontend/src/hooks/useRestaurantChat.ts) |
| Test đơn vị và E2E | [ai/tests](../tests), [ChatEndpointTests.cs](../../backend/tests/RestaurantQrAiOrdering.Api.Tests/Chat/ChatEndpointTests.cs), [use-restaurant-chat.test.tsx](../../frontend/test/use-restaurant-chat.test.tsx) |

## 3. Bài toán và câu hỏi nghiên cứu

Notebook đặt bốn câu hỏi:

1. TF-IDF, BM25, dense embedding hay hybrid RRF xếp hạng tốt nhất?
2. Phương án nào bền vững với tiếng Việt không dấu, paraphrase, policy và câu hỏi multi-intent?
3. Phương án nào cân bằng chất lượng, độ trễ và chi phí vận hành?
4. Câu trả lời cuối có grounded, an toàn và truy vết được nguồn hay không?

Đây là framing phù hợp hơn việc xem chatbot như một bài toán “huấn luyện một model”: phần được chọn/tuning là **retriever và policy trả lời**, còn LLM là thành phần sinh câu trả lời có ràng buộc bởi bằng chứng retrieval.

## 4. Dữ liệu, provenance và EDA

### 4.1. Nguồn dữ liệu

Nguồn menu chuẩn là seed C# tại:

~~~text
backend/src/RestaurantQrAiOrdering.Api/Data/RestaurantMenuSeed.cs
~~~

Script [build_dataset.py](build_dataset.py) parse seed này, kiểm tra snapshot menu/categorical invariants và ghi dataset có truy vết. Dữ liệu policy được lấy từ [ai/data/policies.json](../data/policies.json).

Các số liệu có thể thay đổi theo run — số case development/test, số document, random seed, latency repeats, model embedding và hash — chỉ được lấy từ [environment.json](artifacts/environment.json) và [summary.json](artifacts/summary.json) của **artifact fresh**. Báo cáo không hard-code các số này để tránh biến một snapshot cũ thành kết luận hiện hành.

### 4.2. Thiết kế split và chống leakage

Mỗi nhóm biến thể của cùng một món hoặc cùng một policy có cùng group_id. Hàm _group_split băm SHA-256 group_id và đưa toàn bộ group vào development hoặc test; notebook kiểm tra mỗi group chỉ có một split.

Điều này xử lý leakage quan trọng: ví dụ tên món có dấu và không dấu của cùng một món không bị đưa sang hai phía khác nhau. Dataset còn có các slice như exact name, no diacritic, category intent và các case thủ công cho policy/multi-intent.

### 4.3. EDA trong notebook

Notebook không chỉ nhảy thẳng vào retriever. Phần EDA dựng:

- Bảng menu theo ID, danh mục, tên và độ dài mô tả.
- Số case theo split và theo slice.
- Kiểm tra phân bố group và assertion chống leakage.
- Bảng provenance/data fingerprint trước khi đọc metric.

Mục tiêu là làm lộ đặc tính dữ liệu trước khi diễn giải kết quả: menu ngắn, nhiều truy vấn khớp tên món, tiếng Việt có/không dấu và policy là những yếu tố có thể làm lexical retrieval mạnh hơn dense retrieval.

### 4.4. Provenance gate

Artifact lưu SHA-256 của menu snapshot, queries, policy, model embedding và evaluation script, cùng Python/package/hardware metadata. [test_research_artifacts.py](../tests/test_research_artifacts.py) kiểm tra:

- số case và split group không leakage;
- nguồn menu snapshot;
- hash của queries/menu/policy;
- hash văn bản chuẩn hóa CRLF/LF về LF để provenance ổn định giữa Windows và Linux;
- winner có trong summary;
- production config khớp artifact summary.

Notebook có cổng ARTIFACTS_FRESH: nếu code hoặc dữ liệu không khớp artifact, notebook hiển thị BLOCK và yêu cầu chạy lại pipeline. Artifact hiện tại đã được tái tạo sau khi sửa selection và chuẩn hóa hash; cổng provenance PASS. Mọi thay đổi tương lai đối với code hoặc dữ liệu vẫn phải chạy lại pipeline trước khi dùng metric làm kết quả hiện hành.

## 5. Chuẩn hóa, document hóa và chunking

### 5.1. Chuẩn hóa văn bản

[ai/app/text.py](../app/text.py) thực hiện:

1. lowercase;
2. thay đ thành d;
3. NFKD và bỏ combining marks để bỏ dấu tiếng Việt;
4. giữ token khớp mẫu a-z hoặc 0-9;
5. ghép lại thành chuỗi chuẩn, rồi tokenize theo khoảng trắng.

Nhờ đó, truy vấn “pho bo tai nam” có thể khớp với tên món có dấu. Chuẩn hóa này dùng cho retrieval; nội dung hiển thị/LLM vẫn lấy từ dữ liệu gốc có dấu.

### 5.2. Đơn vị document

Không có chunking theo số token cho menu, và đây là quyết định có chủ ý:

- Mỗi món là một document nguyên tử gồm tên, danh mục, mô tả và tags.
- Món không còn phục vụ không được đưa vào document retrieval.
- Mỗi policy là một document gồm tiêu đề, aliases và answer chuẩn.

Vì một món menu là đơn vị nghiệp vụ nhỏ, tách chunk có thể phá liên kết giữa menu_item_id, giá và availability. Đây không phải là thiếu bước preprocessing, mà là thiết kế document granularity phù hợp dữ liệu.

### 5.3. Freshness của tri thức runtime

Mỗi request gửi current menu từ backend vào AI service. [RetrievalService](../app/retrieval/service.py) tạo fingerprint của menu và chỉ rebuild index khi fingerprint thay đổi. Điều này tránh coi một knowledge base menu nhân bản, cũ và tách rời database là nguồn sự thật.

## 6. Các phương án retrieval đã so sánh

| Phương án | Trạng thái | Biểu diễn/cơ chế | Tuning trong study |
|---|---|---|---|
| TF-IDF | Đã cài đặt và đánh giá | Unigram + bigram TF-IDF | Không có grid riêng |
| BM25 | Đã cài đặt và đánh giá | BM25 lexical với title boost | k1, b, title_boost |
| Dense embedding | Đã cài đặt và đánh giá | FastEmbed với multilingual MiniLM | embedding model |
| Hybrid RRF | Đã cài đặt và đánh giá | BM25 + dense, weighted reciprocal-rank fusion | rrf_k, lexical_weight |
| Hybrid TF-IDF + embedding | Đã cài đặt và đánh giá | TF-IDF + dense, weighted RRF | rrf_k, lexical_weight |
| Cross-encoder/reranker | **Chưa có** | Không có rerank stage trong runtime/study | Chỉ là hướng mở rộng |

Chi tiết hiện có:

- BM25 thử các cấu hình k1 = 1.2/1.5/1.8, b = 0.65/0.75/0.80 và title boost = 1.0/1.2/1.5 trên development.
- Hybrid BM25+dense thử rrf_k 20/60 và lexical weight 1/2/4, dense weight cố định 1.0.
- Dense embedding dùng FastEmbed/ONNX với model multilingual MiniLM được ghi hash trong environment artifact.
- Tất cả phương án dùng cùng document và qrels, nên bảng metric là so sánh có kiểm soát giữa retriever chứ không phải so sánh giữa các dữ liệu khác nhau.

Reranker nên được thêm dưới protocol selection hiện đã đúng — development chọn phương án, frozen test chỉ đánh giá sau chọn — dưới dạng một candidate độc lập, chẳng hạn dense/hybrid lấy top-N rồi cross-encoder re-score. Khi đó cần đo thêm P95 end-to-end, chi phí inference và sự cải thiện có ý nghĩa thống kê; không nên giả định reranker chắc chắn tốt hơn trên menu ngắn.

## 7. Protocol đánh giá

### 7.1. Metric retrieval và vận hành

Notebook đo:

| Nhóm | Metric | Ý nghĩa |
|---|---|---|
| Xếp hạng | Hit@1 | Có document đúng ở vị trí đầu hay không |
| Xếp hạng | Hit@5 | Có ít nhất một document đúng trong top 5 |
| Xếp hạng | Recall@5 | Mức bao phủ document kỳ vọng, quan trọng với truy vấn nhiều món |
| Xếp hạng | MRR@10 | Độ sớm của kết quả đúng đầu tiên |
| Xếp hạng | nDCG@10 | Chất lượng thứ hạng có chiết khấu theo vị trí |
| Công bằng slice | Macro slice nDCG@10 | Trung bình theo nhóm truy vấn, tránh slice lớn lấn át |
| Vận hành | P50/P95 latency | Độ trễ retrieval |
| Abstention | Answerability | Phân biệt truy vấn nên/không nên trả lời bằng evidence |
| End-to-end | Groundedness, citation coverage, hallucination, guardrail, task success | Đánh giá chatbot thay vì chỉ retriever |

### 7.2. Tuning, test và statistics

Protocol hiện được thực thi là:

1. Tuning BM25/hybrid và threshold trên development.
2. Chọn một phương án trước test.
3. Đóng băng test và chỉ dùng test để báo cáo.
4. So sánh paired bằng bootstrap 95% CI của delta nDCG và McNemar exact two-sided cho Hit@5.

_select_winner hiện lấy dev.macro_slice_ndcg_at_10 và dev.latency_p95_ms; production selection rule nói rõ frozen test chỉ là post-selection evaluation. Test regression tạo hai phương án có dev/test winner trái nhau và assertion winner phải là dev_winner.

**Gate còn lại trước khi công bố/production hóa kết luận nghiên cứu**

1. Regenerate summary.json, production_config.json, statistical_tests.json, environment.json, per_query_results.csv và notebook bằng source đã sửa.
2. Xác nhận artifact mới ghi selection_split = dev và selection rule có frozen test post-selection.
3. Chạy test một lần với winner đã khóa; dùng kết quả đó để báo cáo cuối.
4. Lưu timestamp, config, threshold và hash input cùng artifact run.

### 7.3. Snapshot metric hiện có

Kết quả số của từng run là dữ liệu có hạn sử dụng: phải đọc trực tiếp từ [summary.json](artifacts/summary.json), [statistical_tests.json](artifacts/statistical_tests.json) và [per_query_results.csv](artifacts/per_query_results.csv) sau khi provenance gate PASS. Báo cáo này cố ý không sao chép metric cố định, vì menu, policy, qrels, model hoặc code đổi thì bảng cũ trở thành stale.

Bảng cần được xuất/đọc cho mỗi run có tối thiểu:

| Method | Dev macro slice nDCG@10 | Dev P95 | Test Hit@5 | Test nDCG@10 | Test macro slice nDCG@10 | Test P95 |
|---|---:|---:|---:|---:|---:|---:|
| TF-IDF | lấy từ artifact fresh | lấy từ artifact fresh | lấy từ artifact fresh | lấy từ artifact fresh | lấy từ artifact fresh | lấy từ artifact fresh |
| BM25 | lấy từ artifact fresh | lấy từ artifact fresh | lấy từ artifact fresh | lấy từ artifact fresh | lấy từ artifact fresh | lấy từ artifact fresh |
| Dense embedding | lấy từ artifact fresh | lấy từ artifact fresh | lấy từ artifact fresh | lấy từ artifact fresh | lấy từ artifact fresh | lấy từ artifact fresh |
| Hybrid BM25+dense RRF | lấy từ artifact fresh | lấy từ artifact fresh | lấy từ artifact fresh | lấy từ artifact fresh | lấy từ artifact fresh | lấy từ artifact fresh |
| Hybrid TF-IDF+dense RRF | lấy từ artifact fresh | lấy từ artifact fresh | lấy từ artifact fresh | lấy từ artifact fresh | lấy từ artifact fresh | lấy từ artifact fresh |

Diễn giải đúng mức:

- Winner production phải được đọc từ production_config.json mới và phải khớp selection_split = dev trong summary.
- Không có family nào được mặc định là tốt hơn: lexical, dense và hybrid phải được kết luận từ run mới trên cùng qrels.
- Phân tích slice, per-query failure và P95 phải đi cùng metric trung bình; không suy rộng kết quả từ catalog menu ngắn sang knowledge base khác.
- Bootstrap kiểm tra delta nDCG, còn McNemar kiểm tra khác biệt paired Hit@5; không dùng một p-value để thay cho toàn bộ đánh giá ranking.

## 8. Kiến trúc chatbot RAG + LLM

~~~mermaid
flowchart LR
    A["Khách quét QR / Customer web"] --> B["Table session + chat session API"]
    B --> C["PostgreSQL: table, chat session, messages"]
    B --> D["ChatAssistantService: menu hiện hành + history + compact memory"]
    D --> E["AI service /v1/chat"]
    E --> F{"Fast path / guardrail?"}
    F -->|Có| G["Câu trả lời xác định từ menu/policy"]
    F -->|Không| H["Retriever theo production_config"]
    H --> I["Retrieved sources + verified context"]
    I --> J{"LLM enabled và provider có sẵn?"}
    J -->|Có| K["9Router / Gemini Flash sinh câu trả lời grounded"]
    J -->|Không hoặc lỗi| L["Retrieval fallback"]
    G --> M["Diagnostics, sources, flags, suggested actions"]
    K --> M
    L --> M
    M --> B
    B --> A
~~~

### 8.1. Luồng backend và AI service

1. Customer app tạo hoặc khôi phục chat session gắn với tableSessionId.
2. Khi nhận một message, backend đọc tối đa 30 message trước khi lưu lượt hiện tại; sáu lượt gần nhất đi vào history.
3. Backend tạo compact session memory từ các user turn cũ hơn, tối đa 8 item và 1.200 ký tự.
4. ChatAssistantService đọc menu hiện hành từ database, cache 2 giây, rồi gửi menu, history, session memory và table code sang AI service.
5. AI service chạy intent/guardrail, retrieval và các fast path. Nếu cần LLM, prompt chỉ chứa context được kiểm chứng, history gần và session memory được đánh dấu là untrusted context.
6. Response trả về content, provider availability, model, retrieval method, sources, guardrail flags, suggested actions và latency.
7. Backend lưu cả user message và assistant message; UI nhận diagnostics và render kết quả.

### 8.2. Fast path và safety

Các fast path có mục tiêu giảm hallucination và không giao quyền thao tác cho LLM:

- prompt injection/out-of-scope bị chặn;
- món hết bị chặn trước provider;
- giá và policy trả lời từ canonical menu/policy;
- yêu cầu đặt món chỉ tạo gợi ý, luôn requires_customer_confirmation;
- output của model có các claim như “đã đặt”, “đã thêm giỏ”, “đã thanh toán” bị từ chối và chuyển fallback;
- provider lỗi/timeout trả retrieval fallback thay vì bịa câu trả lời.

### 8.3. Tính truy vết

Chat response có retrieved_sources, retrieval_method, fast_path, guardrail_flags và latency. Đây là nền tảng để UI/QA cho biết câu trả lời đã dựa vào document nào, thay vì xem câu trả lời LLM như một hộp đen.

## 9. Vòng đời phiên bàn, lịch sử chat và memory

~~~mermaid
flowchart TD
    A["Quét QR cùng bàn"] --> B{"Có TableSession Open, chưa hết hạn?"}
    B -->|Có| C["Trả về cùng tableSessionId"]
    B -->|Không| D["Tạo tableSessionId mới"]
    C --> E["CreateOrGet chat theo tableSessionId"]
    D --> E
    E --> F{"Có chat session đang mở?"}
    F -->|Có| G["Khôi phục chatSessionId + messages từ DB"]
    F -->|Không| H["Tạo chat session mới"]
    G --> I["Frontend giữ mapping localStorage"]
    H --> I
    J["Close hoặc hết hạn"] --> K["Xóa ChatSession gắn table session"]
    K --> L["Lịch sử/memory cũ không còn khôi phục"]
~~~

### 9.1. Điều gì được lưu ở đâu

| Dữ liệu | Nơi lưu | Vai trò |
|---|---|---|
| Table session | Database | Xác định phiên QR của bàn |
| Chat session và messages | Database | Nguồn sự thật cho lịch sử chat |
| Mapping tableSessionId → chatSessionId | localStorage nếu có table session | Tăng tốc khôi phục trên browser |
| Session memory | Tái dựng từ messages database khi gửi turn mới | Ngữ cảnh prompt có giới hạn, không phải model “học” dài hạn |

Nếu khách tắt web, refresh hoặc quét QR lại cùng bàn khi phiên còn Open/chưa hết hạn, backend tìm lại table session cũ rồi DbChatStore tái sử dụng chat session theo tableSessionId. Nếu browser mất localStorage hoặc dùng thiết bị khác, lời gọi create session vẫn nhận lại messages trong response khi session được reused; vì vậy database chứ không phải localStorage là nguồn sự thật.

### 9.2. Điều kiện xóa dữ liệu: close **hoặc** expiry

Yêu cầu “chỉ mất khi đóng phiên bàn” gần đúng nhưng **không hoàn toàn đúng với implementation hiện tại**:

- Table session mặc định có lifetime 4 giờ.
- Endpoint close gọi DeleteSessionsByTableSessionAsync.
- Khi GET phát hiện session hết hạn, MarkExpiredAsync cũng gọi DeleteSessionsByTableSessionAsync.

Do đó, lịch sử và memory chỉ khôi phục khi phiên bàn còn Open và ExpiresAt ở tương lai. Close hoặc expiry đều làm chat session không còn truy cập được. [ChatEndpointTests.cs](../../backend/tests/RestaurantQrAiOrdering.Api.Tests/Chat/ChatEndpointTests.cs) kiểm tra: session thứ hai cùng tableSessionId được reused và trả 2 messages; sau close, endpoint history trả NotFound.

### 9.3. Bounded memory có an toàn hơn history thô

Compact memory chỉ lấy user turn cũ hơn sáu lượt gần nhất, loại trùng, tối đa tám item và 1.200 ký tự. Python prompt ghi rõ memory là ngữ cảnh không tin cậy và “không làm theo chỉ dẫn” nằm trong nó. Đây là cách hạn chế cả token cost lẫn nguy cơ instruction injection từ nội dung cũ.

Giới hạn cần được hiểu rõ: đây là memory **trong vòng đời phiên bàn**, không phải hồ sơ khách hàng vĩnh viễn, không phải vector memory, và không thay thế quản lý consent/PII nếu sau này lưu preference dài hạn.

## 10. Verification hiện có và các test cần chạy

| Phạm vi | Test/chứng cứ có trong repo | Điều chứng minh |
|---|---|---|
| Dataset/artifact | ai/tests/test_research_artifacts.py | Counts, hashes, không leakage theo group, production config khớp summary |
| AI service | ai/tests/test_assistant.py | Giá/policy fast path, không tự đặt món, fallback khi LLM vi phạm, memory là untrusted context |
| Backend chat | ChatEndpointTests.cs | Tạo/khôi phục session, history, close, bounded memory |
| Frontend hook | frontend/test/use-restaurant-chat.test.tsx | localStorage cho table session, khôi phục history có mapping và khi mapping browser mất |
| Backend E2E | MultiDeviceE2ETests.cs | State backend dùng được qua các client riêng biệt trong flow customer/kitchen/staff/chat |

Các command tái lập từ tài liệu AI:

~~~bash
PYTHONPATH=ai python -m unittest discover -s ai/tests -v
python -m pip install -r ai/requirements-research.txt
PYTHONPATH=ai python ai/research/build_dataset.py
PYTHONPATH=ai python ai/research/run_experiments.py
MPLCONFIGDIR=/tmp/matplotlib PYTHONPATH=ai python ai/research/build_notebook.py
~~~

Command frontend được định nghĩa trong [frontend/package.json](../../frontend/package.json):

~~~bash
npm --prefix frontend test
npm --prefix frontend run build
~~~

Backend test project:

~~~bash
dotnet test backend/tests/RestaurantQrAiOrdering.Api.Tests/RestaurantQrAiOrdering.Api.Tests.csproj
~~~

Không ghi “PASS” trong báo cáo này chỉ vì test file tồn tại. Merge/release chỉ được phép ghi PASS sau khi command tương ứng chạy thành công trên đúng commit, và notebook provenance gate trả ARTIFACTS_FRESH = true.

## 11. Hạn chế và backlog nghiên cứu

1. **Audit protocol selection đã được remediate:** source hiện chọn bằng development và frozen test chỉ dùng post-selection; artifact cũ vẫn phải được regenerate và kiểm tra provenance trước khi dùng làm claim release.
2. **Artifact freshness:** menu, qrels, model hoặc code thay đổi đòi hỏi một experiment run mới; không suy diễn từ artifact cũ.
3. **Evaluation generation chưa hoàn tất:** notebook mới định nghĩa rubric groundedness, citation coverage, safety và task success; release checklist vẫn có các mục TODO cho selection record, frozen test, groundedness/safety và UI sources.
4. **Thiếu human/user evaluation:** chưa có log ẩn danh hay test người dùng thực tế để đo satisfaction, task success và chi phí thao tác.
5. **Không có reranker:** cross-encoder/reranker là candidate hợp lý nhưng chưa được implement/evaluate.
6. **Dữ liệu menu ngắn:** kết quả lexical mạnh không đảm bảo cho catalog dài, FAQ dài hoặc knowledge base nhiều tài liệu.
7. **LLM availability:** LLM là optional và provider có thể lỗi; cần theo dõi tỷ lệ fallback, latency, flags và quality trong production.
8. **Privacy/memory:** memory chỉ sống cùng session bàn nhưng vẫn có thể chứa preference/dị ứng; cần retention policy, access control và audit nếu mở rộng sang profile lâu dài.

## 12. Runbook triển khai và hợp nhất

### 12.1. Gate kỹ thuật trước khi merge

1. Rà lại diff để chỉ gồm thay đổi AI/RAG/chat-memory và báo cáo này.
2. Cài research dependencies, regenerate dataset/artifact/notebook bằng protocol đã xác minh: development chọn winner, frozen test chỉ hậu kiểm.
3. Kiểm tra artifact hashes, selection_split = dev và ARTIFACTS_FRESH.
4. Chạy Python, backend và frontend test/build.
5. Review metrics mới, error slices, bootstrap/McNemar và generation/safety checklist.
6. Chỉ sau đó mới commit, push branch AI và mở PR vào develop.

### 12.2. Quy trình merge và phát hành

1. Tạo PR từ nhánh AI vào develop, mô tả rõ retriever selection và limitation protocol.
2. Chờ CI pass; không bypass test/provenance gate.
3. Merge develop sau review.
4. Tạo PR hoặc promotion từ develop vào main theo release workflow của repository.
5. Sau deploy, kiểm tra:
   - GET /health của AI service;
   - POST /v1/retrieval/search và POST /v1/chat;
   - quét lại QR cùng bàn trả đúng tableSessionId/chat history khi session còn mở;
   - xóa localStorage hoặc dùng browser khác vẫn khôi phục bằng server;
   - close/expiry khiến history cũ không còn truy cập;
   - diagnostics có method, source, latency và guardrail flags.

### 12.3. Tiêu chí chấp nhận cuối cùng

Một release AI có thể được gọi là vừa vận hành được vừa có tính học thuật khi đồng thời thỏa:

- retriever production được chọn từ development trước test;
- frozen test, statistical comparison và provenance đều có artifact fresh;
- generation/safety có kết quả, không chỉ rubric;
- unit/E2E/frontend build pass trên commit merge;
- lifecycle table session, chat restore và cleanup được kiểm thử;
- observability production theo dõi retrieval method, source coverage, fallback, latency và guardrail;
- tài liệu này cùng notebook phản ánh chính xác điều đã triển khai, điều đã đánh giá và điều còn là backlog.

## 13. Kết luận

Phần AI hiện tại đã vượt khỏi mức “gọi LLM trả lời menu”: nó có retrieval có thể tái lập, source diagnostics, guardrail, fallback, session-scoped memory và lifecycle gắn với table session. Notebook cũng đã có bố cục chuyên nghiệp theo kiểu nghiên cứu ML/DL.

Điểm cần giữ kỷ luật nhất là phân biệt ba mức:

1. **Đã cài đặt:** RAG runtime, năm retriever, LLM optional, safety, session memory/restore.
2. **Đã có artifact đánh giá:** metric retrieval, latency, bootstrap/McNemar của snapshot hiện có.
3. **Chưa được khẳng định final:** artifact fresh và kết quả frozen-test hậu chọn của run mới, generation/human evaluation, reranker và validation production dài hạn.

Sau khi artifact được regenerate từ development selection, frozen test hậu chọn được chạy và release checklist hoàn tất, TF-IDF/BM25/dense/hybrid sẽ là một nghiên cứu retrieval có thể bảo vệ được bằng số liệu; đồng thời chatbot vẫn giữ được behavior an toàn và liên tục trong suốt phiên bàn.
