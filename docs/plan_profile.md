# 네이버 카페 프로필 기반 실행 계획

## 목적

현재 `ncafe`는 Playwright의 `storage_state` JSON을 저장했다가 다시 읽는 방식으로 로그인 상태를 재사용한다. 실측 결과 이 방식은 네이버 로그인 안정성에 한계가 있었고, 사용자가 직접 로그인한 Chrome 프로필을 그대로 재사용하는 방향으로 전환이 필요하다.

이 문서는 다음 범위만 다룬다.

- 실제 Windows Chrome 프로필을 Playwright 실행 경로에 연결하는 구조
- 프록시, 프로필, 가상환경, 구글시트 설정을 일관되게 묶는 방법
- 현재 코드에서 어떤 부분을 바꿔야 하는지
- 사전 검증 항목과 실패 패턴

이 문서는 사이트의 CAPTCHA나 봇 판정을 우회하는 방법은 다루지 않는다. 대신 실행 환경의 불일치와 상태 관리 문제를 줄이는 방향으로 정리한다.

## 현재 코드 기준 진단

현재 브라우저 진입점은 `core/browser.py`에 있다.

- `BrowserState.launch_browser()`는 `playwright.chromium.launch()`를 사용한다.
- `BrowserState.new_context()`는 `browser.new_context(storage_state=..., proxy=...)`를 사용한다.
- `BrowserController.with_browser()`는 매 작업마다 브라우저를 새로 띄우고 종료 시 `context.storage_state()`를 다시 저장한다.
- `task/farm.py`의 `task_loop()`는 계정별 `self.config.ip_addr`를 그대로 proxy 인자로 넘긴다.
- `task/farm.py`의 `navigate_to_menu()`는 `state` 파일이 없으면 `core/login.py`의 `login()`으로 직접 로그인한다.

즉 현재 구조는 "브라우저 프로필 재사용"이 아니라 "새 브라우저 + JSON 상태 복원" 구조다. 사용자가 원하는 실행 모델과 다르다.

## 이번 점검에서 확인한 사실

### 1. Chrome 프로필 지정 방식

Playwright의 `launch_persistent_context()`는 Chrome의 프로필 하위 폴더를 직접 넘기면 안 된다.

- 올바른 방식: `user_data_dir`는 `C:\Users\${user}\AppData\Local\Google\Chrome\User Data` 같은 상위 디렉터리로 두고, 추가 인자로 `--profile-directory=Profile`를 전달한다.
- 잘못된 방식: `user_data_dir`에 `...\User Data\Profile`를 직접 넘기면 그 아래에 다시 `Default`가 생성되어 기존 프로필을 그대로 재사용하지 못한다.

임시 디렉터리 테스트에서도 이 차이가 그대로 재현됐다.

### 2. 프록시는 persistent context에서 정상 적용 가능

임시 Chrome 프로필로 `launch_persistent_context(..., proxy={"server": "${ip_addr}"})`를 실행한 뒤 `https://api.ipify.org?format=json`을 호출했을 때 응답 IP가 `${ip_addr}`로 확인됐다.

즉 현재 사용 중인 프록시 주소는 Playwright의 브라우저 레벨 프록시 설정으로 적용 가능하다.

### 3. 구글시트 설정은 현재 환경에서 정상 로드됨

`.secrets/config.yaml` 기준으로 읽기 시트를 로드한 결과 다음이 확인됐다.

- `${userid}` 계정 존재: 확인

즉 프로필 기반 실행으로 바꾸더라도 `Farmer`의 계정 설정 공급원 자체는 그대로 유지할 수 있다.

### 3.5. `User Data`의 기본 위치는 사이트에 직접 노출되지 않음

Chrome 프로필 루트를 `C:\Users\${user}\AppData\Local\Google\Chrome\User Data`에 두지 않고 다른 경로에 두는 것 자체가 웹사이트에 직접 노출되지는 않는다. 즉 로컬 파일 시스템 경로 그 자체가 페이지에 보이는 값은 아니다.

실무적으로 중요한 것은 경로 자체보다 다음 항목이다.

- 프로필이 얼마나 일관되게 재사용되는가
- 쿠키, 로컬 스토리지, 방문 이력 같은 상태가 충분히 쌓여 있는가
- 같은 프로필이 다른 실행과 충돌하지 않는가

