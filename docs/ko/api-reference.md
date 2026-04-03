# API 레퍼런스

[사용자 가이드 홈](/Users/eastl/MLObservability/Stream/docs/USER_GUIDE.ko.md)

이 페이지는 `Stream`에서 공개된 공개 Python API를 수집합니다. 이는 가져올 수 있는 표면, 생성자 및 메서드 서명, 결과 모델, 구성 열거형, 호출자가 추론할 것으로 예상되는 형식화된 예외에 중점을 둡니다.

추가, 검색, 재생, 재구축 또는 복구를 언제 사용해야 하는지에 대한 개념적 설명이 필요한 경우 설명 페이지를 먼저 사용하세요. 원하는 작업을 이미 알고 있고 정확한 공개 표면이 필요한 경우 이 페이지를 열어 두십시오.

## 공공 수입 표면

주요 공개 패키지 표면은 [`src/stream/__init__.py`](/Users/eastl/MLObservability/Stream/src/stream/__init__.py)에 의해 정의됩니다. The public API submodule is defined by [`src/stream/api/__init__.py`](/Users/eastl/MLObservability/Stream/src/stream/api/__init__.py).

공개 가져오기 경로:

- `stream`
- `stream.api`
- `stream.config`
- `stream.exceptions`
- `stream.models`

대부분의 애플리케이션 코드에서 기본 가져오기는 다음과 같습니다.

- `StreamStore`
- `StoreConfig`
- `ScanFilter`
- `ReplayMode`

패키지 루트는 아래에 설명된 결과 모델, 구성 열거형 및 입력된 예외도 내보냅니다.

## 기본 진입점

### `stream.StreamStore`

`StreamStore`은(는) 도서관의 주요 공개 진입점입니다.

생성자 모양:

```python
from stream import StoreConfig, StreamStore

store = StreamStore.open(StoreConfig(root_path=Path(".stream-store")))
```

중요한 점은 호출자가 일반적으로 하위 수준 서비스를 직접 조립하지 않는다는 것입니다. 하나의 로컬 저장소 루트에 바인딩된 하나의 `StreamStore`을 열고 해당 개체를 통해 모든 표준 쓰기, 읽기, 무결성, 내보내기 및 복구 작업을 수행합니다.

공용 생성자 및 속성:

- `StreamStore.open(config: StoreConfig) -> StreamStore`
- `store.config -> StoreConfig`

공개 메소드:

- `append(record: object) -> AppendResult`
- `append_many(records: list[object] | tuple[object, ...]) -> AppendResult`
- `scan(scan_filter: ScanFilter | None = None) -> Iterator[StoredRecord]`
- `replay(scan_filter: ScanFilter | None = None, *, mode: ReplayMode = ReplayMode.STRICT) -> ReplayResult`
- `iter_replay(scan_filter: ScanFilter | None = None, *, mode: ReplayMode = ReplayMode.STRICT) -> Iterator[StoredRecord]`
- `check_integrity() -> IntegrityReport`
- `export_jsonl(destination: str | Path, scan_filter: ScanFilter | None = None, *, mode: ReplayMode = ReplayMode.STRICT) -> ReplayResult`
- `rebuild_indexes() -> RepairReport`
- `repair_truncated_tails() -> RepairReport`

### `StreamStore.open(...)`

`StreamStore.open(config)`은 공개 생성자 스타일 진입점입니다.

매개변수:

- `config`
  - 필수 `StoreConfig`

보고:

- `StreamStore`

참고:

- 저장소를 하나의 로컬 루트 경로에 바인딩합니다.
- 외관 뒤의 내부 서비스 표면을 초기화합니다.
- 상점 인스턴스를 생성하는 일반적인 방법입니다

### `store.config`

`store.config`은 저장소에 첨부된 해결된 `StoreConfig`을 반환합니다.

일반적인 용도:

```python
print(store.config.root_path)
print(store.config.durability_mode)
```

이는 상위 수준 애플리케이션 코드가 로그에 저장소 ID 또는 구성을 노출하려고 할 때 유용합니다.

## 쓰기 방법

