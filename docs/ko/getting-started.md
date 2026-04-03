# 시작하기

이 페이지는 먼저 하나의 실용적인 질문인 실제 Python 세션에서 로컬 `StreamStore`을 엔드 투 엔드로 작동시키려면 어떻게 해야 합니까?에 답하는 데 도움이 됩니다. 목표는 아직 모든 스토리지 세부 사항을 설명하는 것이 아닙니다. 목표는 하나의 추가-읽기 흐름을 성공시키고, 디스크에 기록된 내용을 보여주고, 결과가 무엇을 의미하는지 설명하고, 나중에 복구 및 재생 작업을 신비롭지 않고 자연스럽게 느끼게 만드는 처음 몇 가지 습관을 확립하는 것입니다.

라이브러리를 사용하기 전에 한 페이지만 읽었다면 이 페이지가 그 페이지여야 합니다.

## 이 페이지가 귀하에게 도움이 되는 것

이 페이지를 읽고 나면 다음을 수행할 수 있습니다.

- 로컬 `StreamStore` 만들기
- 하나의 표준 레코드를 성공적으로 추가했습니다.
- 여러 레코드를 추가하고 부분 승인을 해석합니다.
- 저장된 기록을 다시 스캔
- 매장 무결성과 일치하는 방식으로 해당 기록을 재생합니다.
- 다른 도구에 JSONL이 필요할 때 재생 기록 내보내기
- 동등한 CLI 명령 실행
- 디스크에 있는 어떤 파일이 표준이고 어떤 것이 도우미일 뿐인지 인식

## 여기서 시작해야 하는 이유

언뜻 보면 `Stream`은(는) 몇 가지 편리한 방법을 갖춘 일반 이벤트 로그처럼 보일 수 있습니다. 실제로 그러한 정신적 모델은 너무 느슨합니다. `Stream`은 특히 스택의 추가 지향 표준 레코드 저장소입니다. 중요한 점은 세그먼트 기록이 진실의 소스인 반면 도우미 인덱스는 파생되고 재구성 가능하다는 것입니다.

첫 번째 성공적인 워크플로에서는 올바른 습관을 즉시 가르쳐야 하기 때문에 이것이 중요합니다.

- 임의의 디버그 blob이 아닌 정식 레코드를 추가합니다.
- 쓰기가 전부 아니면 전무라고 가정하는 대신 결과 추가에 주의하세요.
- 질문하는 내용에 따라 `scan` 또는 `replay`을 읽어보세요.
- `segments/`을(를) 신뢰할 수 있는 것으로 취급
- `indexes/`을(를) 도우미로 취급
- 무결성 검사를 단순한 비상 절차가 아닌 일반적인 매장 운영으로 취급합니다.

해당 정신 모델이 일찍 시작되면 손상된 저장소, 관용적 재생 및 수리에 대한 이후 페이지를 추론하기가 훨씬 쉬워집니다.

## 시작하기 전에

이 페이지에서는 `stream` 패키지를 가져올 수 있는 Python 환경이 있다고 가정합니다.

예제에서는 다음을 사용합니다.

- `.stream-store`에 뿌리를 둔 지역 상점
- `structured_event` 레코드 계열 1개
- `run_ref="run/eval-1"`을 실제 스캔 키로 사용

실행 중인 서비스, 데이터베이스 또는 원격 백엔드가 필요하지 않습니다. `Stream`은(는) 로컬 우선으로 설계되었습니다.

## 가장 작은 성공 흐름

가장 작은 유용한 흐름은 다음과 같습니다.

1. 로컬 디렉터리에 뿌리를 둔 저장소를 만듭니다.
2. 하나의 유효한 표준 레코드를 추가합니다.
3. 실용적인 필터를 사용해 매장을 스캔해보세요.
4. 재생 경로를 통해 동일한 내역을 재생합니다.

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

print(append_result.success)
print(append_result.accepted_count)
print(append_result.accepted[0].durability_status)

records = list(store.scan(ScanFilter(run_ref="run/eval-1")))
print(records[0].sequence, records[0].record["record_type"])

replay = store.replay(ScanFilter(run_ref="run/eval-1"), mode=ReplayMode.STRICT)
print(replay.record_count, replay.mode)
```

한 번의 성공적인 실행은 이미 런타임 형태의 대부분을 가르쳐줍니다.

- `append()`은 `True` 또는 `False`뿐만 아니라 구조화된 추가 메타데이터를 반환합니다.
- `scan()`은 저장된 레코드를 추가 순서로 반환합니다.
- `replay()`은 나중에 경고 및 알려진 공백을 표면화할 수 있는 재생 결과를 반환합니다.
- 쓰기 후 디스크에서 직접 저장소를 검사할 수 있습니다.

## 1단계: 매장 개설

`StreamStore` 생성은 의도적으로 간단합니다.

```python
from pathlib import Path

