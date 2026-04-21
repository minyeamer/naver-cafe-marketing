# Playwright 스텔스 설정 설명서

자동화 봇을 탐지하는 웹사이트에 걸리지 않기 위해 `core/browser.py`에는 두 가지 방어 수단이 적용됩니다.

1. **Chrome 실행 플래그 (launch args)** — 브라우저를 켜는 시점에 적용
2. **STEALTH_INIT_SCRIPT** — 모든 페이지가 열리기 직전 자바스크립트로 적용

---

## 1. Chrome 실행 플래그 (launch_kwargs)

브라우저를 실행할 때 명령줄 옵션으로 전달하는 설정입니다.  
윈도우 바로가기에서 `chrome.exe --옵션` 형태로 쓰는 것과 동일한 개념입니다.

### `ignore_default_args=["--enable-automation"]`

Playwright는 기본적으로 `--enable-automation` 플래그를 Chrome에 전달합니다.  
이 플래그가 켜지면 브라우저 상단에 **"자동화된 소프트웨어가 Chrome을 제어하고 있습니다"** 라는 띠 배너가 나타나고,  
동시에 자바스크립트 환경에서 `navigator.webdriver === true` 값이 설정됩니다.

→ Playwright 기본값 목록에서 이 항목을 **제거**하여 배너와 webdriver 마킹을 원천 차단합니다.

---

### `args` 목록 상세

#### `--profile-directory=Default`

Chrome의 프로필 폴더 이름을 지정합니다.  
`user_data_dir`(격리된 자동화 루트)의 어떤 하위 폴더를 "현재 사용자"로 쓸지 결정합니다.  
`Default`는 새 격리 루트를 만들 때 생성되는 기본 폴더명입니다.

