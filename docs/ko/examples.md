# 예제

이 페이지는 실용적인 `Stream` 예제를 수집하고, 마찬가지로 중요한 것은 먼저 어떤 예제에 도달해야 하는지 설명합니다. 목표는 더 깊은 쓰기, 읽기 및 복구 페이지를 대체하는 것이 아닙니다. 목표는 "개념을 이해합니다"에서 "어떤 구체적인 흐름이 내 앞에 있는 문제와 일치하는지 알고 있습니다"로 이동하도록 돕는 것입니다.

나머지 문서에서 `Stream`의 작동 방식을 설명한다면 이 페이지에서는 해당 부분을 인식 가능한 일상 시나리오로 조합하는 방법을 설명합니다.

## 이 페이지가 귀하의 선택에 도움이 되는 것

이 페이지를 읽고 나면 다음 사항을 결정할 수 있습니다.

- 새로운 지역 매장 설정과 일치하는 예는 무엇인가요?
- 실제 작업 흐름에서 추가, 스캔, 재생 및 내보내기 중에서 선택하는 방법
- 작은 인라인 예제로 충분할 때와 개념 페이지로 다시 전환해야 할 때
- 도우미 상태를 정식 진실과 혼동하지 않고 예제 출력을 읽는 방법
- 일반적인 검사 흐름과 운영 복구 흐름의 예는 무엇입니까?

## `Stream`에 시나리오 예가 필요한 이유

언뜻 보기에 `Stream`은 하나의 기본 예만으로 충분할 정도로 작아 보일 수 있습니다. 실제로 어려운 부분은 일반적으로 "한 메소드를 어떻게 호출합니까?"가 아닙니다. 어려운 부분은 "어떤 방법 순서가 지금 당장 내려야 하는 결정과 일치하는가?"입니다.

이것이 바로 이 페이지가 API 기호가 아닌 시나리오별로 구성되어 있는 이유입니다.

중요한 점은 `Stream` 사용이 몇 가지 반복 패턴으로 클러스터되는 경향이 있다는 것입니다.

- 로컬 저장소를 시작하고 정식 레코드를 추가합니다.
- 정상적인 개발 중에 저장된 기록의 하위 집합을 검사합니다.
- 무결성 인식 동작으로 표준 기록 재생
- 다른 도구에서 JSONL이 필요한 경우 재생 기록 내보내기
- 손상이 중요하지 않은 척하지 않고 손상된 매장을 진단합니다.

이것이 이 페이지에서 중점적으로 다루는 패턴입니다.

## 이 페이지를 사용하는 방법

다음 두 가지 방법 중 하나로 이 페이지를 사용하십시오.

- `Stream`을 처음 사용하는 경우 위에서 아래로 읽으세요.
- 지금 가지고 있는 질문과 일치하는 시나리오로 이동하세요.

예가 "정확히 정식이란 무엇입니까?"와 같은 더 깊은 질문을 제기하기 시작하면 또는 "여기서 왜 `strict`이 실패했습니까?", 예제 자체에서 모든 것을 배우려고 하기보다는 링크된 개념 페이지를 따르십시오.

## 예시 지도

어디서부터 시작해야 할지 확실하지 않다면 다음 빠른 지도를 사용하세요.

- "가장 작은 엔드투엔드 성공 경로가 필요합니다."
  - `Example 1: One Record In, One Record Back Out`로 시작
- "몇 가지 기록을 작성하고 실행을 검사하고 싶습니다."
  - `Example 2: Append A Small Run And Scan It`로 이동
- "나는 일반 스캔 대신 무결성 인식 읽기를 원합니다."
  - `Example 3: Replay A Run In Strict Mode`로 이동
- "다른 도구에는 JSONL 출력이 필요합니다."
  - `Example 4: Export Replayed History`로 이동
- "가게가 파손된 것으로 의심되어 주의 깊게 읽어야 합니다."
  - `Example 5: Inspect Integrity Before Acting`로 이동
- "수리 중심의 운영자 흐름이 필요합니다."
  - `Example 6: Rebuild First, Repair Only When Justified`로 이동