from stream import StoreConfig, StreamStore

store = StreamStore.open(StoreConfig(root_path=Path(".stream-store")))
```

이 한 줄은 저장소의 로컬 루트를 설정하고 검사 가능한 레이아웃이 아직 존재하지 않는 경우 초기화합니다.

실제로 이는 다음을 의미합니다.

- 루트 디렉토리가 생성됩니다
- `segments/` 디렉토리가 생성됩니다
- `manifest.json`이 누락된 경우 초기화됩니다.
- 달리 구성하지 않는 한 도우미 색인이 활성화됩니다.

중요한 점은 매장을 여는 것이 단순히 메모리에 객체를 생성하는 것이 아니라는 점입니다. 또한 정식 기록이 디스크에 저장될 위치를 선언합니다.

## 2단계: 표준 레코드 추가

첫 번째 쓰기는 유효한 표준 레코드여야 합니다. `Stream`은(는) 자유 형식 JSON 버킷이 아니기 때문에 이를 명시적으로 설명할 가치가 있습니다.

```python
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
```

이는 레코드가 예상되는 표준 형태를 충족하는 경우에만 성공합니다. 여기에는 다음이 포함됩니다.

- 필수 봉투 필드
- 정규화된 타임스탬프
- 지원되는 스키마 버전
- 레코드 유형과 일치하는 페이로드 구조

즉, `Stream`은(는) 데이터가 단순히 직렬화 가능한지 여부를 결정하지 않습니다. 그 기록이 정식 역사서로 받아들여질 수 있는지 여부를 결정하는 것입니다.

## 3단계: 추가 결과를 주의 깊게 읽으세요.

일반적인 첫 번째 실수는 `append()`을 호출한 다음 반환 값을 무시하는 것입니다. 그러지 마세요.

건강한 단일 레코드 저장소의 경우 결과는 일반적으로 개념적으로 다음과 같습니다.

```text
append_result.success == True
append_result.accepted_count == 1
append_result.rejected_count == 0
append_result.accepted[0].durability_status == "flushed" or "fsynced"
append_result.accepted[0].sequence == 1
append_result.accepted[0].segment_id == 1
append_result.accepted[0].offset == 1
```

중요한 점은 추가가 "작성된 쓰기" 이상의 내용을 알려준다는 것입니다.

- `success`은 배치에 거부가 있었는지 여부를 알려줍니다.
- `accepted_count` 및 `rejected_count`은 결과가 부분적인지 여부를 알려줍니다.
- `durability_status`은 메서드가 반환되기 전에 디스크에서 쓰기가 얼마나 멀리 도달했는지 알려줍니다.
- `sequence`, `segment_id` 및 `offset`는 기록이 표준 역사에서 어디에 도착했는지 알려줍니다.

상점이 한 줄 이상의 기록을 보유하면 해당 메타데이터가 훨씬 더 유용해집니다.

## 4단계: 저장된 기록 스캔

레코드가 존재하면 `scan()`을(를) 사용하여 검사할 수 있습니다.

```python
records = list(store.scan(ScanFilter(run_ref="run/eval-1")))

for stored in records:
    print(stored.sequence, stored.record["record_type"], stored.record["payload"])
```

`scan()`은 간단한 읽기 경로입니다. 일반적으로 다음과 같은 경우에 올바른 기본값입니다.

- 일반 현지 점검
- 실행, 단계, 기록 유형 또는 기간별로 필터링
- 위에 계층화된 재생 의미 없이 레코드를 직접 저장함

핵심 아이디어는 `scan()`이 실제 검색 질문(이 필터와 일치하는 저장된 레코드는 무엇입니까?)에 답한다는 것입니다.

## 5단계: 동일한 기록 재생

이제 `replay()`을 통해 동일한 기록을 읽습니다.

```python
from stream import ReplayMode, ScanFilter

replay = store.replay(
    ScanFilter(run_ref="run/eval-1"),
    mode=ReplayMode.STRICT,
)

