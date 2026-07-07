# TLH_CANON.md

## CANON-000 — Project Status

TLH는 AICO를 폐기한 뒤 새로 시작하는 별도 프로젝트다.

AICO는 no-call, approval gate, safety, policy, 문서 검증 중심으로 흘렀고, 사용자의 실제 목표와 어긋났다.

TLH는 AICO의 후속 버전이 아니다.
TLH는 새 프로젝트다.

TLH는 다음을 목표로 한다.

```text
큰 작업을 한 번에 처리하지 않는다.
TeamLead가 작업을 나눈다.
Worker들이 조각을 처리한다.
MergeHarness가 결과를 합친다.
AccumulatedArtifact에 조각을 붙인다.
LoopController가 다음 조각을 결정한다.
Obsidian vault가 AI-readable 작업 기억층이 된다.
최종적으로 Claude/Codex가 바로 쓸 수 있는 FinalPacket을 만든다.
```

---

## CANON-010 — One Sentence Definition

TLH는 Obsidian vault를 AI-readable 작업 기억층으로 사용하고, TeamLead agent가 사용자 요청을 질문으로 명확히 한 뒤, 큰 목표를 TaskCard로 분해하여 worker에게 배분하고, WorkerResult를 MergePacket으로 통합하며, AccumulatedArtifact에 순차적으로 붙이는 루프를 반복하여, 최종적으로 사용자 또는 Claude/Codex가 바로 사용할 FinalPacket을 만드는 팀장 중심 작업분배·결과통합·점진 조립 하네스다.

---

## CANON-020 — Boundary With AI_WORKFLOW_KIT

TLH는 AI_WORKFLOW_KIT과 역할이 다르다.

AI_WORKFLOW_KIT은 전역 운영층이다.

```text
AI_WORKFLOW_KIT의 역할.
- Codex 전역 AGENTS.md 보강.
- Claude 전역 CLAUDE.md 보강.
- Codex/Claude 공용 skills.
- Ponytail, canon-router, handoff-pack, loop-audit, context-pack, reentry-summary.
- Serena/RTK/Repomix 사용 정책.
- repo별 candidate 적용 도구.
```

TLH는 프로젝트 본체다.

```text
TLH의 역할.
- Obsidian-first AI-readable memory.
- TeamLead orchestration.
- TaskCard generation.
- Worker dispatch.
- WorkerResult collection.
- MergePacket creation.
- AccumulatedArtifact update.
- Slice-and-attach loop.
- Graph-ready vault.
- FinalPacket / CodexPrompt / ClaudePrompt generation.
```

따라서 TLH 정본에는 AI_WORKFLOW_KIT의 전역 설치, skill 설치, 전역 AGENTS/CLAUDE 보강 내용을 반복하지 않는다.

TLH는 AI_WORKFLOW_KIT을 사용할 수 있지만, AI_WORKFLOW_KIT 자체가 TLH의 본체는 아니다.

---

## CANON-030 — Core Problem

단일 LLM에게 큰 작업을 한 번에 맡기면 다음 문제가 생긴다.

```text
출력 토큰 한계에 막힌다.
긴 작업이 누락된다.
작업의 앞부분과 뒷부분이 연결되지 않는다.
Claude/Codex가 같은 맥락을 반복해서 읽는다.
사용자가 계속 판단해야 한다.
worker를 여러 명 써도 결과가 잘 합쳐지지 않는다.
문서와 로그가 쌓이지만 다음 AI가 어디부터 읽어야 할지 모른다.
```

TLH가 해결하려는 문제는 “AI를 더 많이 부르는 것”이 아니다.

핵심 질문은 다음이다.

```text
어떻게 잘 나눌 것인가.
어떻게 필요한 context만 줄 것인가.
어떻게 worker 결과를 회수할 것인가.
어떻게 결과를 기존 산출물에 붙일 것인가.
어떻게 루프로 점점 키울 것인가.
어떻게 Claude/Codex가 바로 실행하게 만들 것인가.
```

---

## CANON-040 — Non-Goals

TLH 초기 버전에서 하지 않는다.