## 예 1: 하나의 레코드 입력, 하나의 레코드 취소

이것은 여전히 ​​실제 `Stream` 사용법처럼 느껴지는 가장 작은 예입니다.

다음과 같은 경우에 사용하세요:

- 처음으로 지역 매장을 오픈하시네요
- 패키지가 올바르게 가져왔는지 확인하고 싶습니다.
- 허용된 추가가 디스크에서 어떻게 보이는지 확인하고 싶습니다.

```python
from pathlib import Path

from stream import ReplayMode, ScanFilter, StoreConfig, StreamStore

store = StreamStore.open(StoreConfig(root_path=Path(".stream-store")))

append_result = store.append(
    {
        "record_ref": "record/eval-start",
        "record_type": "structured_event",
        "recorded_at": "2026-04-03T00:10:00Z",
        "observed_at": "2026-04-03T00:10:00Z",
        "producer_ref": "scribe.python.local",
        "run_ref": "run/eval-1",
        "stage_execution_ref": "stage/evaluate",
        "operation_context_ref": "op/evaluate-open",
        "correlation_refs": {"trace_id": "trace/eval-1"},
        "completeness_marker": "complete",
        "degradation_marker": "none",
        "schema_version": "1.0.0",
        "payload": {
            "event_key": "evaluation.started",
            "level": "info",
            "message": "Evaluation started.",
        },
    }
)

stored = list(store.scan(ScanFilter(run_ref="run/eval-1")))
replay = store.replay(ScanFilter(run_ref="run/eval-1"), mode=ReplayMode.STRICT)

print(append_result.success)
print(append_result.accepted_count)
print(stored[0].sequence, stored[0].record["record_type"])
print(replay.record_count, replay.mode)
```

주목할 사항:

- `append()`은 구조화된 승인 정보를 반환합니다.
- `scan()`은 배치 메타데이터와 함께 저장된 레코드를 반환합니다.
- `replay()`은 읽기 위에 무결성 인식 해석 레이어를 추가합니다.

이 예 이후의 일반적인 정신 모델은 다음과 같습니다.

- 하나의 표준 레코드가 세그먼트에 추가되었습니다.
- 스캔이 저장된 기록을 직접 반환했습니다.
- 재생을 통해 해당 역사에 대해 엄격한 해석이 허용됨이 확인되었습니다.

해당 온디스크 모양은 일반적으로 다음과 같이 보입니다.

```text
.stream-store/
  manifest.json
  segments/
    segment-000001.jsonl
  indexes/
    run_ref/
      run__eval-1.jsonl
```

이는 첫 번째 성공적인 예가 이미 신뢰 분할을 가르쳐야 하기 때문에 중요합니다.

- `segments/`은 정식 기록입니다.
- `indexes/`은 도우미입니다
- `manifest.json`은 매장 운영 상태를 추적합니다.

이것이 오늘 실행하는 유일한 예제라면 다음으로 [시작하기](/Users/eastl/MLObservability/Stream/docs/ko/getting-started.md)을 읽어보세요.

## 예 2: 작은 실행을 추가하고 스캔합니다.

첫 번째 쓰기가 성공하면 일반적으로 다음으로 일반적인 질문은 다음과 같습니다. 조금 더 현실적인 실행은 어떤 모습입니까?

다음과 같은 경우에 이 예를 사용하세요.

- 하나 이상의 레코드를 추가하고 싶습니다
- `scan()`을(를) 통해 실행을 검사하고 싶습니다.
- 읽는 동안 추가 순서가 어떻게 나타나는지 보고 싶습니다.