print(replay.record_count)
print(replay.mode)
print(replay.warnings)
print(replay.known_gaps)
```

건강한 매장의 경우 재생 결과는 일반적으로 개념적으로 다음과 같습니다.

```text
replay.record_count == 1
replay.mode == "strict"
replay.warnings == ()
replay.known_gaps == ()
```

언뜻 보면 `scan()` 및 `replay()`은 둘 다 저장된 레코드를 반환하므로 중복되어 보일 수 있습니다. 실제로는 약간 다른 질문에 답합니다.

- `scan()`은(는) 무엇이 저장되어 있는지 묻습니다.
- `replay()`은(는) 선택한 재생 모드에서 어떤 기록을 안전하게 해석할 수 있는지 묻습니다.

건강한 단일 레코드 예에서는 이러한 차이가 크게 중요하지 않습니다. 부패가 등장하면 매우 중요합니다.

## 6단계: 소규모 배치 추가 시도

`Stream`은 추가 지향적이므로 모든 쓰기가 단일 레코드라고 가정하는 대신 작은 배치를 조기에 확인하는 것이 유용합니다.

```python
batch_result = store.append_many(
    [
        {
            "record_ref": "record/eval-metric-1",
            "record_type": "metric",
            "recorded_at": "2026-04-03T00:10:01Z",
            "observed_at": "2026-04-03T00:10:01Z",
            "producer_ref": "scribe.python.local",
            "run_ref": "run/eval-1",
            "stage_execution_ref": "stage/evaluate",
            "operation_context_ref": "op/evaluate-metric-1",
            "correlation_refs": {"trace_id": "trace/eval-1"},
            "completeness_marker": "complete",
            "degradation_marker": "none",
            "schema_version": "1.0.0",
            "payload": {
                "metric_key": "evaluation.loss",
                "value": 0.42,
                "value_type": "scalar",
                "aggregation_scope": "step",
                "tags": {"split": "validation"},
            },
        },
        {
            "record_type": "metric",
            "payload": {},
        },
    ]
)

print(batch_result.accepted_count)
print(batch_result.rejected_count)
print(batch_result.rejected)
```

`append_many()`은 전부 아니면 전무가 아니기 때문에 이는 중요합니다. 일괄 처리는 동일한 호출에서 유효한 레코드를 허용하고 유효하지 않은 레코드를 거부할 수 있습니다.

## 전반적으로 기대할 수 있는 것

정상적인 첫 실행 후에는 라이브러리에서 세 가지 종류의 정보를 얻을 수 있습니다.

- 결과를 추가하면 수용성, 내구성 및 배치를 알 수 있습니다.
- 저장된 기록은 어떤 정식 라인이 존재하는지 알려줍니다.
- 재생 결과는 기록이 어떻게 해석되었는지 알려줍니다.

중요한 점은 추가, 검색 및 재생이 서로 다른 운영 결정을 지원하기 때문에 의도적으로 서로 다른 표면이라는 것입니다.

## 디스크에 기록되는 내용

첫 번째 추가 후 저장소 디렉터리는 대략 다음과 같습니다.

```text
.stream-store/
  manifest.json
  segments/
    segment-000001.jsonl
  indexes/
    run_ref/
      run__eval-1.jsonl
    stage_execution_ref/
      stage__evaluate.jsonl
    record_type/
      structured_event.jsonl