```text
GUI.
대시보드.
Obsidian plugin 개발.
Obsidian MCP write 권한.
Serena edit/refactor/write.
RTK global hook 강제.
Claude/Codex 자동 실행.
GitHub 자동 PR/merge.
worker 직접 파일 수정.
worker끼리 자유 토론.
대형 벤치마크.
no-call safety harness.
approval gate 중심 구조.
긴 문서 반복 생산.
```

TLH는 실행 자동화 플랫폼이 아니라, 작업을 나누고, 붙이고, 이어받게 만드는 하네스다.

---

## CANON-100 — Obsidian-first Memory

TLH는 Obsidian vault를 처음부터 중심 기억층으로 사용한다.

Obsidian은 사람용 예쁜 노트앱이 아니라, AI들이 읽는 Markdown 기반 작업 기억층이다.

```text
Obsidian vault.
- 현재 상태를 저장한다.
- active run을 저장한다.
- TaskCard를 저장한다.
- WorkerResult를 저장한다.
- MergePacket을 저장한다.
- AccumulatedArtifact를 저장한다.
- FoldedSummary를 저장한다.
- FinalPacket을 저장한다.
- Pattern과 Failure를 저장한다.
- 다음 AI가 이어받을 re-entry 문서를 저장한다.
```

Python engine은 Obsidian vault를 읽고 쓴다.
TeamLead와 worker들은 vault의 AI-readable note를 읽는다.

---

## CANON-110 — Vault Structure

초기 vault 구조는 다음을 기본으로 한다.

```text
vault/
  _AI_README.md
  _CURRENT_STATE.md
  _AI_INDEX.md
  _GRAPH_INDEX.json
  _GRAPH_INDEX.md

  00_Inbox/
  01_Runs/
  02_TaskCards/
  03_WorkerResults/
  04_MergePackets/
  05_Artifacts/
  06_Handoff/
  07_Patterns/
  08_Failures/
  09_Decisions/
  10_ContextPackets/
  11_MinimalityChecks/
```

핵심 파일은 다음이다.

```text
_AI_README.md.
AI가 이 vault를 어떻게 읽어야 하는지 설명한다.

_CURRENT_STATE.md.
현재 프로젝트 상태와 active run을 알려준다.

_AI_INDEX.md.
AI가 필요한 문서를 찾는 라우터다.

_GRAPH_INDEX.json.
note 사이의 node/edge 관계를 기계가 읽는 형태로 저장한다.

_GRAPH_INDEX.md.
graph 관계를 사람이 읽기 쉬운 형태로 보여준다.
```

---

## CANON-120 — AI-readable Note Rules

모든 주요 note는 AI-readable해야 한다.

필수 frontmatter는 다음이다.

```yaml
type:
id:
run_id:
status:
created:
updated:
read_priority:
ai_readable: true
supersedes:
superseded_by:
source:
```

status는 다음 중 하나를 사용한다.

```text
active.
done.
waiting.
stale.
superseded.
archived.
```

AI-readable note는 다음 섹션을 가져야 한다.

```text
Purpose.
Current State.
Inputs.
Outputs.
Links.
Do Next.
Do Not.
```

AI에게 중요한 규칙은 다음이다.

```text
최신 상태는 _CURRENT_STATE.md를 우선한다.
긴 로그보다 FoldedSummary를 우선한다.
raw worker output은 기본으로 읽지 않는다.
superseded 문서는 근거 추적이 필요할 때만 읽는다.
```

---

## CANON-130 — Graph-ready Memory

TLH vault는 단순 Markdown 폴더가 아니라 graph-ready AI memory다.

모든 note는 node로 취급할 수 있어야 한다.
note 사이의 관계는 typed edge로 명시한다.

권장 edge type은 다음이다.

```text
DEPENDS_ON.
PRODUCES.
MERGED_INTO.
UPDATES.
SUPERSEDES.
CONFLICTS_WITH.
DERIVED_FROM.
VALIDATES.
DROPPED_BY.
HANDOFF_TO.
USES_CONTEXT.
USES_EXECUTION_HINT.
```

예시.

```markdown
## Graph Links

- DEPENDS_ON: [[ContextPacket-CR001]]
- PRODUCES: [[WorkerResult-T1-Gemma01]]
- MERGED_INTO: [[MergePacket-M1]]
- UPDATES: [[AccumulatedArtifact-v2]]
```