```python
from pathlib import Path

from stream import ScanFilter, StoreConfig, StreamStore

store = StreamStore.open(StoreConfig(root_path=Path(".stream-store")))

records = [
    {
        "record_ref": "record/eval-start",
        "record_type": "structured_event",
        "recorded_at": "2026-04-03T00:10:00Z",
        "observed_at": "2026-04-03T00:10:00Z",
        "producer_ref": "scribe.python.local",
        "run_ref": "run/eval-1",
        "stage_execution_ref": "stage/evaluate",
        "operation_context_ref": "op/evaluate-open",
        "correlation_refs": {"trace_id": "trace/eval-1"},
        "completeness_marker": "complete",
        "degradation_marker": "none",
        "schema_version": "1.0.0",
        "payload": {
            "event_key": "evaluation.started",
            "level": "info",
            "message": "Evaluation started.",
        },
    },
    {
        "record_ref": "record/eval-metric-1",
        "record_type": "metric",
        "recorded_at": "2026-04-03T00:10:05Z",
        "observed_at": "2026-04-03T00:10:05Z",
        "producer_ref": "scribe.python.local",
        "run_ref": "run/eval-1",
        "stage_execution_ref": "stage/evaluate",
        "operation_context_ref": "op/evaluate-open",
        "correlation_refs": {"trace_id": "trace/eval-1"},
        "completeness_marker": "complete",
        "degradation_marker": "none",
        "schema_version": "1.0.0",
        "payload": {
            "metric_key": "accuracy",
            "metric_value": 0.94,
        },
    },
]

append_result = store.append_many(records)

for stored in store.scan(ScanFilter(run_ref="run/eval-1")):
    print(stored.sequence, stored.offset, stored.record["record_type"])
```

주목할 사항:

- `append_many()`은(는) 여전히 추가 지향적이며 숨겨진 재작성 작업이 아닙니다.
- 승인된 레코드는 여전히 개별적으로 주문된 세그먼트 항목이 됩니다.
- `scan()`은 일치하는 레코드를 반환할 때 추가 순서를 유지합니다.

실제로 이 예제는 애플리케이션이 예상한 실행 및 단계 참조와 함께 표준 레코드를 내보내고 있는지 확인하는 데 유용합니다.

일반적인 실수는 `scan()`을 의미론적 재생 레이어처럼 취급하는 것입니다. 그렇지 않습니다. `scan()`은 실제 필터와 일치하는 저장된 기록을 직접 검사하기 위한 것입니다. 무결성 인식 해석이 필요한 경우 재생으로 전환하세요.

추가 허용, 일괄 처리 및 내구성을 더 자세히 이해하려면 [쓰기 경로](/Users/eastl/MLObservability/Stream/docs/ko/write-path.md)을 읽어보세요.

## 예 3: 엄격 모드에서 실행 재생

이 예는 더 이상 저장된 레코드 일치를 원하지 않는 경우의 다음 단계입니다. 재생 규칙에 따라 지역 역사에 대한 해석을 원합니다.

다음과 같은 경우에 사용하세요:

- 저장소에서 무결성 인식 재생 의미 체계를 적용하기를 원합니다.
- 신뢰할 수 있는 로컬 기록을 위한 기본 읽기 모드를 원합니다.
- 나중에 경고나 공백을 명시적으로 드러낼 수 있는 결과를 원합니다.

```python
from stream import ReplayMode, ScanFilter

replay = store.replay(
    ScanFilter(run_ref="run/eval-1"),
    mode=ReplayMode.STRICT,
)

print(replay.mode)
print(replay.record_count)
print(replay.warnings)
print(replay.known_gaps)
```

주목할 사항:

- 엄격한 재생은 단순히 "다른 이름으로 스캔"이 아닙니다.
- 성공적인 엄격한 재생은 요청된 기록이 해당 읽기에 대한 저장소의 무결성 해석을 통과했음을 의미합니다.
- 재생은 원시 저장된 레코드뿐만 아니라 결과 모델을 반환합니다.

실제로 매장이 건강해야 한다고 믿을 때 `strict`이 기본 운영자 사고방식이 되어야 합니다.

이는 기본 내역이 정규화하기에 안전하지 않은 경우 엄격한 재생이 실패하도록 허용되기 때문에 중요합니다. 이는 불편이 아니라 보호 메커니즘입니다.

스캔과 별도로 재생이 존재하는 이유가 궁금하다면 [읽기 경로](/Users/eastl/MLObservability/Stream/docs/ko/read-path.md)로 돌아가세요.

## 예 4: 재생 내역 내보내기