따라서 자동화 전용 프로필을 위해 별도 루트 경로를 쓰는 것은 충분히 가능한 전략이다. 오히려 일반 Chrome 생활용 프로필과 충돌하지 않는다는 장점이 크다.

### 4. Chrome 창을 닫아도 프로세스가 남을 수 있음

사용자가 `Profile` 창을 닫은 뒤에도 `chrome.exe`가 여러 개 남아 있었다. 실제 프로세스 트리를 확인해 보니 Chrome 루트 브라우저 프로세스는 다음과 같이 떠 있었다.

- 루트 프로세스 예시: `chrome.exe --no-startup-window`
- 자식 프로세스 예시: crashpad, renderer, utility
- 관찰 결과: 실행 중인 프로세스 어디에서도 `--profile-directory=Profile` 같은 표식은 보이지 않았다.

즉 현재 Windows Chrome은 `Profile`만 따로 독립 실행 중이라고 식별되지 않았고, 같은 `User Data` 루트를 공유하는 모든 프로필 창이 사실상 한 Chrome 인스턴스 트리에 매달려 있었다.

실무 결론:

- `Profile`만 닫아서는 충분하지 않을 수 있다.
- 같은 `C:\Users\${user}\AppData\Local\Google\Chrome\User Data` 루트를 쓰는 다른 프로필 창도 모두 닫아야 한다.
- 강제 종료가 필요하다면 프로필 단위가 아니라 `User Data` 루트 단위로 종료해야 한다.

따라서 실제 프로필을 직접 여는 경로는 반드시 사전 점검이 필요하다.

### 5. 현재 모바일 강제 설정은 기존 `Profile`와 충돌 가능성이 큼

현재 설정은 다음과 같다.

- `device: "Galaxy S24"`
- `mobile: true`

하지만 현재 재사용 대상으로 잡은 `Profile`는 Windows Chrome 데스크톱 프로필이다. 데스크톱 프로필을 띄우면서 Playwright에서 Galaxy S24 에뮬레이션을 덮어쓰는 구성은 일관성이 떨어진다.

핵심 판단:

- 기존 `Profile`는 데스크톱 기준 프로필로 보는 편이 맞다.
- Farmer가 계속 모바일 DOM 기준으로 동작한다면, `Profile`를 억지로 재활용하기보다 별도 모바일 실험용 프로필을 분리하는 편이 낫다.

### 6. Windows 데스크톱에는 "진짜 모바일 Chrome 프로필" 개념이 없음

Windows 데스크톱 Chrome에서 `Profile 2`를 만든다고 해서 그 자체가 안드로이드 Chrome 프로필이 되지는 않는다. Playwright로 만들 수 있는 것은 어디까지나 Windows Chrome의 일반 프로필 폴더다.

대신 가능한 방식은 있다.

- `Profile 2` 같은 별도 프로필 폴더를 실제 `User Data` 아래 생성한다.
- 이 프로필은 생성과 이후 실행 모두에서 Playwright의 모바일 emulation을 항상 같이 건다.
- 그러면 저장되는 쿠키, 로컬 스토리지, 방문 이력은 "모바일 emulation으로 열었던 세션" 기준으로 누적된다.

즉 `Profile 2`는 "모바일 전용 프로필"이 아니라, "모바일 emulation으로 일관되게 운용하는 전용 프로필"이라고 이해하는 것이 정확하다.

### 7. `Profile 2` 생성 가능 여부와 현재 상태

Playwright로 실제 `C:\Users\${user}\AppData\Local\Google\Chrome\User Data` 아래에 새 프로필 디렉터리를 생성하는 것은 가능하다. 방식은 다음과 같다.

- 상위 `User Data` 루트를 `user_data_dir`로 사용
- `--profile-directory=Profile 2`로 새 프로필 지정
- 첫 실행 시 Chrome가 `Profile 2` 폴더와 관련 상태를 생성

다만 이번 세션에서는 실제 생성까지 완료하지 못했다. 이유는 현재도 다른 프로필 창이 열려 있고, 같은 `User Data` 루트를 쓰는 Chrome 루트 프로세스가 살아 있기 때문이다. 이 상태에서 강제로 생성 시도를 하면 충돌 위험이 있다.