> `${$user_data_dir}\Default\` 안에 쿠키, 로컬스토리지 등이 저장됩니다.

---

#### `--no-first-run`

Chrome을 처음 실행할 때 나타나는 **"Chrome을 시작합니다" 환영 화면**을 건너뜁니다.  
자동화 환경에서 환영 팝업이 뜨면 클릭 위치가 틀어져 스크립트가 오작동할 수 있습니다.

---

#### `--no-default-browser-check`

"Chrome을 기본 브라우저로 설정하시겠습니까?" 대화상자를 억제합니다.  
자동화 중 이런 팝업이 뜨면 스크립트가 중단될 수 있으므로 항상 꺼 둡니다.

---

#### `--disable-blink-features=AutomationControlled`

Blink(Chrome의 렌더링 엔진)에서 `AutomationControlled` 기능을 비활성화합니다.  
이 기능이 켜져 있으면 웹페이지의 자바스크립트가 `navigator.webdriver` 값을 `true`로 읽을 수 있어  
봇임을 즉시 감지할 수 있습니다.

→ 이 플래그를 끄면 `navigator.webdriver`가 `undefined`로 남습니다.

> `--enable-automation` 제거와 이 플래그는 역할이 비슷해 보이지만 작동 계층이 다릅니다.  
> `--enable-automation`은 Playwright 레이어에서, 이 플래그는 Blink 렌더러 레이어에서 각각 독립적으로 마킹을 제거합니다.  
> 두 가지를 모두 적용해야 확실히 차단됩니다.

---

#### `--disable-infobars`

자동화 감지 외에도 Chrome이 보안, 확장 프로그램, 성능 경고 등을 알릴 때 띠 모양으로 나타나는  
**인포바(infobar)** 를 전부 숨깁니다.  
인포바가 뜨면 화면 레이아웃이 변하고, 좌표 기반 클릭이 어긋날 수 있습니다.

---

#### `--force-webrtc-ip-handling-policy=disable_non_proxied_udp`

**WebRTC IP 누출 방지** 설정입니다.

WebRTC는 영상통화·음성통화용 기술인데, 프록시(VPN 포함)를 사용 중이어도  
WebRTC를 통해 실제 로컬 IP 주소가 웹페이지에 노출될 수 있습니다.

`disable_non_proxied_udp`로 설정하면 프록시를 거치지 않는 UDP 연결(= 실제 IP 노출 경로)을 강제로 차단합니다.

---

#### `--lang=ko-KR`

Chrome UI 언어를 한국어로 고정합니다.  
`locale="ko-KR"` 옵션(Playwright)과 함께 사용하면 브라우저 자체 언어와 HTTP 요청 헤더의 `Accept-Language: ko-KR`이 일치하여  
"브라우저 언어 설정이 이상한 봇"으로 탐지될 가능성을 줄입니다.

---

## 2. STEALTH_INIT_SCRIPT

`context.add_init_script()`로 등록한 자바스크립트 코드입니다.  
이 코드는 **페이지 HTML이 실행되기 직전**, 즉 웹사이트 스크립트보다 먼저 실행됩니다.  
웹사이트가 봇 감지를 시작하기 전에 브라우저 속성을 먼저 바꿔 놓는 원리입니다.

---

### 1. `navigator.webdriver` 제거

```js
if (navigator.webdriver !== undefined) {
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
        configurable: true,
    });
}
```

**`navigator.webdriver`** 는 브라우저가 자동화 도구에 의해 제어될 때 `true`로 설정되는 표준 속성입니다.  
네이버, Google 등 대형 서비스의 봇 탐지 로직이 가장 먼저 확인하는 값입니다.

`Object.defineProperty`로 `get()` 함수를 가로채어 항상 `undefined`를 반환하게 만듭니다.  
Chrome 플래그(`--disable-blink-features=AutomationControlled`)와 이중으로 적용하는 이유는,  
플래그 적용 후에도 일부 타이밍 문제로 `true`가 노출될 수 있기 때문입니다.

---

### 2. 하드웨어 프로필 — Galaxy S24

```js
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
Object.defineProperty(navigator, 'deviceMemory',        { get: () => 8 });
Object.defineProperty(navigator, 'platform',            { get: () => 'Linux armv8l' });
```

웹사이트는 기기 사양 정보를 수집해 "이 기기가 실제로 존재할 법한 기기인지"를 검사합니다.

| 속성 | 의미 | 설정값 |
|---|---|---|
| `hardwareConcurrency` | 논리 CPU 코어 수 | 8 (Snapdragon 8 Gen 3 기준) |
| `deviceMemory` | RAM 용량 (GB) | 8 |
| `platform` | 운영체제 플랫폼 문자열 | `Linux armv8l` (Android ARM64) |

Playwright가 Galaxy S24 에뮬레이션을 적용해도 이 세 값은 자동으로 변경되지 않습니다.  
`user_agent`가 Galaxy S24를 주장하면서 CPU가 2코어이거나 플랫폼이 `Win32`이면 모순이 발생해 탐지됩니다.  
→ 실제 Galaxy S24 사양과 일치하도록 수동으로 덮어씁니다.

---

### 3. `window.chrome` 런타임 프로브

```js
if (!window.chrome) { window.chrome = { runtime: {} }; }
```

진짜 Chrome 브라우저에는 `window.chrome.runtime` 객체가 항상 존재합니다.  
Chromium 기반 자동화 환경에서는 이 객체가 누락되거나 비어 있는 경우가 있어,  
봇 탐지 스크립트가 `window.chrome?.runtime`을 확인하는 방식으로 자동화 여부를 파악합니다.

→ 객체가 없는 경우 최소한의 구조 `{ runtime: {} }` 를 채워 실제 Chrome처럼 보이게 합니다.

---

### 4. 캔버스 핑거프린팅 노이즈

```js
const orig = CanvasRenderingContext2D.prototype.getImageData;
CanvasRenderingContext2D.prototype.getImageData = function (sx, sy, sw, sh) {
    const d = orig.call(this, sx, sy, sw, sh);
    d.data[0] ^= 0x01;
    return d;
};
```

**캔버스 핑거프린팅**이란, 웹사이트가 화면에 보이지 않는 `<canvas>` 태그에 텍스트나 도형을 그린 후  
픽셀 데이터를 해시값으로 만들어 기기를 식별하는 기법입니다.  
동일한 기기·드라이버·폰트 조합이면 항상 같은 픽셀 값이 나오기 때문에, 계정이 바뀌어도 같은 기기로 인식됩니다.

`getImageData`를 가로채어 픽셀 배열의 첫 번째 값에 `XOR 0x01` 연산을 적용합니다.  
`0x01`은 1비트만 바꾸는 최소한의 변경이므로 육안으로는 전혀 차이가 없지만, 해시값은 완전히 달라집니다.

---

### 5. WebGL 벤더·렌더러 스푸핑

```js
proto.getParameter = function (param) {
    if (param === 37445) return 'Qualcomm';
    if (param === 37446) return 'Adreno (TM) 750';
    return orig.call(this, param);
};
```

**WebGL 핑거프린팅**이란, GPU 정보를 읽어 기기를 식별하는 기법입니다.  
`gl.getParameter(37445)`는 GPU 제조사(VENDOR), `gl.getParameter(37446)`는 GPU 모델명(RENDERER)을 반환합니다.

실제 Galaxy S24(Snapdragon 8 Gen 3)의 GPU는 **Qualcomm Adreno 750** 이므로 이 값을 고정합니다.  
`user_agent`가 Galaxy S24를 주장하면서 GPU가 Intel이나 NVIDIA이면 모순이 발생해 탐지됩니다.

`WebGL2RenderingContext`도 존재할 경우 동일하게 패치해 WebGL1/2 두 경로 모두를 덮습니다.

---

## 요약

| 방어 수단 | 위치 | 막는 것 |
|---|---|---|
| `--enable-automation` 제거 | Playwright 기본값 제거 | 자동화 배너, webdriver 마킹 |
| `--disable-blink-features=AutomationControlled` | Chrome 플래그 | Blink 렌더러의 webdriver 마킹 |
| `--disable-infobars` | Chrome 플래그 | UI 레이아웃 틀어짐 |
| `--force-webrtc-...=disable_non_proxied_udp` | Chrome 플래그 | 프록시 뒤 실제 IP 노출 |
| `--lang=ko-KR` + `locale` | Chrome 플래그 + Playwright | 언어 설정 불일치 탐지 |
| `navigator.webdriver` 제거 | JS init script | webdriver 속성 탐지 |
| 하드웨어 프로필 고정 | JS init script | 기기 사양 불일치 탐지 |
| `window.chrome` 보충 | JS init script | Chrome 런타임 부재 탐지 |
| 캔버스 노이즈 | JS init script | 캔버스 핑거프린팅 |
| WebGL 벤더 스푸핑 | JS init script | WebGL 핑거프린팅 |