때때로 질문은 "파이썬에서 이것을 어떻게 검사합니까?"가 아닙니다. 하지만 "일관된 기록을 다른 도구에 어떻게 전달합니까?"

다음과 같은 경우에 이 예를 사용하세요.

- 다른 도구는 줄 기반 JSON을 기대합니다.
- 내보내는 동안 재생 의미를 유지하려는 경우
- 편리한 운영 핸드오프 형식을 원합니다

```python
from pathlib import Path

from stream import ReplayMode, ScanFilter

output_path = Path("exports/run-eval-1.jsonl")

report = store.export_jsonl(
    output_path=output_path,
    scan_filter=ScanFilter(run_ref="run/eval-1"),
    mode=ReplayMode.STRICT,
)

print(report.record_count)
print(report.output_path)
```

주목할 사항:

- 우회하는 대신 재생 의미 체계에 따라 빌드 내보내기
- 출력은 편리한 형식이지 새로운 정보 소스가 아닙니다.
- 엄격한 재생이 정당화되지 않으면 수출은 그렇지 않은 척해서는 안 됩니다.

일반적인 실수는 내보낸 JSONL이 정식 기록이 된다고 생각하는 것입니다. 그렇지 않습니다. 표준 내역은 여전히 ​​상점에서 주문된 세그먼트 레코드 내역입니다.

재생과 내보내기 간의 정확한 관계가 필요한 경우 [읽기 경로](/Users/eastl/MLObservability/Stream/docs/ko/read-path.md)을(를) 읽어보세요.

## 예 5: 행동하기 전에 무결성을 검사하십시오

뭔가 기분이 좋지 않을 때 접근할 수 있는 예입니다.

다음과 같은 경우에 사용하세요:

- 재생이 예기치 않게 실패하기 시작합니다.
- 잘림이나 기타 디스크 손상이 의심되는 경우
- 재건이나 수리를 선택하기 전에 진단을 원합니다.

```python
integrity = store.check_integrity()

print(integrity.healthy)
print(integrity.state)

for issue in integrity.issues:
    print(issue.severity, issue.code, issue.segment_id, issue.line_number)

for recommendation in integrity.recommendations:
    print(recommendation)
```

주목할 사항:

- 무결성은 그 자체로 명시적인 연산자 표면입니다.
- `healthy`만으로는 충분하지 않습니다. `state`, `issues` 및 `recommendations` 문제
- 매장을 방문하기 전에 어떤 문제가 있는지 알아볼 수 있는 곳입니다

실제로 첫 번째로 유용한 질문은 "이 문제를 어떻게 해결합니까?"가 되는 경우가 거의 없습니다. 첫 번째 유용한 질문은 "내가 실제로 보고 있는 피해는 어떤 종류인가?"입니다.

이것이 바로 무결성 검사가 재구축 및 수리 전에 수행되는 이유입니다.

이 예 다음에 [무결성과 복구](/Users/eastl/MLObservability/Stream/docs/ko/integrity-and-repair.md)을 읽어보세요.

## 예 6: 먼저 재구축하고 타당성이 입증된 경우에만 수리

이것은 페이지에서 가장 운영적인 예입니다.

다음과 같은 경우에 사용하세요:

- 무결성 보고서는 도우미 상태 드리프트를 제안합니다.
- 파생 인덱스를 안전하게 재구축하고 싶은 경우
- 수리를 고려하고 있으며 이에 대해 신중하게 생각해야 합니다.

```python
rebuild_report = store.rebuild_indexes()
print(rebuild_report.success)
print(rebuild_report.integrity_state)
print(rebuild_report.warnings)

repair_report = store.repair()
print(repair_report.success)
print(repair_report.actions_taken)
print(repair_report.quarantined_paths)
```

주목할 사항:

- 재구축과 수리는 서로 바꿔서 사용할 수 없습니다.
- 재구축은 파생 도우미 상태에 관한 것입니다.
- 수리는 상점이 제한적이고 명시적인 수정 방법을 알고 있는 경우에만 발생해야 하는 정식 작업입니다.

중요한 점은 재구축은 인덱스가 표류할 때 일반적인 첫 번째 유지 관리 단계인 반면, 복구는 표준 기록에 대한 운영자의 해석에 영향을 주기 때문에 더 심각하게 느껴져야 한다는 것입니다.