Python engine은 이 관계를 읽어 `_GRAPH_INDEX.json`을 생성한다.

---

## CANON-140 — AI Context Pack

AI가 vault 전체를 읽게 하면 안 된다.

TLH는 active task에 필요한 note만 모아 `AI_CONTEXT_PACK.md`를 생성할 수 있어야 한다.

포함 대상은 다음이다.

```text
_CURRENT_STATE.
Active Run.
Current AccumulatedArtifact.
Latest MergePacket.
Current TaskCards.
Relevant ContextPackets.
Relevant Patterns.
Relevant Failures.
Current Do Not list.
```

제외 대상은 다음이다.

```text
old raw worker outputs.
archived AICO documents.
superseded canon sections.
large logs.
unrelated past runs.
```

---

## CANON-200 — TeamLead

TeamLead는 TLH의 작업 관리자이자 통합자다.

TeamLead는 답변자가 아니다.

TeamLead의 책임은 다음이다.

```text
사용자 요청 이해.
필요한 질문 생성.
사용자 답변 반영.
작업 구체화.
TaskCard 생성.
worker 배분.
WorkerResult 회수.
MergePacket 생성.
AccumulatedArtifact 갱신.
FoldedSummary 갱신.
LoopController와 함께 다음 slice 결정.
FinalPacket 생성.
CodexPrompt / ClaudePrompt 생성.
```

TeamLead의 금지 사항은 다음이다.

```text
worker 없이 최종 답변 작성 금지.
TaskCard 없이 worker 호출 금지.
worker 결과 충돌 숨기기 금지.
AccumulatedArtifact 무시 금지.
모든 것을 한 번에 완성하려 하기 금지.
raw output을 정본으로 승격 금지.
```

TLH를 실행했다면 TeamLead 단독 처리는 허용하지 않는다.

---

## CANON-210 — Clarification

TeamLead는 사용자 요청을 바로 작업으로 바꾸지 않는다.

먼저 필요한 질문을 한다.

질문 원칙은 다음이다.

```text
최대 5개.
실행에 필요한 질문만.
취향 질문보다 작업 범위 질문 우선.
답 없이 진행 가능한 것은 묻지 않음.
질문 후 바로 TaskCard 생성으로 이어짐.
```

질문 예시는 다음이다.

```text
목표 산출물은 무엇인가.
Claude/Codex에게 넘길 지시문이 필요한가.
대상 repo나 문서가 있는가.
이번 작업에서 금지할 범위가 있는가.
최종 결과는 사람이 읽는 문서인가, agent가 실행할 패킷인가.
```

---

## CANON-220 — TaskCard

TaskCard는 worker에게 줄 작업 단위다.

모든 worker 호출은 TaskCard를 입력으로 받아야 한다.

TaskCard schema는 다음이다.

```json
{
  "task_id": "",
  "run_id": "",
  "loop_index": 0,
  "title": "",
  "goal": "",
  "worker_role": "",
  "input_context": [],
  "expected_output": "",
  "attach_point": "",
  "dependencies": [],
  "merge_key": "",
  "topology_hint": ""
}
```

TaskCard 검사 기준은 다음이다.

```text
Solvability.
이 worker가 처리할 수 있는 크기인가.

Completeness.
모든 TaskCard를 합치면 원래 목표를 덮는가.

Non-redundancy.
같은 작업을 중복시키고 있지 않은가.

Attachability.
결과가 AccumulatedArtifact의 어디에 붙는지 명확한가.
```

---

## CANON-230 — Worker

Worker는 TaskCard 하나를 처리한다.

worker는 다음을 하지 않는다.

```text
사용자에게 직접 질문.
다른 worker 호출.
최종 결론 작성.
파일 수정.
shell 실행.
GitHub 작업.
vault 정본 직접 수정.
```

worker는 다음만 한다.

```text
TaskCard를 읽는다.
필요 context를 읽는다.
WorkerResult를 생성한다.
```

초기 worker 역할은 다음 정도로 제한한다.

```text
analyst.
planner.
builder.
critic.
tester.
compressor.
continuity_checker.
```

역할은 고정 직책이 아니라 TaskCard마다 부여되는 임시 역할이다.

---

