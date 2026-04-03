# Stream 사용자 가이드 (KO)

`Stream` 문서는 먼저 하나의 실용적인 질문에 답해야 합니다. "이 라이브러리를 로컬 Python workflow에서 append-oriented canonical record store로 어떻게 사용해야 하는가?" 모든 저장소 세부 사항을 읽기 전에, `Stream`이 무엇을 소유하고 무엇을 소유하지 않는지, 그리고 일반적인 write-read-repair 흐름이 실제 사용에서 어떻게 느껴져야 하는지를 먼저 이해하는 편이 더 중요합니다.

## 여기서부터 시작하세요

- [시작하기](ko/getting-started.md)
- [멘탈 모델](ko/mental-model.md)
- [쓰기 경로](ko/write-path.md)
- [읽기 경로](ko/read-path.md)
- [레이아웃과 저장소](ko/layout-and-storage.md)
- [무결성과 복구](ko/integrity-and-repair.md)
- [CLI 레퍼런스](ko/cli-reference.md)
- [API 레퍼런스](ko/api-reference.md)
- [예제](ko/examples.md)
- [FAQ](ko/faq.md)

## 권장 읽기 순서

1. 개별 작업으로 들어가기 전에 문서 전체 지도를 보고 싶다면 [한국어 문서 홈](USER_GUIDE.ko.md)부터 읽으세요.
2. 가장 작은 성공적인 `StreamStore` 흐름을 보려면 [시작하기](ko/getting-started.md)를 읽으세요.
3. `Stream`이 무엇을 소유하고, 무엇이 canonical truth이며, 무엇이 derivative helper state인지 이해하려면 [멘탈 모델](ko/mental-model.md)을 읽으세요.
4. 허용되는 record, append semantics, batching, validation boundary를 이해하려면 [쓰기 경로](ko/write-path.md)를 읽으세요.
5. `scan`, `replay`, tolerant read, JSONL export의 차이를 이해하려면 [읽기 경로](ko/read-path.md)를 읽으세요.
6. `manifest.json`, `segments/*.jsonl`, derivative index, 그리고 디스크 위 trust boundary를 이해하려면 [레이아웃과 저장소](ko/layout-and-storage.md)를 읽으세요.
7. corruption 해석, index rebuild, truncated tail repair가 필요할 때는 [무결성과 복구](ko/integrity-and-repair.md)를 읽으세요.
8. 정확한 명령줄 형태와 출력 payload가 필요하면 [CLI 레퍼런스](ko/cli-reference.md)를 사용하세요.
9. 정확한 공개 Python import, 메서드, 결과 모델, 예외가 필요하면 [API 레퍼런스](ko/api-reference.md)를 사용하세요.
10. 주요 개념이 익숙해진 뒤에는 [예제](ko/examples.md)와 [FAQ](ko/faq.md)를 빠른 후속 참고 문서로 사용하세요.

`Stream`이 처음이라면 보통 `시작하기`, `멘탈 모델`, `쓰기 경로`만 먼저 읽어도 올바르게 사용을 시작하기에 충분합니다. 저장 구조와 복구 문서는 store가 장난감 예제가 아니라 실제 운영 history를 맡기 시작할 때 더 중요해집니다.

## 이 문서군이 최적화하는 것

`Stream`은 metadata anchor store도 아니고, analytics layer도 아니며, visualization surface도 아닙니다. `Stream`은 canonical observability record를 위한 append-oriented local store입니다. 그래서 문서에서 가장 중요한 질문은 대개 다음과 같습니다.

- application이나 experiment workflow 안에서 `StreamStore`를 어디에 두어야 하는가
- 무엇을 canonical history로 append해야 하고, 무엇은 store 밖에 두어야 하는가
- 언제 `scan`을 쓰고 언제 `replay`를 써야 하는가
- tolerant replay의 warning과 known gap을 어떻게 해석해야 하는가
- 디스크 위 어떤 상태가 canonical이고, 어떤 상태가 rebuild 가능한 helper state인가
- 언제 index rebuild가 안전하고, 언제 실제 repair 단계가 필요한가

그래서 이 문서들은 단순히 모듈 이름을 나열하기보다 저장 동작과 운영 해석을 중심으로 구성됩니다.

## Stream이 하는 일

큰 그림에서 `Stream`은 코드가 다음 여섯 가지를 하도록 돕습니다.