### `store.append(record)`

하나의 정식 레코드를 로컬 저장소에 추가합니다.

서명:

```python
append(record: object) -> AppendResult
```

매개변수:

- `record`
  - 하나의 표준 레코드형 매핑

보고:

- `AppendResult`

레이즈:

- `RecordValidationError`
  - 입력이 유효한 표준 레코드가 아닌 경우
- `AppendError`
  - 추가 실행이 실패하는 경우

운영상의 의미:

- 하나의 레코드를 검증하고 정규화합니다.
- 표준 세그먼트 기록에 추가합니다.
- 인덱싱이 활성화된 경우 도우미 인덱스를 업데이트합니다.
- 단순한 부울 대신 구조화된 승인 메타데이터를 반환합니다.

예:

```python
result = store.append(record)
print(result.success)
print(result.accepted_count)
print(result.accepted[0].durability_status)
```

### `store.append_many(records)`

여러 표준 레코드를 순서대로 추가합니다.

서명:

```python
append_many(records: list[object] | tuple[object, ...]) -> AppendResult
```

매개변수:

- `records`
  - 정규 레코드와 유사한 매핑의 정렬된 배치

보고:

- `AppendResult`

운영상의 의미:

- 허용된 레코드 전체에 걸쳐 추가 순서를 유지합니다.
- `accepted`에서 레코드별 영수증을 반환합니다.
- `rejected`을(를) 통해 거부 세부정보를 보고할 수 있습니다.

`append_many()`은 숨겨진 재작성 또는 트랜잭션 추상화가 아니라 구조화된 일괄 추가 표면으로 해석되어야 하기 때문에 이는 중요합니다.

전체 쓰기 의미를 보려면 [쓰기 경로](/Users/eastl/MLObservability/Stream/docs/ko/write-path.md)을 읽으세요.

## 읽기 방법

### `store.scan(scan_filter=None)`

저장된 기록을 직접 스캔합니다.

서명:

```python
scan(scan_filter: ScanFilter | None = None) -> Iterator[StoredRecord]
```

매개변수:

- `scan_filter`
  - 선택사항 `ScanFilter`

보고:

- `StoredRecord`의 반복자

운영상의 의미:

- 직접 저장된 기록 검사 경로
- 추가 순서 유지
- 간단한 실제 사례에서는 도우미 인덱스를 사용할 수 있습니다.
- 재생 경고 또는 재생 상태 해석을 추가하지 않습니다.

예:

```python
for stored in store.scan(ScanFilter(run_ref="run/eval-1")):
    print(stored.sequence, stored.record["record_type"])
```

### `store.replay(scan_filter=None, *, mode=ReplayMode.STRICT)`

명시적인 재생 의미에 따라 저장된 기록을 재생합니다.

서명:

```python
replay(
    scan_filter: ScanFilter | None = None,
    *,
    mode: ReplayMode = ReplayMode.STRICT,
) -> ReplayResult
```

매개변수:

- `scan_filter`
  - 선택사항 `ScanFilter`
- `mode`
  - `ReplayMode.STRICT` 또는 `ReplayMode.TOLERANT`

보고:

- `ReplayResult`

레이즈:

- `ReplayError`
  - 저장소가 손상되어 엄격한 재생이 허용되지 않는 경우

운영상의 의미:

- 무결성 인식 기록 읽기를 수행합니다.
- 관련되는 경우 표준 레코드와 재생 경고 및 알려진 간격을 반환합니다.
- 원시 검색보다 안전이 더 중요할 때 읽을 때 적합한 표면입니다.

### `store.iter_replay(scan_filter=None, *, mode=ReplayMode.STRICT)`

재생의 반복자 형식입니다.

서명:

```python
iter_replay(
    scan_filter: ScanFilter | None = None,
    *,
    mode: ReplayMode = ReplayMode.STRICT,
) -> Iterator[StoredRecord]
```

매개변수:

- `scan_filter`
  - 선택사항 `ScanFilter`
- `mode`
  - `ReplayMode.STRICT` 또는 `ReplayMode.TOLERANT`

보고:

- `StoredRecord`의 반복자

레이즈:

- `ReplayError`
  - 엄격한 재생이 허용되지 않는 경우

운영상의 의미:

- 전체 `ReplayResult.records` 튜플을 먼저 구체화하지 않고 재생 의미를 원할 때 유용합니다.
- 여전히 `replay()`과 동일한 무결성 게이트를 준수합니다.

### `store.export_jsonl(destination, scan_filter=None, *, mode=ReplayMode.STRICT)`

재생 기록을 JSONL로 내보냅니다.

서명:

```python
export_jsonl(
    destination: str | Path,
    scan_filter: ScanFilter | None = None,
    *,
    mode: ReplayMode = ReplayMode.STRICT,
) -> ReplayResult
```

매개변수:

- `destination`
  - 출력 파일 경로
- `scan_filter`
  - 선택사항 `ScanFilter`
- `mode`
  - 내보내기에 사용되는 재생 모드

보고:

- `ReplayResult`

운영상의 의미:

- 재생을 우회하는 대신 재생된 기록을 내보냅니다.
- 재생 의미를 명시적으로 유지합니다.
- JSONL을 기대하는 다운스트림 도구에 유용합니다.

전체 스캔/재생/내보내기 관계에 대해서는 [읽기 경로](/Users/eastl/MLObservability/Stream/docs/ko/read-path.md)을(를) 읽어보세요.

## 무결성 및 유지 관리 방법

### `store.check_integrity()`

로컬 저장소에서 무결성 검사를 실행하세요.

서명:

```python
check_integrity() -> IntegrityReport
```

보고:

- `IntegrityReport`

레이즈:

- `IntegrityError`
  - 무결성 처리가 예기치 않게 실패하는 경우

운영상의 의미:

- 매니페스트 및 세그먼트 기록을 검사합니다.
- 건강을 `healthy`, `degraded` 또는 `corrupted`로 분류합니다.
- 문제 세부정보 및 권장사항 반환

### `store.rebuild_indexes()`

표준 세그먼트에서 파생 도우미 인덱스를 다시 작성합니다.

서명:

```python
rebuild_indexes() -> RepairReport
```

보고:

- `RepairReport`

운영상의 의미:

- 파생 인덱스를 재구성합니다.
- 재구축 중에 확인된 무결성 상태를 보고합니다.
- 기본 저장소가 이미 손상된 경우 경고할 수 있습니다.

### `store.repair_truncated_tails()`

알려진 잘린 꼬리 손상을 복구하고 나중에 파생 인덱스를 다시 빌드합니다.

서명:

```python
repair_truncated_tails() -> RepairReport
```

보고:

- `RepairReport`

운영상의 의미:

- 수정하기 전에 손상된 세그먼트 파일을 격리합니다.
- 손상된 꼬리를 손질합니다. 매장에서는 안전하게 처리하는 방법을 알고 있습니다.
- 매니페스트 프론티어를 다시 계산합니다.
- 복구 후 인덱스를 다시 작성합니다.

의도적으로 좁게 만든 것입니다. 범용 히스토리 재작성 API로 취급되어서는 안 됩니다.

생산 수리 작업 흐름을 구축하기 전에 [무결성과 복구](/Users/eastl/MLObservability/Stream/docs/ko/integrity-and-repair.md)을(를) 읽어보세요.

## 구성 모델

### `stream.StoreConfig`

`StoreConfig`은 하나의 로컬 저장소에 대한 구성 데이터 클래스입니다.

서명:

```python
StoreConfig(
    root_path: Path,
    max_segment_bytes: int = 1_048_576,
    durability_mode: DurabilityMode = DurabilityMode.FSYNC,
    layout_mode: LayoutMode = LayoutMode.JSONL_SEGMENTS,
    layout_version: str = "1",
    enable_indexes: bool = True,
)
```

전지:

- `root_path`
  - 필수 저장소 루트 경로
- `max_segment_bytes`
  - 세그먼트 롤오버 임계값
- `durability_mode`
  - 내구성 동작 추가
- `layout_mode`
  - 현재 `jsonl_segments`
