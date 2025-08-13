# 한컴 오피스 제품키 변환 도구 (Product ID to Serial Converter)

한컴 오피스 제품키의 다양한 형식 간 변환을 지원하는 도구입니다.

## 참고한 문서 및 동영상 등등 한컴 오피스 제품키 변환 도구 (Product ID to Serial Converter)

한컴 오피스 제품키의 다양한 형식 간 변환을 지원하는 도구입니다.

## 참고한 문서 및 동영상 등등

https://github.com/loopback-kr/hwp-key-converter

https://www.youtube.com/watch?v=kxbXpVnV5aw

## 지원하는 변환

- **PID (23자리)** → **ECDATA (20자리)** + **PID2 (31자리)**
- **PID2 (31자리)** → **ECDATA (20자리)** + **PID (23자리)**
- **ECDATA (20자리)** → **PID (23자리)** + **PID2 (31자리)**

## 입력 형식

### PID (Product ID)
- 형식: `XXXXX-XXXXX-XXXXX-XXXXX`
- 길이: 23자리 (하이픈 3개 포함)
- 예시: `ABCDE-FGHIJ-KLMNO-PQRST`

### ECDATA
- 형식: 20자리 문자열 (하이픈 없음)
- 길이: 20자리
- 예시: `ABCDEFGHIJKLMNOPQRST`

### PID2 (Serial Key)
- 형식: 31자리 문자열 (하이픈 포함 가능)
- 길이: 31자리
- 예시: `0000001-0000002-0000003-0000004`

## 다운로드

[ProductID-to-Serial.exe](ProductID-to-Serial.exe)

## 사용법

1. 실행 파일을 다운로드하여 실행
2. 변환할 키를 입력 (PID, ECDATA, PID2 중 하나)
3. 자동으로 적절한 변환 결과 출력

## 개발자용

### EXE 파일 생성

```bash
# 의존성 설치
pip install -r requirements.txt

# EXE 파일 생성
pyinstaller --onefile --icon=favicon.ico --name ProductID-to-Serial.exe final.py
```

### Python 스크립트 실행

```bash
python final.py
```

## 주요 기능

- **자동 형식 감지**: 입력된 키의 형식을 자동으로 분석하여 적절한 변환 수행
- **다양한 변환 지원**: PID, ECDATA, PID2 간의 모든 변환 조합 지원
- **오류 처리**: 잘못된 입력 형식에 대한 상세한 오류 메시지 제공
- **사용자 친화적**: 직관적인 인터페이스와 명확한 결과 출력

## 기술적 세부사항

### 변환 알고리즘

1. **PID ↔ ECDATA 변환**
   - 해시 테이블 기반 문자 변환
   - 블록별 stride 값 적용
   - 범위 조정 로직 포함

2. **PID ↔ PID2 변환**
   - 32진수 인덱스 변환
   - 특별 규칙 적용 (인덱스 3)
   - 문자열 재배열 알고리즘

