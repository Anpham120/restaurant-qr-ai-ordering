# AI retrieval dev results

## Kết luận

Hybrid RRF được chọn **tạm thời trên dev** cho bước tích hợp production. Kết luận
này chưa sử dụng frozen test và không được diễn giải thành kết quả test cuối.

Corpus gồm 126 document: 91 món chính thức (bao gồm đồ uống) và 35 knowledge
document. Dev có 125 case, trong đó 110 case có expected selector để tính retrieval
quality. Frozen test có 235 case và chưa được mở.

## Kết quả chính

| Phương pháp | Hit@1 | Hit@5 | Hit@10 | MRR@5 | nDCG@5 | Forbidden@10 | p50 | p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BM25 | 0,5727 | 0,8909 | 0,9636 | 0,6798 | 0,4991 | 0 | 1,06 ms | 1,61 ms |
| Dense E5 | 0,6455 | 0,9091 | 0,9636 | 0,7415 | 0,5838 | 0 | 13,28 ms | 17,74 ms |
| Hybrid RRF | **0,6545** | **0,9364** | **1,0000** | **0,7661** | **0,6100** | **0** | 15,07 ms | 18,63 ms |

So với BM25, hybrid tăng MRR@5 `+0,0857` (Holm p = `0,0204`), tăng
nDCG@5 `+0,0906` (Holm p = `0,00030`) và có rank-biserial effect `0,4481`
(Holm p = `0,0203`). So với dense E5, điểm hybrid cao hơn nhưng các kiểm định
quality chưa có ý nghĩa sau hiệu chỉnh Holm; latency median tăng khoảng `1,38 ms`.

## Protocol

- Git SHA: `afa3a6e13b852f9213e08add236750496b4d8323`, worktree sạch.
- Encoder: `intfloat/multilingual-e5-small`, revision
  `fd1525a9fd15316a2d503bf26ab031a61d056e98`, 384 chiều, normalized.
- Mỗi target warm-up tối đa 5 query; mỗi query đo 7 lần và lấy median.
- Thứ tự case và phương pháp được deterministic shuffle với seed `20260713`.
- Bootstrap 10.000 vòng; McNemar exact; Wilcoxon signed-rank; p-value được
  Holm-Bonferroni trong từng test family qua ba cặp phương pháp.
- Frozen test chỉ được kiểm tra SHA-256, `frozen_test_opened=false`.

Artifact máy đọc nằm tại
`ai/evaluation/results/dev_retrieval_summary.v1.json`.