```

첫 번째 표준 세그먼트 항목은 대략 다음과 같습니다.

```json
{
  "sequence": 1,
  "appended_at": "2026-04-03T00:10:00Z",
  "record": {
    "record_ref": "record/eval-start",
    "record_type": "structured_event",
    "recorded_at": "2026-04-03T00:10:00Z",
    "observed_at": "2026-04-03T00:10:00Z",
    "producer_ref": "scribe.python.local",
    "run_ref": "run/eval-1",
    "stage_execution_ref": "stage/evaluate",
    "operation_context_ref": "op/evaluate-open",
    "correlation_refs": {
      "trace_id": "trace/eval-1"
    },
    "completeness_marker": "complete",
    "degradation_marker": "none",
    "schema_version": "1.0.0",
    "payload": {
      "event_key": "evaluation.started",
      "level": "info",
      "message": "Evaluation started."
    }
  }
}
```

그리고 `manifest.json`은(는) 추가 진행 상황 추적을 시작합니다.

```json
{
  "layout_mode": "jsonl_segments",
  "layout_version": "1",
  "current_segment_id": 1,
  "next_sequence": 2,
  "last_committed_sequence": 1,
  "current_segment_record_count": 1
}
```

이는 신뢰 경계를 명확하게 보여주기 때문에 중요합니다.

- `segments/` 표준 추가 기록 보유
- `manifest.json`은 추가 진행 상황과 현재 레이아웃 상태를 추적합니다.
- `indexes/` 실용적인 스캔에 도움이 되지만 신뢰할 수는 없습니다.

## 동등한 CLI 흐름

동일한 첫 번째 워크플로우는 CLI에서도 단순하게 느껴져야 합니다.

지역 상점을 스캔하세요:

```powershell
stream-cli --store .stream-store scan --run-ref run/eval-1
```

동일한 기록을 재생합니다.

```powershell
stream-cli --store .stream-store replay --run-ref run/eval-1 --mode strict
```

빠른 무결성 검사를 실행합니다.

```powershell
stream-cli --store .stream-store integrity
```

재생 기록을 JSONL로 내보내기:

```powershell
stream-cli --store .stream-store export --run-ref run/eval-1 --output exports/eval.jsonl
```

건강한 매장에서 무결성 출력은 개념적으로 다음과 같습니다.

```json
{
  "healthy": true,
  "state": "healthy",
  "segment_count": 1,
  "record_count": 1,
  "issues": [],
  "recommendations": []
}
```

## `scan`과 `replay`에 대해 생각하는 방법

언뜻 보면 `scan`과 `replay`은 둘 다 저장된 레코드를 반환하기 때문에 매우 유사해 보입니다. 실제로 그들은 약간 다른 질문에 대답합니다.

다음과 같은 경우 `scan`을(를) 사용하세요.

- 당신은 직접 저장된 기록을 원한다
- 실행, 단계, 기록 유형 또는 시간별로 필터링하고 있습니다.
- 일반적인 현지 점검을 하고 계십니다
- 가능한 가장 간단한 읽기 경로를 원합니다

다음과 같은 경우 `replay`을(를) 사용하세요.

- 무결성 인식 읽기 경로를 원합니다
- `strict` 대 `tolerant` 의미론이 필요합니다.
- 매장이 손상되었을 때 경고 및 알려진 격차 보고를 원합니다.
- 당신은 얼마나 많은 피해를 감수할 의사가 있는지 명시적으로 밝히고 싶습니다.

## `strict`과 `tolerant`에 대해 생각하는 방법

시작 페이지에서도 이러한 차이점을 조기에 파악하는 것이 도움이 됩니다.

- `strict`은 편리함보다 안전을 우선시합니다.
- `tolerant`은 명시적인 경고와 함께 사용 가능한 부분 기록의 우선순위를 지정합니다.

중요한 점은 `tolerant`이 "더 많이 반환하기 때문에 더 나은" 것이 아니라는 것입니다. 그것은 단순히 다른 절충안일 뿐입니다.

## 첫 번째 설정에서 흔히 발생하는 실수

### `Stream`을 일반 JSON 버킷처럼 처리

일반적인 실수는 이벤트처럼 보이는 한 JSON 페이로드를 추가할 수 있다고 가정하는 것입니다. `Stream`은(는) 스택에서 사용하는 계약 형태를 충족하는 정식 레코드를 기대합니다.

### 인덱스를 정보 소스로 취급

`indexes/`을 먼저 검사하고 읽기 쉽기 때문에 신뢰할 수 있다고 가정하고 싶은 유혹이 있습니다. 그렇지 않습니다. 인덱스는 다시 작성 가능한 도우미 파일입니다. 표준 기록은 `segments/*.jsonl`에 있습니다.

### `strict` 재생이 더 까다로운 읽기라고 가정

`strict` 재생은 장식 모드가 아닙니다. 안전 경계입니다. 저장소가 손상된 경우 `strict` 재생이 계속되지 않습니다.

### 부분 배치 결과 무시

또 다른 일반적인 실수는 `append_many()`을 트랜잭션의 전부 아니면 전무 호출처럼 취급하는 것입니다. 그렇지 않습니다. 결과 개체를 읽고 배치가 입력의 일부만 허용하는지 확인해야 합니다.

## 이것이 운영상 중요한 이유

이 첫 번째 연습에서도 주요 운영 습관이 확립되었습니다.

- 추가 결과는 무시되지 않고 해석되어야 합니다.
- 재생 모드는 의도적으로 선택해야 합니다.
- 디스크상의 도우미 파일을 정식 진실로 오해해서는 안 됩니다.
- 무결성 검사는 응급 복구뿐만 아니라 일반 저장소 사용의 일부입니다.
- 내보내기는 새로운 정보 소스가 아니라 읽기 측 편의로 간주되어야 합니다.

## 좋은 첫 번째 세션 체크리스트

이 페이지를 마친 후 실질적인 자가 점검을 원할 경우 짧은 세션 하나로 다음을 모두 수행할 수 있는지 확인하세요.

1. 새로운 지역 매장을 열다
2. 하나의 유효한 표준 레코드 추가
3. 추가 결과 필드를 검사합니다.
4. `run_ref`까지 기록을 다시 스캔해 주세요
5. `strict` 모드에서 동일한 레코드 재생
6. `manifest.json` 및 디스크의 첫 번째 세그먼트 열기
7. `stream-cli integrity` 실행
8. 재생 기록을 JSONL 파일로 내보내기

## 다음에 읽을 내용

스토리지 경계, 신뢰 모델, `Stream`의 역할을 정확하게 이해하려면 다음 [멘탈 모델](mental-model.md)을 읽어보세요.

`scan`, `replay`, 허용되는 읽기 및 내보내기 동작에 대한 자세한 설명을 보려면 다음 [읽기 경로](read-path.md)을 읽어보세요.

레코드 승인, 일괄 처리, 내구성 및 추가 동작을 더 자세히 이해하려면 다음 [쓰기 경로](write-path.md)을 읽어보세요.