일반적인 실수는 수리를 무해한 정리로 취급하는 것입니다. `Stream`에서 그것은 잘못된 사고방식입니다.

프로덕션에서 이 흐름을 사용하기 전에 [레이아웃과 저장소](/Users/eastl/MLObservability/Stream/docs/ko/layout-and-storage.md) 및 [무결성과 복구](/Users/eastl/MLObservability/Stream/docs/ko/integrity-and-repair.md)을 읽어보세요.

## 예제 7: 번들 기본 예제에서 시작

문서에서 조각을 복사하는 대신 체크인된 파일로 시작하려면 여기에서 시작하세요.

번들 예제는 [examples/basic_usage.py](/Users/eastl/MLObservability/Stream/examples/basic_usage.py)에 있습니다.

의도적으로 작은 작업 흐름을 보여줍니다.

- 지역 매장을 열다
- 하나의 표준 레코드 추가
- `run_ref`로 스캔
- 저장된 결과를 인쇄하세요

따라서 다음과 같은 경우에 적합합니다.

- 귀하의 환경이 `stream`을(를) 가져오는지 확인 중입니다.
- 코드에서 하나의 작은 표준 레코드 모양 보기
- 기본 스캔 흐름이 어떤 느낌인지 확인

실행한 후 다음으로 이동하세요.

- [시작하기](/Users/eastl/MLObservability/Stream/docs/ko/getting-started.md) 더 자세한 내용을 보려면
- [쓰기 경로](/Users/eastl/MLObservability/Stream/docs/ko/write-path.md) 의미를 추가하려면
- [읽기 경로](/Users/eastl/MLObservability/Stream/docs/ko/read-path.md) 재생 및 의미 내보내기를 원하는 경우

## 일반적인 예시 실수

사람들이 이 스니펫을 처음 적용할 때 몇 가지 실수가 반복적으로 나타납니다.

- 임의의 JSON을 추가 가능한 표준 레코드로 처리
- `append_many()`이 자동으로 전부 아니면 전무라고 가정합니다.
- 실제 질문이 재생 안전일 때 `scan()` 사용
- 내보낸 JSONL을 표준 스토리지로 처리
- 무결성 보고서를 읽기 전에 `repair()`로 이동
- 디버깅 중 `indexes/`을 정보 소스로 처리

예 중 하나가 놀랍게 느껴진다면 방법이 이상해서가 아닐 가능성이 가장 높습니다. 가장 가능성 있는 원인은 라이브러리가 실제로 지원하는 것보다 느슨한 이벤트 로그 정신 모델을 사용하여 `Stream`에 접근하고 있다는 것입니다.

## 다음에 읽을 페이지

예제 다음에 이 빠른 가이드를 사용하세요.

- 추가 승인 또는 일괄 처리가 불분명하다고 느껴지면 [쓰기 경로](/Users/eastl/MLObservability/Stream/docs/ko/write-path.md)을 읽어보세요.
- `scan`, `replay` 또는 `export_jsonl()` 경계가 불분명하다고 느껴지면 [읽기 경로](/Users/eastl/MLObservability/Stream/docs/ko/read-path.md)을(를) 읽어보세요.
- 디스크의 표준이 무엇인지 이해하려면 [레이아웃과 저장소](/Users/eastl/MLObservability/Stream/docs/ko/layout-and-storage.md)을 읽어보세요.
- 손상을 진단하는 경우 [무결성과 복구](/Users/eastl/MLObservability/Stream/docs/ko/integrity-and-repair.md)을 읽어보세요.
- 가장 작은 전체 연습을 다시 원하시면 [시작하기](/Users/eastl/MLObservability/Stream/docs/ko/getting-started.md)을 읽어보세요.

중요한 점은 사례가 인식 속도를 높여야지 더 깊은 정신 모델을 대체해서는 안 된다는 것입니다. `Stream`에서는 하나의 행복한 경로 조각을 암기하는 것보다 올바른 작동 해석이 여전히 더 중요합니다.
