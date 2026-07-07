# TLH_MVP_PLAN.md

## Purpose

이 문서는 TLH의 MVP 구현 범위를 정의한다.

`TLH_CANON.md`는 정본이고, `TLH_INDEX.md`는 정본 라우터다.
이 문서는 실제 구현 순서와 검증 기준을 정하는 실행 계획이다.

TLH MVP의 목표는 다음 하나다.

```text
Obsidian-compatible Markdown vault 안에서 하나의 사용자 요청이
질문 → TaskCard → WorkerResult → MergePacket → AccumulatedArtifact → FinalPacket
으로 자라는 것을 증명한다.
```

---

## 1. MVP Boundary

### Included

MVP에 포함한다.

```text
1. Vault 초기화.
2. _AI_README.md 생성.
3. _CURRENT_STATE.md 생성.
4. _AI_INDEX.md 생성.
5. _GRAPH_INDEX.json 생성.
6. _GRAPH_INDEX.md 생성.
7. 사용자 mission 입력.
8. TeamLead clarification question 생성.
9. 사용자 answer 반영.
10. TaskCard 생성.
11. 최소 2개 worker dispatch.
12. WorkerResult 저장.
13. MergePacket 생성.
14. AccumulatedArtifact 갱신.
15. FoldedSummary 생성.
16. Ponytail MinimalityCheck 생성.
17. LoopController decision 생성.
18. FinalPacket 생성.
19. CodexPrompt 생성.
20. machine-readable run files 저장.
```

### Excluded

MVP에 포함하지 않는다.

```text
1. GUI.
2. 대시보드.
3. Obsidian plugin.
4. Obsidian MCP write.
5. Serena live edit/write/refactor.
6. RTK global hook.
7. Claude/Codex 자동 실행.
8. GitHub 자동 PR/merge.
9. worker 직접 파일 수정.
10. worker shell 실행.
11. 대형 벤치마크.
12. AI_WORKFLOW_KIT 기능 중복 구현.
13. 전역 AGENTS.md / CLAUDE.md 관리 기능.
14. Codex/Claude skills 설치 기능.
```

---

## 2. Project Structure

초기 repo 구조는 다음으로 한다.

```text
C:\Users\USER\TLH\
  AGENTS.md
  CLAUDE.md

  docs\
    TLH_INDEX.md
    TLH_CANON.md
    TLH_MVP_PLAN.md
    TLH_IMPLEMENTATION_PROMPT.md
    CURRENT_STATE.md

  tlh\
    __init__.py
    __main__.py
    cli.py
    schemas.py
    vault.py
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

  prompts\
    team_lead_clarify.v1.md
    team_lead_decompose.v1.md
    worker_base.v1.md
    worker_builder.v1.md
    worker_critic.v1.md
    merge_harness.v1.md
    continuity_check.v1.md
    final_packet.v1.md
    codex_prompt.v1.md

  vault\
    _AI_README.md
    _CURRENT_STATE.md
    _AI_INDEX.md
    _GRAPH_INDEX.json
    _GRAPH_INDEX.md

    00_Inbox\
    01_Runs\
    02_TaskCards\
    03_WorkerResults\
    04_MergePackets\
    05_Artifacts\
    06_Handoff\
    07_Patterns\
    08_Failures\
    09_Decisions\
    10_ContextPackets\
    11_MinimalityChecks\

  machine\
    runs\
```

---

## 3. CLI Scope

MVP CLI는 다음 명령을 제공한다.

```powershell
python -m tlh init
python -m tlh run --mission "vault\00_Inbox\mission.md"
python -m tlh answer --run "<run_id>" --answers "vault\01_Runs\<run_id>_answers.md"
python -m tlh dispatch --run "<run_id>"
python -m tlh merge --run "<run_id>"
python -m tlh loop --run "<run_id>"
python -m tlh finalize --run "<run_id>"
```

### init

역할.

```text
vault 구조를 만든다.
machine\runs 구조를 만든다.
기본 _AI_README.md, _CURRENT_STATE.md, _AI_INDEX.md를 만든다.
기본 _GRAPH_INDEX.json, _GRAPH_INDEX.md를 만든다.
```

성공 조건.

```text
필수 디렉터리와 필수 vault 파일이 생성된다.
기존 파일이 있으면 덮어쓰지 않고 보존한다.
```

