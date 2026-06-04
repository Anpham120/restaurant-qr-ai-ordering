# Git Workflow

Tai lieu nay quy dinh luong Git chuan cho du an Restaurant QR AI Ordering. Muc tieu la giup thay, Lead, thanh vien va AI agent cua tung thanh vien nhin ro: ai dang lam issue nao, code nam o nhanh nao, ket qua da bao cao chua.

## 1. Branch Model

Du an dung 3 tang nhanh:

- `main`: nhanh on dinh de demo, nop bai va deploy production.
- `develop`: nhanh tich hop code cua ca nhom.
- `issue-<number>/<github-username>-<short-task>`: nhanh ca nhan cho tung issue.

Khong push truc tiep vao `main` hoac `develop`. Moi thay doi phai di qua Pull Request.

## 2. Vai Tro Cua Tung Nhanh

### `main`

- Chi chua code da on dinh.
- Dung cho demo chinh thuc, deploy VPS va nop bao cao.
- Chi nhan code tu PR `develop` -> `main`.
- Lead `Anpham120` la nguoi review va merge cuoi cung.

### `develop`

- La nhanh tich hop tien do hang ngay cua nhom.
- Tat ca issue branches merge vao `develop`.
- Dung de test tich hop frontend, backend, AI va realtime.

### Issue branch

- Tao tu `develop`, khong tao tu `main`.
- Moi issue co mot branch rieng.
- Format bat buoc:

```bash
issue-<number>/<github-username>-<short-task>
```

Vi du:

```bash
issue-3/quanghieu1605-efcore-menu-order
issue-7/tanh2k8-customer-cart
issue-11/anpham120-rag-menu-faq
```

## 3. Luong Lam Viec Chuan Cho Thanh Vien

Bat dau issue:

```bash
git checkout develop
git pull origin develop
git checkout -b issue-<number>/<github-username>-<short-task>
```

Trong khi lam:

- Chi sua file/vung duoc ghi trong `Allowed files/areas`.
- Khong sua file/vung ghi trong `Do not touch`.
- Neu can sua API contract, shared model, config chung hoac file cua nguoi khac, phai comment hoi Lead trong issue truoc.

Hoan thanh issue:

```bash
git status
git add <changed-files>
git commit -m "feat: short description"
git push origin issue-<number>/<github-username>-<short-task>
```

Sau do tao Pull Request:

- Base branch: `develop`
- Compare branch: branch issue cua minh
- PR description phai co `Closes #<issue_number>`
- Dien day du checklist trong PR template
- Comment bao cao ket qua vao issue

## 4. Luong Merge

### Issue branch -> `develop`

Dung cho moi task hang ngay.

Dieu kien merge:

- PR dung base branch `develop`.
- PR link issue bang `Closes #<issue_number>`.
- Khong sua ngoai pham vi issue.
- Da chay test/build phu hop.
- Da comment bao cao ket qua trong issue.
- Lead hoac nguoi duoc Lead chi dinh da review.

### `develop` -> `main`

Chi thuc hien cuoi tuan hoac khi can demo.

Dieu kien merge:

- Cac issue trong milestone tuan da duoc tong hop.
- Khong con loi nghiem trong.
- Da chay test/build/integration.
- Da co bao cao tuan.
- Lead `Anpham120` merge cuoi cung.

## 5. Conventional Commits

Dung commit message ro nghia:

```bash
feat: add customer order placement api
fix: correct unavailable menu item validation
docs: add week 1 report template
test: add order service integration tests
refactor: simplify menu query service
chore: update docker compose config
```

Khong dung commit mo ho:

```bash
update
fix bug
done
new code
```

## 6. Quy Tac Conflict

- Khong tu y resolve conflict o file ngoai pham vi issue.
- Neu conflict lien quan file cua nguoi khac, comment vao issue/PR va tag Lead.
- Truoc khi mo PR, nen cap nhat branch tu `develop`:

```bash
git checkout develop
git pull origin develop
git checkout issue-<number>/<github-username>-<short-task>
git merge develop
```

Neu merge conflict qua lon, dung lai va bao Lead, khong sua doan code khong hieu.

## 7. Quy Tac Cho AI Agent

Khi moi thanh vien dung AI agent rieng, phai dua agent doc cac tai lieu sau truoc khi code:

- `README.md`
- `docs/GIT_WORKFLOW.md`
- issue duoc giao
- PR/issue lien quan neu co

AI agent chi duoc:

- Lam dung muc tieu issue.
- Sua dung vung `Allowed files/areas`.
- Bao cao neu can sua file ngoai pham vi.

AI agent khong duoc:

- Push truc tiep vao `main` hoac `develop`.
- Tu y sua API contract/shared model.
- Tu y xoa/refactor code cua thanh vien khac.
- Tu y thay doi scope issue.

## 8. Bao Cao Ket Qua Trong Issue

Truoc khi yeu cau review PR, thanh vien comment vao issue theo mau:

```text
## Bao cao ket qua
- Da lam:
- File/chuc nang da thay doi:
- Cach test:
- Anh/video demo neu co:
- Van de con ton tai:
- PR lien quan:
```

## 9. Checklist Nhanh

Truoc khi mo PR:

- [ ] Branch tao tu `develop`.
- [ ] Branch dung format `issue-<number>/<github-username>-<short-task>`.
- [ ] PR merge vao `develop`, khong merge vao `main`.
- [ ] PR co `Closes #<issue_number>`.
- [ ] Khong sua file ngoai pham vi issue.
- [ ] Da chay test/build phu hop.
- [ ] Da comment bao cao ket qua trong issue.

