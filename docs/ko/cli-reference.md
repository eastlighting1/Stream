# CLI 레퍼런스

[사용자 가이드 홈](/Users/eastl/MLObservability/Stream/docs/USER_GUIDE.ko.md)

이 페이지는 `Stream`에 대한 명령줄 참조입니다. 설치된 `stream-cli` 진입점, 사용 가능한 하위 명령, 공유 필터 옵션, JSON 출력 형태 및 각 명령의 작동 의미를 문서화합니다.

작업 중심의 설명을 먼저 원한다면 이 개념 페이지 이전에 개념 페이지를 읽어보세요. 어떤 종류의 저장 작업이 필요한지 이미 알고 있고 정확한 명령 모양을 원한다면 이 페이지를 열어두세요.

## CLI 진입점

`Stream`은 [`pyproject.toml`](/Users/eastl/MLObservability/Stream/pyproject.toml)에 선언된 콘솔 스크립트를 통해 CLI를 노출합니다.

- `stream-cli`

모듈을 통해 동일한 진입점을 호출할 수도 있습니다.

- `python -m stream.cli`

이 페이지의 예에서는 `stream-cli`을 사용하지만 하위 명령과 옵션은 두 형식 모두 동일합니다.

## 글로벌 형태

모든 명령은 필수 저장소 경로로 시작됩니다.

```bash
stream-cli --store .stream-store <command> [options]
```

전역 인수:

- `--store`
  - 필수의
  - 로컬 `Stream` 저장소 루트 경로

CLI는 `StreamStore.open(StoreConfig(root_path=Path(args.store)))`을 통해 저장소를 열므로 명령줄은 항상 한 번에 하나의 로컬 저장소 루트에서 작동합니다.

## 공유 필터 옵션

`scan`, `replay` 및 `export` 명령은 모두 내부적으로 동일한 `ScanFilter` 개체를 빌드합니다.

공유 필터 옵션:

- `--run-ref`
  - 표준 `run_ref` 기준으로 필터링
- `--stage-ref`
  - 표준 `stage_execution_ref` 기준으로 필터링
- `--record-type`
  - 표준 `record_type` 기준으로 필터링
- `--start-time`
  - 시간 기반 필터링의 하한
- `--end-time`
  - 시간 기반 필터링의 상한

중요한 점은 CLI 필터링이 임의적이기보다는 의도적으로 실용적이라는 것입니다. CLI는 임시 쿼리 언어 기능이 아닌 일반적인 검사 및 재생 질문을 중심으로 설계되었습니다.

## 공통 규칙

여러 가지 동작이 명령 전체에서 일관됩니다.

- 명령 출력은 JSON 또는 줄 기반 JSON입니다.
- 표준 기록은 여전히 ​​명령 출력이 아닌 `segments/`에 있습니다.
- 재생 지향 명령은 명시적인 재생 모드 의미를 사용합니다.
- 유지 관리 명령은 운영 위험을 숨기지 않고 상태를 보고합니다.

CLI는 매장 자체 옆에 두 번째 스토리지 모델을 개발하기 위한 것이 아니라 검사 및 운영을 위한 것이기 때문에 이것이 중요합니다.

## `scan`

저장된 레코드를 직접 일치시키려면 `scan`을(를) 사용하세요.

기본 형태:

```bash
stream-cli --store .stream-store scan [filters]
```

지원되는 옵션:

- `--run-ref`
- `--stage-ref`
- `--record-type`
- `--start-time`
- `--end-time`

예:

```bash
stream-cli --store .stream-store scan --run-ref run/eval-1
```

출력 동작:

- 일치하는 저장된 레코드당 하나의 JSON 객체를 인쇄합니다.
- 전체 `StoredRecord` 봉투가 아닌 `record.record`을 인쇄합니다.
- 추가 순서로 레코드를 반환합니다.

예제 출력:

```json
{"completeness_marker":"complete","correlation_refs":{"trace_id":"trace/eval-1"},"degradation_marker":"none","observed_at":"2026-04-03T00:10:00Z","operation_context_ref":"op/evaluate-open","payload":{"event_key":"evaluation.started","level":"info","message":"Evaluation started."},"producer_ref":"scribe.python.local","record_ref":"record/eval-start","record_type":"structured_event","recorded_at":"2026-04-03T00:10:00Z","run_ref":"run/eval-1","schema_version":"1.0.0","stage_execution_ref":"stage/evaluate"}
```

`scan`에 포함되지 않는 것:

- `sequence`
- `segment_id`
- `offset`
- 경고 재생
- 무결성 분류

그것은 의도적인 것입니다. `scan`은 무결성 인식 요약 화면이 아닌 직접 저장된 기록 검사 경로입니다.

직접 스캔과 재생 간의 개념적 차이가 필요한 경우 [읽기 경로](/Users/eastl/MLObservability/Stream/docs/ko/read-path.md)을(를) 읽어보세요.

## `replay`