## CANON-240 — WorkerResult

WorkerResult는 worker가 제출하는 구조화 결과다.

schema는 다음이다.

```json
{
  "task_id": "",
  "worker_id": "",
  "summary": "",
  "findings": [],
  "risks": [],
  "assumptions": [],
  "open_questions": [],
  "attach_notes": []
}
```

WorkerResult는 자유문 장문 보고서가 아니다.
MergeHarness가 읽고 합칠 수 있는 구조화 결과여야 한다.

WorkerResult note는 `03_WorkerResults/`에 저장한다.

---

## CANON-250 — MergePacket

MergePacket은 TeamLead가 WorkerResult를 통합한 결과다.

schema는 다음이다.

```json
{
  "merge_id": "",
  "run_id": "",
  "loop_index": 0,
  "merged_tasks": [],
  "confirmed_points": [],
  "alternatives": [],
  "conflicts": [],
  "dropped_items": [],
  "attach_success": false,
  "updated_artifact_version": 0,
  "continuity_check": "",
  "minimality": {}
}
```

MergeHarness 규칙은 다음이다.

```text
공통 의견은 confirmed_points로 올린다.
다른 의견은 alternatives로 보존한다.
충돌은 conflicts로 기록한다.
근거 없는 주장은 dropped_items로 버린다.
중복은 제거한다.
기존 산출물에 붙지 않는 내용은 final에 넣지 않는다.
사용자 결정 항목은 최대 3개만 남긴다.
```

MergePacket note는 `04_MergePackets/`에 저장한다.

---

## CANON-260 — AccumulatedArtifact

AccumulatedArtifact는 현재까지 누적된 산출물이다.

TLH의 핵심은 모든 새 조각을 AccumulatedArtifact에 붙이는 것이다.

핵심 원칙은 다음이다.

```text
Every slice must attach to the accumulated artifact.
```

AccumulatedArtifact는 다음을 포함한다.

```text
현재 버전.
완료된 slices.
현재 통합 초안.
열린 conflicts.
다음 attach points.
최근 MergePacket 링크.
FoldedSummary 링크.
```

AccumulatedArtifact note는 `05_Artifacts/`에 저장한다.

---

## CANON-270 — FoldedSummary

FoldedSummary는 긴 히스토리를 접은 요약이다.

worker에게 전체 로그를 주지 않는다.
worker에게는 현재 task에 필요한 folded context만 준다.

FoldedSummary는 다음을 포함한다.

```text
현재까지 완료된 것.
현재 열린 conflict.
지켜야 할 constraints.
다음 attach point.
이번 loop에서 필요한 context.
읽지 말아야 할 raw history.
```

FoldedSummary는 loop마다 갱신한다.

---

## CANON-280 — FinalPacket

FinalPacket은 사용자 또는 Claude/Codex가 바로 사용할 최종 산출물이다.

필수 섹션은 다음이다.

```text
Goal.
Current State.
Confirmed Assumptions.
Scope.
Out of Scope.
Execution Steps.
Risks.
Verification.
Handoff Prompt.
User Decision Points.
```

FinalPacket은 설명문이 아니라 실행 가능한 패킷이어야 한다.

---

## CANON-290 — Handoff Prompts

TLH는 필요하면 ClaudePrompt와 CodexPrompt를 생성한다.

Handoff prompt는 다음을 포함한다.

```text
목표.
현재 상태.
대상 파일 또는 문서.
범위.
금지 범위.
실행 단계.
검증 방법.
보고 형식.
사용할 context pack.
```

HandoffPrompt는 `06_Handoff/`에 저장한다.

---

## CANON-300 — Topology Routing

TeamLead는 작업 구조에 따라 topology를 선택한다.

초기 topology는 다음만 지원한다.

```text
parallel.
독립적인 분석 작업에 사용한다.

sequential_attach.
긴 결과물을 a → b → c로 붙일 때 사용한다.

hybrid.
병렬 분석 후 순차 통합할 때 사용한다.
```

예시는 다음이다.

```text
repo 리뷰.
문서, 코드, 테스트, 구조를 병렬 분석한 뒤 merge한다.

긴 정본 작성.
outline → section A → section B attach → section C attach 순서로 진행한다.

Claude/Codex 지시문 생성.
분석, 계획, 위험, 검증을 병렬로 받고 handoff prompt를 순차 작성한다.
```