- canonical record를 하나씩 또는 배치로 append하기
- append 순서를 로컬 JSONL segment history로 보존하기
- run, stage, record type, time 같은 실용적인 filter로 저장된 record를 scan하기
- canonical history를 `strict` 또는 `tolerant` 모드로 replay하기
- downstream inspection을 위해 replay 결과를 JSONL로 export하기
- corruption을 진단하고 알려진 damaged-tail case를 repair하면서 canonical truth 경계를 분명하게 유지하기

정상적인 사용 패턴은 대략 다음과 같습니다.

```text
create StreamStore
  -> append canonical records during execution
    -> scan or replay local history for inspection
      -> export replayed history when another tool needs JSONL output
        -> run integrity checks if corruption or drift is suspected
          -> rebuild indexes or repair truncated tails only when needed
```

이 흐름은 범용 이벤트 데이터베이스보다 훨씬 더 좁은 목적을 가집니다. `Stream`은 주변 스택이 바뀌더라도 이해 가능한 local record history를 유지하는 데 최적화되어 있습니다.

## 문서를 어떻게 나눴는가

현재 문서들은 내부 패키지 구조가 아니라 사용자 작업 기준으로 나뉘어 있습니다.

- `시작하기`
  - 첫 append, scan, replay, CLI 흐름
- `멘탈 모델`
  - 역할, 경계, source-of-truth 규칙, 저장 책임
- `쓰기 경로`
  - 허용되는 record, append 동작, batching, durability, validation
- `읽기 경로`
  - scan, replay, tolerant read, export behavior
- `레이아웃과 저장소`
  - manifest, segments, derivative index, sequence 흐름, storage trust boundary
- `무결성과 복구`
  - integrity 해석, rebuild 동작, truncated-tail 복구
- `CLI 레퍼런스`
  - 정확한 명령 형태, 옵션, 출력 payload
- `API 레퍼런스`
  - 정확한 공개 import, 메서드, 모델, 예외
- `예제`
  - 시나리오 중심 example code 진입점
- `FAQ`
  - 반복되는 운영/개념 질문에 대한 짧은 답변

이 구조는 의도된 것입니다. `Stream`에서 생기는 대부분의 혼란은 "canonical truth가 무엇인가?", "디스크에서 무엇을 믿어야 하는가?", "corruption 뒤에는 무엇을 해야 하는가?" 같은 질문에서 오지, "어느 파일에 어느 클래스가 들어 있는가?" 같은 질문에서 오지 않기 때문입니다.

## 시간이 없을 때 먼저 읽을 것

몇 분밖에 없다면 먼저 아래 세 문서를 읽으세요.

1. [시작하기](ko/getting-started.md)
2. [멘탈 모델](ko/mental-model.md)
3. [읽기 경로](ko/read-path.md)

이 세 문서만으로도 다음을 이해하기에 충분합니다.

- `Stream`의 기본 runtime shape
- canonical on-disk boundary가 어떻게 생겼는지
- append, scan, replay, export를 어떻게 구분해서 써야 하는지

## Spine 및 스택의 다른 구성요소와의 관계

`Stream`은 ML observability stack의 다른 구성요소와 맞물려 있지만, 책임은 분명합니다.

- `Spine`은 canonical record contract와 validation vocabulary를 정의합니다.
- capture-side library는 canonical record가 되는 runtime fact를 생산합니다.
- `Stream`은 그 canonical record를 local에 append 순서대로 저장하고, 그 history를 안전하게 읽고 복구할 수 있게 돕습니다.

깊은 schema 의미나 record shape semantic이 필요하다면 보통 `Spine`이 맞는 곳입니다. 반대로 local canonical history, replay behavior, corruption handling, repair-oriented store operation을 이해하고 싶다면 `Stream`이 맞는 곳입니다.

## 관련 파일

- Project README: [README.md](../README.md)
- Korean docs home: [docs/USER_GUIDE.ko.md](USER_GUIDE.ko.md)
- Package entrypoint: [src/stream/__init__.py](../src/stream/__init__.py)
- Public store API: [src/stream/api/store.py](../src/stream/api/store.py)
- CLI entrypoint: [src/stream/cli.py](../src/stream/cli.py)
- Basic example: [examples/basic_usage.py](../examples/basic_usage.py)