- `layout_version`
  - 현재 `"1"`
- `enable_indexes`
  - 파생지수 유지 여부

확인:

- `max_segment_bytes <= 0`인 경우 `ValueError` 발생

일반적인 용도:

```python
config = StoreConfig(
    root_path=Path(".stream-store"),
    durability_mode=DurabilityMode.FSYNC,
    enable_indexes=True,
)
```

### `stream.DurabilityMode`

추가 내구성 동작을 제어하는 ​​열거형입니다.

값:

- `DurabilityMode.FLUSH`
- `DurabilityMode.FSYNC`

운영상의 의미:

- `FLUSH`은 버퍼링된 파일 콘텐츠가 Python에서 OS로 플러시됨을 의미합니다.
- `FSYNC`은 더 강한 내구성 단계가 요청되었음을 의미합니다.

### `stream.LayoutMode`

저장소 레이아웃 모드를 제어하는 ​​열거형입니다.

값:

- `LayoutMode.JSONL_SEGMENTS`

현재 라이브러리는 추가 지향 JSONL 세그먼트 저장소를 중심으로 의도적으로 범위가 좁기 때문에 `Stream`은 하나의 공개 레이아웃 모드를 노출합니다.

## 결과 및 필터 모델

이러한 모델은 `stream` 및 `stream.models`을 통해 공개적으로 내보내집니다.

### `stream.AppendReceipt`

허용되는 추가 항목 하나를 설명하는 데이터 클래스입니다.

전지:

- `sequence`
- `segment_id`
- `offset`
- `record_ref`
- `record_type`
- `run_ref`
- `durability_status`

이 모델은 `AppendResult.accepted` 내부에 반환됩니다.

### `stream.AppendResult`

단일 추가 작업 또는 일괄 추가의 결과를 설명하는 데이터 클래스입니다.

전지:

- `accepted`
  - `AppendReceipt`의 튜플
- `rejected`
  - 거절 메시지의 튜플
- `durability_status`
  - 총 내구성 상태
- `durable_count`
  - 내구성 목표에 도달한 레코드 수

계산된 속성:

- `accepted_count`
- `rejected_count`
- `success`

운영 참고 사항:

- `success`은 아무것도 거부되지 않았음을 의미합니다.
- `accepted_count` 및 `rejected_count`은 부분 배치 승인을 검사하는 가장 빠른 방법입니다.

### `stream.DurabilityStatus`

허용된 레코드에 대한 추가 내구성의 가시성을 설명하는 열거형입니다.

값:

- `DurabilityStatus.ACCEPTED`
- `DurabilityStatus.FLUSHED`
- `DurabilityStatus.FSYNCED`

### `stream.ScanFilter`

일반적인 스캔 및 재생 필터를 위한 데이터 클래스입니다.

전지:

- `run_ref`
- `stage_execution_ref`
- `record_type`
- `start_time`
- `end_time`

일반적인 용도:

```python
scan_filter = ScanFilter(
    run_ref="run/eval-1",
    record_type="metric",
)
```

### `stream.StoredRecord`

하나의 저장된 레코드와 배치 메타데이터를 설명하는 데이터 클래스입니다.

전지:

- `sequence`
- `segment_id`
- `offset`
- `appended_at`
- `record`

`scan()` 및 `iter_replay()`이 반환한 결과 모델입니다.

### `stream.ReplayMode`

재생 의미 체계를 제어하는 ​​열거형입니다.

값:

- `ReplayMode.STRICT`
- `ReplayMode.TOLERANT`

운영상의 의미:

- `STRICT`은(는) 손상된 저장소 재생을 거부합니다.
- `TOLERANT`을(를) 사용하면 명시적인 경고 및 알려진 공백과 함께 손상된 기록을 읽을 수 있습니다.

### `stream.ReplayResult`

재생 출력을 설명하는 데이터 클래스입니다.

전지:

- `records`
  - `StoredRecord`의 튜플
- `record_count`
  - 재생된 레코드 수
- `mode`
  - 사용된 재생 모드
- `warnings`
  - 경고 재생