### run

역할.

```text
mission.md를 읽는다.
run_id를 생성한다.
TeamLead clarification question을 생성한다.
run note를 만든다.
_CURRENT_STATE.md를 active run 상태로 갱신한다.
```

성공 조건.

```text
01_Runs에 run note가 생긴다.
machine\runs\<run_id>\state.json이 생긴다.
질문 파일이 생성된다.
```

### answer

역할.

```text
사용자 답변을 반영한다.
Concrete Mission을 만든다.
TeamLead가 TaskCard를 생성한다.
```

성공 조건.

```text
02_TaskCards에 TaskCard note가 생성된다.
machine\runs\<run_id>\task_cards.jsonl이 생성된다.
```

### dispatch

역할.

```text
TaskCard를 worker에게 배분한다.
WorkerResult를 저장한다.
```

성공 조건.

```text
최소 2개 이상의 WorkerResult가 생성된다.
03_WorkerResults에 note가 생성된다.
machine\runs\<run_id>\worker_results.jsonl이 생성된다.
```

### merge

역할.

```text
WorkerResult를 MergePacket으로 통합한다.
AccumulatedArtifact를 갱신한다.
FoldedSummary를 생성한다.
MinimalityCheck를 생성한다.
```

성공 조건.

```text
04_MergePackets에 MergePacket note가 생성된다.
05_Artifacts에 AccumulatedArtifact note가 생성 또는 갱신된다.
11_MinimalityChecks에 MinimalityCheck note가 생성된다.
machine\runs\<run_id>\merge_packets.jsonl이 생성된다.
```

### loop

역할.

```text
LoopController가 다음 action을 결정한다.
필요하면 다음 slice TaskCard를 만든다.
필요 없으면 finalize 가능 상태로 만든다.
```

성공 조건.

```text
next_slice, targeted_verifier, user_question_needed, stop_and_finalize, failed_to_merge 중 하나를 기록한다.
같은 작업을 무한 반복하지 않는다.
```

### finalize

역할.

```text
FinalPacket을 생성한다.
CodexPrompt를 생성한다.
_GRAPH_INDEX를 갱신한다.
_CURRENT_STATE.md를 갱신한다.
```

성공 조건.

```text
06_Handoff에 FinalPacket과 CodexPrompt가 생성된다.
_GRAPH_INDEX.json과 _GRAPH_INDEX.md가 갱신된다.
run status가 finalized가 된다.
```

---

## 4. Core Schemas

MVP에서는 최소한 다음 schema를 구현한다.

### TaskCard

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

### WorkerResult

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

### MergePacket

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

### MinimalityCheck

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

### LoopDecision

```json
{
  "run_id": "",
  "loop_index": 0,
  "decision": "next_slice | targeted_verifier | user_question_needed | stop_and_finalize | failed_to_merge",
  "reason": "",
  "next_actions": []
}
```

### FinalPacket

```json
{
  "run_id": "",
  "goal": "",
  "current_state": "",
  "confirmed_assumptions": [],
  "scope": [],
  "out_of_scope": [],
  "execution_steps": [],
  "risks": [],
  "verification": [],
  "handoff_prompt": "",
  "user_decision_points": []
}
```

---

## 5. Implementation Order

구현 순서는 다음으로 고정한다.

```text
1. Repo skeleton 생성.
2. docs 존재 확인.
3. vault init 구현.
4. schemas.py 구현.
5. packet_writer.py 구현.
6. graph_index.py 구현.
7. team_lead clarify 구현.
8. team_lead decompose 구현.
9. task_card 저장 구현.
10. worker_pool 인터페이스 구현.
11. gemma_client stub 또는 live wrapper 구현.
12. dispatcher 구현.
13. WorkerResult 저장 구현.
14. merge_harness 구현.
15. AccumulatedArtifact 갱신 구현.
16. ponytail_checker 구현.
17. loop_controller 구현.
18. final_packet 생성 구현.
19. codex_prompt 생성 구현.
20. CLI 연결.
21. smoke test 작성.
22. end-to-end sample run 검증.
```

---

## 6. Worker Strategy

MVP에서는 worker를 과하게 일반화하지 않는다.

초기 worker role은 다음만 사용한다.

```text
planner.
builder.
critic.
continuity_checker.
```