이번 작업에서 반영한 내용:

- 하네스 스크립트에 `create-profile` 명령 추가
- 기본값을 `Profile 2` + `Galaxy S24` 모바일 emulation + `https://m.naver.com` 시드 URL로 설정
- `User Data` 루트를 쓰는 Chrome가 하나라도 살아 있으면 생성 시도를 중단하도록 처리

### 7.5. 분리 루트 전략은 실제로 검증됨

main Chrome `User Data`와 별도로 아래 루트에 실제 자동화용 프로필을 생성했다.

- 생성된 루트: `C:\Users\${user}\chrome\profile2-root`
- 내부 프로필 디렉터리: `Default`
- 생성 방식: Playwright persistent context + `Galaxy S24` 모바일 emulation + `https://m.naver.com` 시드

검증 결과:

- `Default` 폴더와 `Local State`가 실제로 생성됨
- `preflight --user-data-dir C:\Users\${user}\chrome\profile2-root --profile-directory Default` 결과에서 `target_user_data_process_count`가 `0`으로 확인됨
- 즉 main Chrome이 계속 실행 중이어도, 이 분리 루트는 잠기지 않고 독립적으로 관리 가능함

실무 결론:

- 기존 `Profile` 세션을 그대로 재사용해야 하는 경우에만 main `User Data` 루트를 다룬다.
- 모바일 DOM 기준 Farmer를 계속 유지하려면, 별도 루트 기반의 전용 프로필을 쓰는 쪽이 더 현실적이다.
- 단, 이 분리 루트 프로필은 새 프로필이므로 네이버 로그인 상태와 쿠키는 별도로 다시 쌓아야 한다.

### 8. fingerprint 관련 항목은 기술적으로 가능하지만 현재 계획 범위에서 제외

첨부한 okky 문서가 언급한 항목들은 일반론으로 보면 대부분 구현 자체는 가능하다.

- `navigator.webdriver`와 유사한 런타임 속성 오버라이드
- WebGL 상수값 노출 변경
- `hardwareConcurrency` 같은 브라우저 노출값 조정
- 캔버스/오디오 fingerprint 변형
- 쿠키 워밍을 위한 일반 탐색 시퀀스

하지만 이 항목들은 탐지 회피 성격이 강하므로, 현재 문서와 하네스의 범위에서는 구현 대상으로 포함하지 않는다. 이번 계획은 다음까지만 다룬다.

- 프로필 재사용 구조
- `User Data` 잠금 범위 확인
- 프록시 적용 검증
- 모바일 emulation 프로필의 생성 및 운영 일관성

## 권장 아키텍처

### 권장 순서

1. `storage_state` 기반 로그인 복원을 기본 경로에서 내린다.
2. 자동화용 프로필은 main `User Data`와 분리된 루트로 우선 운영한다.
3. 기존 생활용 Chrome 세션을 그대로 써야 할 때만 main `User Data` 기반 경로를 예외적으로 사용한다.
4. Playwright는 실제 Chrome 채널에 붙되, `user_data_dir`와 내부 프로필 경로를 명시적으로 관리한다.
5. 프록시는 브라우저 launch 시점에만 주입한다.
6. 로그인은 운영자가 수동으로 완료한 상태를 전제로 하고, 자동 로그인 함수는 fallback으로만 남긴다.

### 권장 루트 전략

#### 기본 권장. 분리된 `user_data_dir` 루트 사용

예시:

- `C:\Users\${user}\chrome\profile1-root`
- `C:\Users\${user}\chrome\profile2-root`

특징:

- 각 루트는 서로 독립적이다.
- main Chrome `User Data` 잠금과 충돌하지 않는다.
- 내부 프로필은 보통 `Default` 하나로 운영하면 충분하다.

장점:

- 다른 Chrome 창을 전부 닫을 필요가 없다.
- 자동화용 프로필 생명주기를 별도로 관리할 수 있다.
- 모바일 전용 emulation 프로필을 만들기 쉽다.

주의점:

- 기존 `Profile`의 로그인 쿠키나 방문 이력이 자동으로 따라오지 않는다.
- 새 루트에서 네이버 로그인 상태를 다시 만들어야 한다.