저장된 기록의 무결성 인식 읽기를 원할 경우 `replay`을(를) 사용하세요.

기본 형태:

```bash
stream-cli --store .stream-store replay [filters] [--mode strict|tolerant]
```

지원되는 옵션:

- `--run-ref`
- `--stage-ref`
- `--record-type`
- `--start-time`
- `--end-time`
- `--mode`
  - 허용되는 값: `strict`, `tolerant`
  - 기본값: `strict`

예:

```bash
stream-cli --store .stream-store replay --run-ref run/eval-1 --mode strict
```

출력 형태:

```json
{
  "known_gaps": [],
  "mode": "strict",
  "record_count": 1,
  "records": [
    {
      "completeness_marker": "complete",
      "correlation_refs": {"trace_id": "trace/eval-1"},
      "degradation_marker": "none",
      "observed_at": "2026-04-03T00:10:00Z",
      "operation_context_ref": "op/evaluate-open",
      "payload": {
        "event_key": "evaluation.started",
        "level": "info",
        "message": "Evaluation started."
      },
      "producer_ref": "scribe.python.local",
      "record_ref": "record/eval-start",
      "record_type": "structured_event",
      "recorded_at": "2026-04-03T00:10:00Z",
      "run_ref": "run/eval-1",
      "schema_version": "1.0.0",
      "stage_execution_ref": "stage/evaluate"
    }
  ],
  "warnings": []
}
```

출력 필드:

- `mode`
  - 명령에서 사용되는 재생 모드
- `record_count`
  - 반환된 레코드 수
- `warnings`
  - 일반적으로 `tolerant` 모드에서 의미 있는 재생 경고
- `known_gaps`
  - 관용적 재생으로 인해 드러난 명백한 손상된 기록 격차
- `records`
  - 정식 레코드 페이로드만

운영 참고 사항:

- `strict` 저장소가 손상되면 재생이 실패할 수 있습니다.
- `tolerant` 재생을 통해 명시적인 경고와 함께 손상된 기록을 읽을 수 있습니다.
- 재생 출력은 `StoredRecord` 배치 메타데이터가 아닌 표준 레코드 매핑을 반환합니다.

재생은 단순한 검색이 아니라 안전한 해석에 관한 것이기 때문에 이것이 중요합니다.

`warnings`, `known_gaps`의 전체 의미와 엄격한 재생 실패가 필요한 경우 [무결성과 복구](/Users/eastl/MLObservability/Stream/docs/ko/integrity-and-repair.md)을 읽으세요.

## `export`

다른 도구에 JSONL로 재생 기록이 필요한 경우 `export`을 사용하세요.

기본 형태:

```bash
stream-cli --store .stream-store export --output exports/run-eval-1.jsonl [filters] [--mode strict|tolerant]
```

지원되는 옵션:

- `--run-ref`
- `--stage-ref`
- `--record-type`
- `--start-time`
- `--end-time`
- `--mode`
  - 허용되는 값: `strict`, `tolerant`
  - 기본값: `strict`
- `--output`
  - 필수 대상 경로

예:

```bash
stream-cli --store .stream-store export --run-ref run/eval-1 --mode strict --output exports/run-eval-1.jsonl
```

출력 형태:

```json
{"mode":"strict","output":"exports/run-eval-1.jsonl","record_count":1}
```

출력 필드:

- `output`
  - 작성된 대상 경로
- `mode`
  - 내보내기에 사용되는 재생 모드
- `record_count`
  - 내보낸 레코드 수

운영 참고 사항:

- 내보내기는 재생 의미론을 기반으로 구축되었습니다.
- 수출은 새로운 정보 소스를 생성하지 않습니다.
- 엄격한 재생이 정당화되지 않는 경우 내보내기는 해당 위험을 자동으로 평면화해서는 안 됩니다.

정식 기록은 내보내기 파일이 아닌 여전히 저장소에 있습니다.

## `integrity`

지역 매장에 대한 교환원용 건강 보고서가 필요한 경우 `integrity`을(를) 사용하세요.

기본 형태:

```bash
stream-cli --store .stream-store integrity
```

예:

```bash
stream-cli --store .stream-store integrity
```

출력 형태:

```json
{
  "healthy": true,
  "issues": [],
  "record_count": 1,
  "recommendations": [],
  "segment_count": 1,
  "state": "healthy"
}
```

출력 필드:

- `healthy`
  - 최상위 부울 요약
- `state`
  - `healthy`, `degraded` 또는 `corrupted`
- `segment_count`
  - 관찰된 세그먼트 수
- `record_count`
  - 성공적으로 읽은 표준 레코드 수
- `issues`
  - 세부 이슈 목록
- `recommendations`
  - 다음 조치 제안

각 호는 `IntegrityIssue`에서 직렬화되며 다음을 포함할 수 있습니다.

- `severity`
- `code`
- `message`
- `segment_id`
- `line_number`