MVP에서 worker가 live model을 호출할 수 있으면 좋다.
단, API key나 secret을 repo에 저장하지 않는다.

live model 호출이 실패하면 stub worker로 대체할 수 있다.
stub worker는 실제 workflow 검증용으로만 사용하고, 결과에 `stub: true`를 명시한다.

---

## 7. Vault Writing Rules

vault note는 사람이 읽을 수 있고 AI도 읽을 수 있어야 한다.

모든 주요 note에는 frontmatter를 둔다.

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

각 note에는 가능한 한 다음 섹션을 둔다.

```text
Purpose.
Current State.
Inputs.
Outputs.
Links.
Do Next.
Do Not.
```

기존 note를 덮어쓰지 않는다.
갱신이 필요한 note는 version 또는 updated timestamp를 반영한다.

---

## 8. Graph Index Rules

`graph_index.py`는 vault note의 frontmatter와 Graph Links를 읽어 다음 파일을 만든다.

```text
vault\_GRAPH_INDEX.json
vault\_GRAPH_INDEX.md
```

edge type은 다음만 우선 지원한다.

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
```

---

## 9. Verification

최소 검증은 다음이다.

```powershell
python -m tlh init
python -m tlh run --mission "vault\00_Inbox\mission.md"
python -m tlh answer --run "<run_id>" --answers "vault\01_Runs\<run_id>_answers.md"
python -m tlh dispatch --run "<run_id>"
python -m tlh merge --run "<run_id>"
python -m tlh loop --run "<run_id>"
python -m tlh finalize --run "<run_id>"
```

검증해야 할 결과.

```text
vault 구조 생성.
run state 생성.
TaskCard 생성.
WorkerResult 생성.
MergePacket 생성.
AccumulatedArtifact 생성.
MinimalityCheck 생성.
LoopDecision 생성.
FinalPacket 생성.
CodexPrompt 생성.
_GRAPH_INDEX 생성.
```

---

## 10. Success Criteria

MVP 성공 조건.

```text
1. TeamLead가 worker 없이 최종 답변하지 않는다.
2. TaskCard가 생성된다.
3. 최소 2개 이상의 WorkerResult가 생성된다.
4. MergePacket이 생성된다.
5. AccumulatedArtifact가 갱신된다.
6. FoldedSummary가 생성된다.
7. MinimalityCheck가 생성된다.
8. 적어도 1회 LoopDecision이 생성된다.
9. FinalPacket과 CodexPrompt가 생성된다.
10. _GRAPH_INDEX.json이 생성된다.
11. AI_WORKFLOW_KIT 기능을 중복 구현하지 않는다.
```

---

## 11. Failure Criteria

MVP 실패 조건.

```text
1. TeamLead가 혼자 최종 산출물을 만든다.
2. TaskCard 없이 worker를 호출한다.
3. WorkerResult가 자유문 장문이라 merge할 수 없다.
4. MergePacket 없이 결과를 붙인다.
5. AccumulatedArtifact가 갱신되지 않는다.
6. vault가 raw log 저장소가 된다.
7. loop가 같은 내용을 반복한다.
8. FinalPacket이 실행 가능한 지시문이 아니다.
9. AI_WORKFLOW_KIT 역할을 TLH 내부에 다시 만든다.
10. MVP 범위를 넘어 GUI, MCP write, RTK hook, Serena write를 넣는다.
```

---

## 12. Reporting Format

구현 후 보고 형식.

```text
TLH MVP 구현 보고.

변경 파일.
- <file>

생성된 구조.
- vault: YES/NO.
- machine\runs: YES/NO.
- prompts: YES/NO.
- tlh package: YES/NO.

구현된 CLI.
- init: YES/NO.
- run: YES/NO.
- answer: YES/NO.
- dispatch: YES/NO.
- merge: YES/NO.
- loop: YES/NO.
- finalize: YES/NO.

검증.
- 실행한 명령.
- 결과.
- 실패한 명령이 있으면 원인.

MVP 성공 조건.
- TaskCard 생성: YES/NO.
- WorkerResult 생성: YES/NO.
- MergePacket 생성: YES/NO.
- AccumulatedArtifact 갱신: YES/NO.
- FinalPacket 생성: YES/NO.
- Graph index 생성: YES/NO.

남은 위험.
- <risk>

다음 단계.
- <next>
```
