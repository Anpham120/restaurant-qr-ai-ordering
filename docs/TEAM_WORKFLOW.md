# Team Workflow

## 1. Team Ownership

- `Anpham120`: Lead, Docs, DevOps, Testing, Integration, AI.
- `buidaoducanh1210`: Backend.
- `quanghieu1605`: Backend.
- `Tanh2k8-123`: Frontend.
- `totototototoads`: Frontend.

Moi tuan moi thanh vien co mot issue chinh. Moi issue co mot branch, mot PR va mot bao cao ket qua.

## 2. AI Agent Rules

Moi thanh vien co the dung AI agent rieng, nhung agent phai doc:

- `README.md`
- `docs/PROJECT_CONTEXT.md`
- `docs/GIT_WORKFLOW.md`
- `docs/TEAM_WORKFLOW.md`
- `docs/API_CONTRACT.md`
- Issue duoc giao

AI agent duoc phep:

- Lam dung muc tieu issue.
- Sua dung vung `Allowed Files / Areas`.
- Tao test va tai lieu trong pham vi issue.
- Bao cao neu can doi contract hoac scope.

AI agent khong duoc phep:

- Push truc tiep vao `main` hoac `develop`.
- Sua ngoai `Allowed Files / Areas`.
- Sua vung `Do Not Touch`.
- Doi API contract, status name, route, entity chung ma khong hoi Lead.
- Xoa/refactor code cua thanh vien khac.
- Tu y them feature moi ngoai issue.

## 3. Issue Standard

Moi issue phai co:

- Assignee.
- Milestone.
- Required branch.
- Goal.
- Context.
- Scope of work.
- Step-by-step tasks.
- Allowed files/areas.
- Do not touch.
- Acceptance criteria.
- Required test/verification.
- Evidence required.
- AI reviewer notes.

Thay hoac AI reviewer co the dung cac muc tren de so sanh issue, commit va PR.

## 4. Pull Request Standard

Moi PR phai:

- Target vao `develop`.
- Link issue bang `Closes #<issue_number>`.
- Co commit message ro rang.
- Co test/build evidence.
- Khong sua ngoai scope.
- Co comment bao cao ket qua trong issue truoc khi review.

Lead review truoc khi merge. Neu PR vuot scope, Lead co quyen yeu cau tach PR hoac rollback phan vuot scope.

## 5. Reporting Standard

Khi xong issue, thanh vien comment vao issue:

```text
## Bao cao ket qua
- Issue:
- Branch:
- PR:
- Commit chinh:
- Da lam:
- File/chuc nang da thay doi:
- Cach test:
- Bang chung:
- Phan chua lam / gioi han:
- Co sua ngoai scope khong:
```

Cuoi moi tuan Lead tong hop vao `docs/reports/week-N-report.md`.

## 6. Contract Change Rule

Neu can doi mot trong cac muc sau, phai comment hoi Lead:

- API endpoint.
- Request/response DTO.
- Enum/status name.
- Route frontend.
- Shared type.
- Database field dung chung.
- SignalR event payload.

Khong duoc tu y doi contract chi de lam UI hoac backend nhanh hon.

