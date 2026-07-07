# TLH_INDEX.md

## Purpose

이 파일은 Claude, Codex, TeamLead, 또는 다른 AI agent가 `TLH_CANON.md`를 한 번에 전부 읽지 않도록 돕는 라우터다.

먼저 이 파일을 읽고, 현재 작업에 필요한 CANON-ID만 선택한다.

전체 `TLH_CANON.md`를 읽지 않는다.
필요한 섹션만 읽는다.

---

## Read Protocol

```text
1. 먼저 TLH_INDEX.md를 읽는다.
2. 현재 작업 유형을 판단한다.
3. 아래 routing table에서 필요한 CANON-ID를 고른다.
4. TLH_CANON.md에서 해당 CANON-ID 섹션만 읽는다.
5. 코드 작업이 필요한 경우 Serena로 관련 코드 파일과 symbol을 찾는다.
6. 작업 결과는 필요한 경우 Obsidian vault note로 남긴다.
```

---

## Core Canon Sections

```text
CANON-000 — Project Status.
CANON-010 — One Sentence Definition.
CANON-020 — Boundary With AI_WORKFLOW_KIT.
CANON-030 — Core Problem.
CANON-040 — Non-Goals.
```

처음 TLH를 이해해야 한다면 위 다섯 섹션만 먼저 읽는다.

---

## If Task Is Project Orientation

Read.

```text
CANON-000.
CANON-010.
CANON-020.
CANON-030.
CANON-040.
CANON-930.
```

Use when.

```text
새 세션 시작.
프로젝트 방향 확인.
AICO와 TLH 차이 확인.
AI_WORKFLOW_KIT과 TLH 경계 확인.
```

---

## If Task Is Obsidian Vault Design

Read.

```text
CANON-100.
CANON-110.
CANON-120.
CANON-130.
CANON-140.
CANON-700.
CANON-710.
```

Use when.

```text
vault 구조 생성.
_AI_README 작성.
_CURRENT_STATE 작성.
_AI_INDEX 작성.
AI_CONTEXT_PACK 설계.
Graph-ready note 설계.
```

---

## If Task Is TeamLead Design

Read.

```text
CANON-200.
CANON-210.
CANON-220.
CANON-300.
CANON-310.
CANON-320.
```

Use when.

```text
TeamLead prompt 작성.
질문 생성 로직 설계.
작업 분해 로직 설계.
topology routing 설계.
loop decision 설계.
```

---

## If Task Is Worker / TaskCard Schema

Read.

```text
CANON-220.
CANON-230.
CANON-240.
CANON-300.
```

Use when.

```text
TaskCard schema 구현.
WorkerResult schema 구현.
worker prompt 작성.
worker dispatch 설계.
```

---

## If Task Is MergeHarness

Read.

```text
CANON-240.
CANON-250.
CANON-260.
CANON-270.
CANON-330.
CANON-400.
CANON-410.
```

Use when.

```text
WorkerResult 통합.
MergePacket 생성.
AccumulatedArtifact 갱신.
continuity check.
minimality check.
```

---

## If Task Is LoopController

Read.

```text
CANON-260.
CANON-270.
CANON-300.
CANON-310.
CANON-320.
CANON-330.
CANON-400.
```

Use when.

```text
다음 slice 결정.
loop stop 조건 설계.
targeted verifier 판단.
failed_to_merge 처리.
```

---

## If Task Is FinalPacket / Handoff

Read.

```text
CANON-280.
CANON-290.
CANON-600.
CANON-610.
CANON-910.
CANON-920.
```

Use when.

```text
FinalPacket 생성.
CodexPrompt 생성.
ClaudePrompt 생성.
RTK ExecutionHint 포함.
검증/보고 형식 작성.
```

---

## If Task Is Serena Context Integration

Read.

```text
CANON-500.
CANON-510.
CANON-520.
CANON-220.
CANON-290.
```

Use when.

```text
ContextRequest 설계.
ContextPacket 설계.
Serena MCP read/search 연동.
repo symbol context를 TaskCard에 연결.
Codex/Claude handoff에 target context 포함.
```

Do not.

```text
Serena edit/refactor/write를 MVP에 넣지 말 것.
Serena를 TLH 본체로 만들지 말 것.
```

---

## If Task Is RTK / Execution Efficiency

Read.