---

## CANON-310 — Slice-and-Attach Loop

TLH는 큰 결과물을 한 번에 만들지 않는다.

큰 목표 A는 a, b, c, d로 나눈다.

```text
a 생성.
a 검토 및 정리.
b 생성.
a+b 통합.
c 생성.
a+b+c 통합.
d 생성.
a+b+c+d 통합.
최종 A 완성.
```

각 slice는 반드시 기존 AccumulatedArtifact에 붙어야 한다.

Loop 단계는 다음이다.

```text
Plan Next Slice.
Create TaskCards.
Dispatch Workers.
Collect WorkerResults.
Merge Into Artifact.
Check Continuity.
Fold Context.
Decide Next.
```

---

## CANON-320 — LoopController

LoopController는 다음 action 중 하나를 결정한다.

```text
next_slice.
targeted_verifier.
user_question_needed.
stop_and_finalize.
failed_to_merge.
```

LoopController가 멈춰야 하는 조건은 다음이다.

```text
새 loop가 실질적 새 정보를 만들지 않음.
worker 결과가 반복됨.
conflict가 줄지 않음.
FinalPacket 생성이 이미 가능함.
사용자 결정 없이는 진행할 수 없음.
```

LoopController는 무한 반복을 막는다.

---

## CANON-330 — Continuity Check

Continuity check는 새 결과가 기존 AccumulatedArtifact에 붙었는지 확인한다.

검사 항목은 다음이다.

```text
attach_point가 명확한가.
이전 slice와 충돌하지 않는가.
같은 내용을 반복하지 않는가.
새 정보가 있는가.
최종 산출물 방향과 맞는가.
```

continuity check가 실패하면 다음 중 하나를 선택한다.

```text
targeted_verifier.
rework_taskcard.
drop_unattached_result.
ask_user.
```

---

## CANON-400 — Ponytail Minimality

Ponytail은 TLH의 overbuild brake다.

TLH는 worker, loop, 문서, schema가 과하게 늘어나는 것을 막아야 한다.

Ponytail check 대상은 다음이다.

```text
TaskCard.
WorkerResult.
MergePacket.
Loop decision.
FinalPacket.
HandoffPrompt.
```

Ponytail 질문은 다음이다.

```text
이 TaskCard가 꼭 필요한가.
다른 TaskCard와 합칠 수 있는가.
새 worker 호출이 필요한가.
이 loop가 새 정보를 만드는가.
이 문서가 정본을 흐리게 하지 않는가.
FinalPacket이 너무 길지 않은가.
사용자 결정 항목이 3개를 넘는가.
```

Ponytail은 검증을 줄이는 도구가 아니다.
Ponytail은 과잉을 줄이는 도구다.

---

## CANON-410 — MinimalityCheck

MinimalityCheck schema는 다음이다.

```json
{
  "check_id": "",
  "target_type": "task_cards | merge_packet | final_packet | loop",
  "dropped": [],
  "merged": [],
  "deferred": [],
  "kept": [],
  "reason": ""
}
```

MinimalityCheck note는 `11_MinimalityChecks/`에 저장한다.

---

## CANON-500 — Serena MCP

Serena MCP는 TLH의 본체가 아니다.

Serena는 코드 context retrieval layer다.

Serena의 역할은 다음이다.

```text
repo 전체를 prompt에 붙이지 않게 한다.
필요한 symbol, file, reference만 가져온다.
TeamLead가 코드 관련 TaskCard를 만들 때 ContextPacket을 생성하게 돕는다.
Codex/Claude handoff에 정확한 target context를 넣는다.
```

초기 TLH에서는 Serena live integration을 필수로 하지 않는다.
먼저 ContextRequest와 ContextPacket 계약을 만든다.

Serena 사용은 read/search/context retrieval 중심이다.
Serena edit/refactor/write는 초기에는 금지한다.

---

## CANON-510 — ContextRequest

ContextRequest는 TeamLead가 코드 context가 필요할 때 생성한다.

schema는 다음이다.