### 실행 모드 2개로 분리

#### 모드 A. Persistent Context 직접 실행

특징:

- Playwright가 Chrome를 직접 실행한다.
- `launch_persistent_context(user_data_dir=..., args=["--profile-directory=..."])` 구조를 사용한다.
- 한 번에 하나의 Chrome 인스턴스만 같은 `User Data` 루트를 점유해야 한다.

장점:

- 현재 `BrowserController` 구조를 가장 자연스럽게 대체할 수 있다.
- 프록시, 다운로드 경로, viewport 정책을 launch 시점에 함께 제어할 수 있다.

주의점:

- Chrome 메인 `User Data` 디렉터리를 자동화 대상으로 직접 쓰는 것은 Playwright 문서에서도 비권장이다.
- 실제 생활용 프로필을 계속 자동화 대상으로 쓰면 예기치 않은 충돌이 날 수 있다.
- 프로필 단위 종료가 아니라 `User Data` 루트 단위 종료가 필요할 수 있다.

권장 사용처:

- 분리된 자동화 루트를 사용할 때
- 또는 main `User Data`를 반드시 재사용해야 하지만 모든 Chrome를 내릴 수 있을 때

#### 모드 B. 수동 실행 Chrome에 CDP 연결

특징:

- 사용자가 먼저 Chrome를 원하는 프로필로 수동 실행한다.
- Playwright는 `connect_over_cdp()`로 붙는다.
- 브라우저 생명주기는 사용자가 소유하고, Playwright는 조작만 담당한다.

장점:

- 실제 프로필을 Playwright가 직접 기동하지 않아도 된다.
- 운영자가 로그인 완료 여부를 먼저 확인하고 붙을 수 있다.

주의점:

- 브라우저는 반드시 remote debugging 포트로 띄워야 한다.
- Playwright protocol보다 기능 충실도가 낮으므로 모든 API가 동일하게 동작하는지 별도 확인이 필요하다.

권장 사용처:

- 첫 전환 단계
- 실제 프로필을 바로 자동 기동하는 것이 불안할 때

## 이 프로젝트에서 먼저 바꿔야 할 것

### 1. `core/browser.py` 리팩터링

필요한 변경:

- `launch_mode` 개념 추가
  - `ephemeral`: 현재 방식
  - `persistent`: Chrome 프로필 직접 실행
  - `cdp`: 실행 중인 Chrome에 연결
- `channel`, `user_data_dir`, `profile_directory`, `remote_debugging_url` 지원
- `new_context()`와 `launch_browser()`의 책임을 분리
- persistent context에서는 `browser.new_context()`를 호출하지 않도록 구조 변경

핵심 이유:

- persistent context는 `Browser`와 `BrowserContext`를 따로 여는 구조가 아니라, context 자체를 반환한다.
- 따라서 현재 `launch_browser() -> new_context()` 순서는 그대로 재사용할 수 없다.

### 2. `task/farm.py`의 로그인 분기 정리

필요한 변경:

- 프로필 기반 모드에서는 `state` JSON보다 프로필 세션을 우선한다.
- `navigate_to_menu()`에서 `has_state` 대신 `is_authenticated_session` 같은 의미 기반 조건으로 바꾼다.
- 프로필 세션이 이미 로그인 상태이면 `login()`을 호출하지 않는다.

핵심 이유:

- 프로필 기반 구조에서 JSON 저장/복원은 더 이상 주 세션 저장소가 아니다.

### 3. 브라우저 설정을 desktop 전용 경로와 mobile 전용 경로로 분리

필요한 변경:

- 기존 `Profile` 재사용 경로에서는 `mobile: false`를 우선 검토한다.
- 모바일 경로가 반드시 필요하다면 `C:\Users\${user}\chrome\profile2-root` 같은 별도 루트에 전용 프로필을 만들고, 그 프로필은 항상 같은 모바일 emulation으로만 연다.
- 액션 셀렉터가 모바일에만 맞춰져 있다면 데스크톱 셀렉터 세트를 병행 관리해야 한다.

핵심 이유:

- 기존 데스크톱 프로필과 모바일 emulation을 무분별하게 섞으면 세션 의미가 흐려진다.
- 분리된 프로필을 일관되게 운용하는 편이 더 관리 가능하다.