```text
CANON-600.
CANON-610.
CANON-290.
```

Use when.

```text
CodexPrompt에 command efficiency rule 추가.
ExecutionHint schema 구현.
큰 shell output 방지 규칙 작성.
```

Do not.

```text
RTK global hook을 TLH MVP에 넣지 말 것.
모든 shell command에 RTK를 강제하지 말 것.
```

---

## If Task Is Ponytail / Overbuild Control

Read.

```text
CANON-400.
CANON-410.
CANON-920.
```

Use when.

```text
TaskCard 과잉 제거.
worker 호출 수 줄이기.
loop 중단 판단.
FinalPacket 압축.
문서 과잉 방지.
```

---

## If Task Is Graph-ready Memory

Read.

```text
CANON-130.
CANON-140.
CANON-700.
CANON-710.
CANON-260.
CANON-250.
```

Use when.

```text
typed links 설계.
_GRAPH_INDEX.json 생성.
_GRAPH_INDEX.md 생성.
graph traversal 기반 context pack 생성.
provenance 추적.
```

---

## If Task Is MVP Implementation

Read.

```text
CANON-800.
CANON-810.
CANON-820.
CANON-900.
CANON-910.
CANON-920.
```

Also read as needed.

```text
CANON-100.
CANON-200.
CANON-220.
CANON-240.
CANON-250.
CANON-260.
CANON-320.
```

Use when.

```text
repo 초기 생성.
파일 구조 생성.
CLI 구현.
MVP scope 확인.
성공/실패 조건 확인.
```

---

## If Task Is Preventing Scope Creep

Read.

```text
CANON-020.
CANON-040.
CANON-400.
CANON-800.
CANON-920.
```

Use when.

```text
TLH가 AI_WORKFLOW_KIT 기능을 중복하려 할 때.
GUI/대시보드/MCP write 같은 기능이 끼어들 때.
문서가 과하게 늘어날 때.
worker/loop가 과하게 늘어날 때.
```

---

## Do Not Read First

처음부터 읽지 말 것.

```text
raw worker outputs.
old AICO documents.
superseded notes.
archived runs.
large logs.
entire TLH_CANON.md.
AI_WORKFLOW_KIT 설치 문서.
```

필요할 때만 읽을 것.

---

## Serena Usage Rule

Serena는 Markdown 정본 탐색용이 아니라 코드 context 탐색용이다.

문서 정본은 CANON-ID로 찾는다.
코드 구현부는 Serena로 찾는다.

Use Serena for.

```text
project overview.
find_symbol.
find_references.
read_symbol.
summarize file.
```

Do not use Serena for.

```text
editing code directly in MVP.
refactoring directly in MVP.
writing TLH canon.
replacing AI_INDEX routing.
```

---

## AI_WORKFLOW_KIT Boundary Reminder

다음은 TLH 정본에 중복 구현하지 않는다.

```text
전역 Codex AGENTS.md 보강.
전역 Claude CLAUDE.md 보강.
공용 skills 설치.
repo별 candidate 적용 스크립트.
RTK global hook 운영.
Repomix 설치.
Serena 설치 정책.
전역 AI workflow 운영 규칙.
```

이것들은 AI_WORKFLOW_KIT의 역할이다.

TLH는 그 위에서 실행되는 별도 프로젝트다.

---

## Minimum Read Sets

### 빠른 방향 확인.

```text
CANON-000.
CANON-010.
CANON-020.
CANON-930.
```

### MVP 구현 시작.

```text
CANON-800.
CANON-810.
CANON-820.
CANON-900.
CANON-910.
```

### 핵심 schema 구현.

```text
CANON-220.
CANON-240.
CANON-250.
CANON-260.
CANON-270.
```

### loop 구현.

```text
CANON-310.
CANON-320.
CANON-330.
CANON-400.
```

### vault 구현.

```text
CANON-100.
CANON-110.
CANON-120.
CANON-130.
CANON-700.
```

---

## Final Instruction To AI Agents

이 index를 먼저 읽어라.
현재 작업과 관련된 CANON-ID만 골라라.
`TLH_CANON.md` 전체를 처음부터 끝까지 읽지 마라.
코드 작업이 필요하면 Serena로 관련 파일과 symbol만 찾는다.
작업 결과가 TLH 정본을 바꾸는 경우, 변경한 CANON-ID와 이유를 보고한다.