```json
{
  "request_id": "",
  "tool": "serena",
  "purpose": "",
  "query_type": "",
  "target": "",
  "output": "ContextPacket"
}
```

query_type 예시는 다음이다.

```text
project_overview.
find_symbol.
find_references.
read_symbol.
summarize_file.
risk_area_scan.
```

---

## CANON-520 — ContextPacket

ContextPacket은 Serena나 다른 context tool의 결과를 TLH가 읽을 수 있게 접은 결과다.

schema는 다음이다.

```json
{
  "context_id": "",
  "source": "serena",
  "summary": "",
  "relevant_files": [],
  "relevant_symbols": [],
  "references": [],
  "risks": [],
  "attach_to_tasks": []
}
```

ContextPacket note는 `10_ContextPackets/`에 저장한다.

raw tool output은 기본으로 정본에 넣지 않는다.

---

## CANON-600 — RTK

RTK는 TLH의 본체가 아니다.

RTK는 Claude/Codex 실행 단계에서 shell command output과 token 낭비를 줄이는 execution-side efficiency layer다.

TLH 안에서는 RTK를 직접 강제하지 않는다.

TLH는 FinalPacket이나 CodexPrompt에 ExecutionHint로 다음 규칙을 넣을 수 있다.

```text
전체 파일 cat 금지.
긴 git diff 원문 덤프 금지.
긴 테스트 로그 전체 덤프 금지.
가능하면 targeted query 사용.
RTK 사용 가능하면 큰 출력에만 사용.
```

---

## CANON-610 — ExecutionHint

ExecutionHint schema는 다음이다.

```json
{
  "target": "codex | claude",
  "rtk_recommended": false,
  "reason": "",
  "command_efficiency_rules": []
}
```

ExecutionHint는 `06_Handoff/` 또는 FinalPacket 내부에 포함한다.

---

## CANON-700 — Graph Index

TLH는 Obsidian links만 믿지 않는다.

Python engine은 graph-ready note의 frontmatter와 typed links를 읽어 `_GRAPH_INDEX.json`을 생성한다.

예시.

```json
{
  "nodes": [
    {
      "id": "T1",
      "type": "task_card",
      "path": "02_TaskCards/T1.md",
      "status": "done"
    }
  ],
  "edges": [
    {
      "from": "T1",
      "to": "WR-T1-01",
      "type": "PRODUCES"
    }
  ]
}
```

Graph index의 목적은 다음이다.

```text
현재 task 주변 context 찾기.
패턴 재사용.
실패 원인 추적.
충돌 추적.
handoff provenance 추적.
```

---

## CANON-710 — Graph Retrieval Rule

TeamLead는 vault 전체를 검색하지 않는다.

TeamLead retrieval 순서는 다음이다.

```text
1. _CURRENT_STATE.md.
2. active run note.
3. current AccumulatedArtifact.
4. latest MergePacket.
5. current TaskCards.
6. linked ContextPackets.
7. linked Patterns.
8. linked Failures.
```

기본 원칙은 current node 주변 context만 읽는 것이다.

---

## CANON-800 — MVP Scope

TLH MVP의 목표는 하나다.

```text
Obsidian vault 안에서 하나의 사용자 요청이
질문 → TaskCard → WorkerResult → MergePacket → AccumulatedArtifact → FinalPacket
으로 자라는 것을 증명한다.
```

MVP에 포함한다.

```text
Obsidian vault init.
_AI_README / _CURRENT_STATE / _AI_INDEX 생성.
TeamLead 질문 생성.
사용자 답변 반영.
TaskCard 생성.
Gemma worker 실제 호출.
WorkerResult 저장.
MergePacket 생성.
AccumulatedArtifact 갱신.
FoldedSummary 생성.
Ponytail MinimalityCheck.
FinalPacket 생성.
CodexPrompt 생성.
_GRAPH_INDEX 생성.
```

MVP에 포함하지 않는다.

```text
GUI.
대시보드.
Obsidian plugin.
Obsidian MCP write.
Serena live edit/write.
RTK global hook.
Claude/Codex 자동 실행.
GitHub 자동 PR/merge.
대형 벤치마크.
```

---

## CANON-810 — MVP CLI

MVP CLI 초안은 다음이다.