이 명령은 상점이 의심스러울 때 시작하기에 적합한 장소입니다. 일반적으로 `rebuild-indexes` 또는 `repair` 앞에 와야 합니다.

## `rebuild-indexes`

정규 세그먼트에서 파생 도우미 인덱스를 재구성하려면 `rebuild-indexes`을(를) 사용하세요.

기본 형태:

```bash
stream-cli --store .stream-store rebuild-indexes
```

예:

```bash
stream-cli --store .stream-store rebuild-indexes
```

출력 형태:

```json
{
  "integrity_state": "healthy",
  "notes": ["Derivative indexes were rebuilt from canonical segments."],
  "quarantined_paths": [],
  "rebuilt_indexes": true,
  "repaired_segments": [],
  "success": true,
  "warnings": []
}
```

출력 필드:

- `success`
  - `true` 재구축 시 저장소가 정상이었을 때
- `repaired_segments`
  - 재구축 전용 실행의 경우 항상 비어 있음
- `quarantined_paths`
  - 재구축 전용 실행의 경우 항상 비어 있음
- `rebuilt_indexes`
  - 인덱스 재구축이 발생했는지 여부
- `integrity_state`
  - 재구축 중에 관찰된 무결성 상태
- `notes`
  - 설명 메모
- `warnings`
  - 손상된 매장을 재건축하는 등의 경고

운영 참고 사항:

- 재구축은 파생 인덱스에만 영향을 미칩니다.
- 정식 저장소에 무결성 문제가 있는 경우 다시 빌드하면 계속 경고할 수 있습니다.
- 재구축은 손상된 표준 기록을 건강하게 만들지 않습니다.

이는 도우미 상태 드리프트가 문제인 경우 올바른 첫 번째 유지 관리 작업입니다.

## `repair`

잘린 세그먼트 테일을 복구하고 나중에 파생 인덱스를 다시 작성하려면 `repair`을(를) 사용하세요.

기본 형태:

```bash
stream-cli --store .stream-store repair
```

예:

```bash
stream-cli --store .stream-store repair
```

출력 형태:

```json
{
  "integrity_state": "healthy",
  "notes": [
    "trimmed damaged tail from segment 3",
    "Derivative indexes were rebuilt from canonical segments."
  ],
  "quarantined_paths": [".stream-store/quarantine/segment-000003.jsonl"],
  "rebuilt_indexes": true,
  "repaired_segments": [3],
  "success": true,
  "warnings": []
}
```

출력 필드:

- `success`
  - 수리 후 매장이 건강했는지 여부
- `repaired_segments`
  - 손상된 꼬리가 잘려진 세그먼트
- `quarantined_paths`
  - `quarantine/`에 기록된 백업 복사본
- `rebuilt_indexes`
  - 복구 후 인덱스가 다시 작성되었는지 여부
- `integrity_state`
  - 수리 통과 후 결과 무결성 상태
- `notes`
  - 작업 요약
- `warnings`
  - 수리 또는 수리 후 경고

운영 참고 사항:

- 이 명령은 의도적으로 범위를 좁혔습니다
- 상점에서 처리 방법을 알고 있는 잘린 JSON 꼬리를 복구합니다.
- 범용 히스토리 다시 쓰기 명령이 아닙니다.
- `rebuild-indexes`보다 더 심각하게 느껴질 것입니다.

프로덕션 작업 흐름에서 사용하기 전에 [무결성과 복구](/Users/eastl/MLObservability/Stream/docs/ko/integrity-and-repair.md)을 읽어보세요.

## 종료 동작

CLI는 현재 다음을 반환합니다.

- 성공적인 명령 실행을 위한 `0`
- `2` argparse가 잘못된 명령 형태를 거부하는 경우

다른 오류는 다음과 같은 일반적인 Python 오류로 나타납니다.

- `ReplayError` 엄격한 재생이 허용되지 않는 경우
- 라이브러리 동작이 향후 쓰기 지향 CLI 명령으로 확장되는 경우 `RecordValidationError` 또는 `AppendError`
- 경로가 유효하지 않거나 쓸 수 없는 경우 파일 시스템 관련 예외

중요한 점은 명령 성공은 명령이 완료되었음을 의미한다는 것입니다. 자동으로 매장이 건강하다는 의미는 아닙니다. 이를 위해 `integrity`을 사용하고 결과 페이로드를 읽으십시오.

## 다음에 읽을 페이지

- `scan`, `replay`, `export`의 차이점을 알아보려면 [읽기 경로](/Users/eastl/MLObservability/Stream/docs/ko/read-path.md)을 읽어보세요.
- CLI가 작동하는 대상에 대해서는 [레이아웃과 저장소](/Users/eastl/MLObservability/Stream/docs/ko/layout-and-storage.md)을(를) 읽어보세요.
- 상태 확인, 재구축 및 수리의 작동 의미는 [무결성과 복구](/Users/eastl/MLObservability/Stream/docs/ko/integrity-and-repair.md)을(를) 읽어보세요.