- `known_gaps`
  - 명백한 손상된 기록 공백

일반적인 용도:

```python
replay = store.replay(ScanFilter(run_ref="run/eval-1"), mode=ReplayMode.STRICT)
print(replay.record_count)
print(replay.warnings)
```

### `stream.IntegrityState`

상위 수준의 저장소 상태를 설명하는 열거형입니다.

값:

- `IntegrityState.HEALTHY`
- `IntegrityState.DEGRADED`
- `IntegrityState.CORRUPTED`

### `stream.IntegrityIssue`

하나의 무결성 결과를 설명하는 데이터 클래스입니다.

전지:

- `severity`
- `code`
- `message`
- `segment_id`
- `line_number`

### `stream.IntegrityReport`

`check_integrity()`의 결과를 설명하는 데이터 클래스입니다.

전지:

- `healthy`
- `issues`
- `segment_count`
- `record_count`
- `state`
- `recommendations`

운영 참고 사항:

- `healthy`은 최상위 요약입니다.
- `state`은 운영자 결정을 위한 상위 신호 분류입니다.

### `stream.RepairReport`

`rebuild_indexes()` 또는 `repair_truncated_tails()`의 결과를 설명하는 데이터 클래스입니다.

전지:

- `success`
- `repaired_segments`
- `quarantined_paths`
- `rebuilt_indexes`
- `integrity_state`
- `notes`
- `warnings`

이는 의도적으로 두 유지 관리 표면 모두에 사용되므로 운영자는 하나의 결과 형태를 사용하여 유지 관리 결과를 비교할 수 있습니다.

## 유형화된 예외

이러한 예외는 `stream` 및 `stream.exceptions`을 통해 공개적으로 내보내집니다.

### `stream.StreamError`

`Stream`에 대한 기본 예외입니다.

### `stream.LayoutError`

레이아웃 메타데이터 또는 세그먼트 상태가 유효하지 않을 때 발생합니다.

### `stream.RecordValidationError`

입력 레코드가 유효한 표준 레코드가 아닐 때 발생합니다.

일반적인 발신자는 `append()` 및 `append_many()`쯤에 이를 예상해야 합니다.

### `stream.AppendError`

추가 실행이 실패할 때 발생합니다.

### `stream.ReplayError`

재생을 안전하게 진행할 수 없을 때 발생합니다.

현재 가장 중요한 사례는 손상된 저장소에 대한 엄격한 재생입니다.

### `stream.IntegrityError`

무결성 처리가 예기치 않게 실패할 때 발생합니다.

## 최소 가져오기 패턴

대부분의 호출자에게는 이러한 패턴 중 하나만 필요합니다.

최소 매장 사용량:

```python
from pathlib import Path

from stream import ScanFilter, StoreConfig, StreamStore

store = StreamStore.open(StoreConfig(root_path=Path(".stream-store")))

for stored in store.scan(ScanFilter(run_ref="run/eval-1")):
    print(stored.sequence, stored.record["record_type"])
```

재생 지향 사용법:

```python
from stream import ReplayMode, ScanFilter

replay = store.replay(
    ScanFilter(run_ref="run/eval-1"),
    mode=ReplayMode.STRICT,
)
```

무결성 지향 사용법:

```python
from stream import StreamStore

report = store.check_integrity()
print(report.state)
print(report.recommendations)
```

## 다음에 읽을 페이지

- 가장 작은 엔드투엔드 흐름을 보려면 [시작하기](/Users/eastl/MLObservability/Stream/docs/ko/getting-started.md)을 읽으세요.
- 추가 의미 및 내구성 동작에 대해서는 [쓰기 경로](/Users/eastl/MLObservability/Stream/docs/ko/write-path.md)을 읽어보세요.
- 검색, 재생 및 내보내기 의미에 대해서는 [읽기 경로](/Users/eastl/MLObservability/Stream/docs/ko/read-path.md)을(를) 읽으세요.
- 유지 관리 및 운영자 해석은 [무결성과 복구](/Users/eastl/MLObservability/Stream/docs/ko/integrity-and-repair.md)을(를) 읽어보세요.