```powershell
python -m tlh init
python -m tlh run --mission "vault\00_Inbox\mission.md"
python -m tlh answer --run "<run_id>" --answers "vault\01_Runs\<run_id>_answers.md"
python -m tlh dispatch --run "<run_id>"
python -m tlh merge --run "<run_id>"
python -m tlh loop --run "<run_id>"
python -m tlh finalize --run "<run_id>"
```

각 명령은 vault note와 machine-readable 파일을 함께 생성한다.

---

## CANON-820 — MVP File Structure

초기 repo 구조는 다음이다.

```text
tlh/
  engine/
    __init__.py
    team_lead.py
    task_card.py
    worker_pool.py
    gemma_client.py
    dispatcher.py
    merge_harness.py
    loop_controller.py
    ponytail_checker.py
    graph_index.py
    packet_writer.py

  prompts/
    team_lead_clarify.v1.md
    team_lead_decompose.v1.md
    worker_base.v1.md
    worker_builder.v1.md
    worker_critic.v1.md
    merge_harness.v1.md
    continuity_check.v1.md
    final_packet.v1.md
    codex_prompt.v1.md

  vault/
    _AI_README.md
    _CURRENT_STATE.md
    _AI_INDEX.md
    _GRAPH_INDEX.json
    _GRAPH_INDEX.md
    00_Inbox/
    01_Runs/
    02_TaskCards/
    03_WorkerResults/
    04_MergePackets/
    05_Artifacts/
    06_Handoff/
    07_Patterns/
    08_Failures/
    09_Decisions/
    10_ContextPackets/
    11_MinimalityChecks/

  machine/
    runs/
```

---

## CANON-900 — Implementation Priority

구현 우선순위는 다음이다.

```text
1. Vault init.
2. Core schemas.
3. TeamLead clarify.
4. TaskCard generation.
5. Worker dispatch.
6. WorkerResult collection.
7. MergePacket generation.
8. AccumulatedArtifact update.
9. FoldedSummary update.
10. Ponytail minimality check.
11. LoopController.
12. FinalPacket / CodexPrompt.
13. Graph index.
14. ContextRequest / ContextPacket contract.
15. ExecutionHint contract.
```

Serena live integration과 RTK integration은 MVP 이후다.

---

## CANON-910 — Success Criteria

MVP 성공 조건은 다음이다.

```text
TeamLead가 혼자 답하지 않는다.
TaskCard가 생성된다.
최소 2개 이상의 worker가 실제 호출된다.
WorkerResult가 구조화되어 저장된다.
MergePacket이 생성된다.
AccumulatedArtifact가 갱신된다.
FoldedSummary가 생성된다.
적어도 1회 slice-and-attach loop가 돈다.
FinalPacket과 CodexPrompt가 생성된다.
_GRAPH_INDEX가 생성된다.
기존 AI_WORKFLOW_KIT과 역할이 겹치지 않는다.
```

---

## CANON-920 — Failure Criteria

실패 조건은 다음이다.

```text
TeamLead가 worker 없이 최종 답변을 만든다.
TaskCard가 너무 추상적이다.
WorkerResult가 자유문 장문이라 merge가 어렵다.
MergePacket 없이 결과를 이어 붙인다.
AccumulatedArtifact에 attach하지 않는다.
Obsidian vault가 단순 raw log 저장소가 된다.
Loop가 같은 말을 반복한다.
FinalPacket이 Claude/Codex가 실행할 수 없는 설명문에 그친다.
AI_WORKFLOW_KIT 기능을 TLH 내부에 중복 구현한다.
```

---

## CANON-930 — Final Canon Sentence

TLH는 Obsidian vault를 AI-readable graph-ready 작업 기억층으로 사용하고, TeamLead가 사용자 요청을 질문으로 명확히 한 뒤, 큰 목표를 TaskCard로 분해하여 worker에게 배분하며, WorkerResult를 MergePacket으로 통합하고, Ponytail minimality check로 과잉 worker·과잉 loop·과잉 문서를 줄인 뒤, AccumulatedArtifact에 순차적으로 붙이는 루프를 반복하여, 최종적으로 사용자 또는 Claude/Codex가 사용할 FinalPacket을 만드는 팀장 중심 작업분배·결과통합·점진 조립 하네스다.