### 4. 계정과 프로필의 매핑 정책 추가

필요한 변경:

- `userid -> profile_directory` 매핑을 설정 파일 또는 별도 문서로 고정한다.
- 같은 프로필을 여러 계정에 공유하지 않는다.
- 같은 계정을 여러 프로필로 번갈아 쓰지 않는다.

권장 예시:

- `${userid} -> Profile` 또는 별도 desktop 전용 루트
- `${userid}-mobile -> C:\Users\${user}\chrome\profile2-root (Default)`
- 다른 계정은 각각 별도 프로필 생성

## 권장 설정 스키마 초안

`config.yaml`에 아래 키를 추가하는 방향이 적절하다.

```yaml
browser:
  launch_mode: persistent
  channel: chrome
  mobile: false
  no_viewport: true
  user_data_dir: "C:\\Users\\${user}\\AppData\\Local\\Google\\Chrome\\User Data"
  profile_directory: "Profile"
  proxy_server: "${ip_addr}"
  remote_debugging_url: "http://127.0.0.1:9222"
```

모바일 전용 프로필을 별도 운용한다면 다음처럼 분리하는 것도 가능하다.

```yaml
browser:
  launch_mode: persistent
  channel: chrome
  user_data_dir: "C:\\Users\\${user}\\chrome\\profile2-root"
  profile_directory: "Default"
  mobile: true
  device: "Galaxy S24"
```

메모:

- `proxy_server`는 현재 계정별 `ip_addr`와 역할이 겹친다. 구현 시에는 둘 중 하나를 브라우저 레벨 단일 소스로 정리해야 한다.
- 실제 운영 시 프록시를 계정별로 유지할지, 브라우저 공통으로 유지할지 정책을 먼저 정해야 한다.

## 테스트 결과 요약

이번에 실제로 확인한 항목은 다음과 같다.

1. Playwright persistent context는 상위 `User Data` + `--profile-directory=Profile` 조합으로 프로필을 선택할 수 있다.
2. `...\Profile`를 직접 `user_data_dir`로 넘기면 구조가 잘못된다.
3. 프록시 `${ip_addr}`는 persistent context에서 정상 동작했다.
4. `.secrets/config.yaml`을 통한 구글시트 설정 로드는 정상이며 `${userid}` 계정이 존재한다.
5. 실행 중인 Chrome 프로세스에서는 `Profile` 같은 프로필 표식이 보이지 않았고, 루트 브라우저 프로세스가 `User Data` 단위로 살아 있었다.
6. 따라서 `Profile`만 따로 종료하는 것은 신뢰할 수 없고, 같은 `User Data` 루트를 쓰는 Chrome 전체를 내려야 한다.
7. main `User Data` 안의 `Profile 2` 생성 로직은 하네스에 반영했지만, 해당 루트는 다른 Chrome 창이 열려 있으면 live 생성이 차단된다.
8. 별도 루트 `C:\Users\${user}\chrome\profile2-root`에서는 실제 프로필 생성이 성공했고, main Chrome과 독립적으로 관리 가능함을 확인했다.

## 구현 전 체크리스트

- Chrome 백그라운드 프로세스가 완전히 내려가 있는가
- 같은 `User Data` 루트를 쓰는 다른 프로필 창까지 모두 닫았는가
- 아니면 main `User Data` 대신 분리된 전용 루트를 쓸 것인가
- 대상 프로필이 생활용 메인 프로필이 아니라 자동화 전용 프로필인가
- 프로필 기반 경로에서 `mobile: true`를 계속 유지할지 결정했는가
- `storage_state`를 계속 저장할지, 진단용으로만 남길지 결정했는가
- 프록시 소스가 `config.ip_addr`인지 `browser.proxy_server`인지 단일화했는가
- 계정별 프로필 매핑 표가 정리되어 있는가

## 구현 우선순위

1. `core/browser.py`에 launch mode 분기 추가
2. `Farmer.navigate_to_menu()`의 로그인 분기 재정의
3. desktop 경로 기준으로 최소 동작 확인
4. proxy, profile, sheet loading을 한 번에 확인하는 하네스 확정
5. 이후에 필요하면 mobile 경로를 별도 브랜치로 재설계
