"""
한컴 오피스 제품키 변환 도구

지원하는 변환:
1. PID (23자리) ↔ ECDATA (20자리) ↔ PID2 (31자리)
2. 입력에 따라 자동으로 적절한 변환 수행

입력 형식:
- PID: XXXXX-XXXXX-XXXXX-XXXXX (23자리, 하이픈 3개)
- ECDATA: 20자리 문자열 (하이픈 없음)
- PID2: 31자리 문자열 (하이픈 포함 가능)

초보자 안내:
- PID ↔ ECDATA는 "문자 치환 + 블록 섞기"입니다. 각 문자에 일정한 이동값(stride)을 더하거나 빼고,
  그 결과를 다른 블록 위치로 옮겨 최종 문자열을 만듭니다. 숫자(0~9)는 ASCII 48~57, 대문자(A~Z)는
  ASCII 65~90 범위에서 순환(wrap-around)합니다.
- PID2 ↔ Serial Key(PID 형태)는 10개의 정수(0~1023)를 32진수 두 자리로 분해/결합해 20자 "Serial"을 만들고,
  이를 5자씩 4블록(=PID 형태)으로 표기합니다.
- 본 구현에서 PID2 → PID은 아직 완전한 역변환이 없어, PID2 → Serial Key까지만 수행한 뒤 이를 PID 형식 문자열로
  돌려줍니다.

요약 동작:
- PID 입력 → ECDATA + PID2 출력
- PID2 입력 → ECDATA + PID(=Serial Key) 출력
- ECDATA 입력 → PID + PID2 출력

주의:
- PID → PID2 변환은 PID가 Serial Key에서 사용하는 32진 알파벳에 포함된 문자만 있을 때만 동작합니다.
  혼동 방지를 위해 '0,1,5,I,O,L,S' 문자는 제외된 32진 알파벳을 사용합니다.
"""

import sys
from typing import List


# ============================================================================
# PID ↔ ECDATA 변환
# ============================================================================

def pid_to_ecd(pid: str) -> str:
    """
    PID 형식(예: XXXXX-XXXXX-XXXXX-XXXXX)을 내부 20자 ECDATA로 변환합니다.

    핵심 아이디어:
    - 4개 블록 각각에 대해 숫자/대문자에 서로 다른 이동값(stride)을 더합니다.
    - 블록별 결과 문자는 지정된 목적지 블록(dst_block)에 쌓여 최종 20자를 이룹니다.
    - 숫자는 48~57('0'~'9'), 문자는 65~90('A'~'Z') 범위를 벗어나면 순환(wrap-around)합니다.

    매핑 테이블 형식: {원본블록: (목적지블록, 숫자stride, 문자stride)}
    예: 0: (2, 7, 23)는 블록 0의 각 문자는 숫자면 +7, 문자면 +23을 더해 블록 2로 이동한다는 뜻입니다.

    Args:
        pid: '5-5-5-5' 형태의 23자 문자열(하이픈 3개 포함)

    Returns:
        20자 ECDATA 문자열
    """
    # hashtab[원본블록] = (목적지블록, 숫자에 더할 값, 문자에 더할 값)
    hashtab = {
        0: (2, 7, 23),   # 블록 0 → 블록 2, 숫자 +7, 문자 +23
        1: (0, 1, 1),    # 블록 1 → 블록 0, 숫자 +1, 문자 +1
        2: (3, 2, 2),    # 블록 2 → 블록 3, 숫자 +2, 문자 +2
        3: (1, 1, 17),   # 블록 3 → 블록 1, 숫자 +1, 문자 +17
    }
    
    ecdata = ['' for _ in range(len(hashtab))]
    for i, p in enumerate(pid.split('-')):
        for c in p:
            stride = hashtab[i][1 if c.isdigit() else 2]
            sum_val = ord(c) + stride
            if sum_val > (57 if c.isdigit() else 90):
                sum_val -= 10 if c.isdigit() else 26
            ecdata[hashtab[i][0]] += chr(sum_val)
    return ''.join(ecdata)


def ecd_to_pid(ecd: str) -> str:
    """
    20자 ECDATA를 원래 PID(=5-5-5-5 블록) 형식으로 되돌립니다.

    역변환 요약:
    - 인덱스 0~19를 5자씩 끊어 원본의 4개 블록에 대응시킵니다.
    - 각 문자에서 해당 블록의 이동값(stride)을 빼고, 범위를 벗어나면 순환합니다.
    - 변환된 문자를 원래 목적지였던 블록 위치로 재배치하여 PID를 구성합니다.

    Args:
        ecd: 하이픈 없는 20자 문자열

    Returns:
        'XXXXX-XXXXX-XXXXX-XXXXX' 형태의 PID 문자열
    """
    # hashtab[현재블록] = (원래블록, 숫자에 뺄 값, 문자에 뺄 값)
    hashtab = {
        0: (1, 1, 1),    # 블록 0 → 원래 블록 1
        1: (3, 1, 17),   # 블록 1 → 원래 블록 3
        2: (0, 7, 23),   # 블록 2 → 원래 블록 0
        3: (2, 2, 2),    # 블록 3 → 원래 블록 2
    }
    
    # ECDATA 길이 검증 (20자리여야 함)
    if len(ecd) != 20:
        raise ValueError(f"ECDATA는 정확히 20자리여야 합니다. (현재: {len(ecd)}자리)")
    
    pidkey = ['' for _ in range(len(hashtab))]
    for i, c in enumerate(ecd):
        block_num = i // 5
        # block_num이 4를 초과하지 않도록 보장
        if block_num >= len(hashtab):
            raise ValueError(f"ECDATA 길이가 올바르지 않습니다. 20자리여야 합니다.")
        
        stride = hashtab[block_num][1 if c.isdigit() else 2]
        sub_val = ord(c) - stride
        if sub_val < (48 if c.isdigit() else 65):
            sub_val += 10 if c.isdigit() else 26
        pidkey[hashtab[block_num][0]] += chr(sub_val)
    
    # 5자리씩 4개 그룹으로 구성된 PID 형식 반환
    return '-'.join(pidkey)


# ============================================================================
# PID2 ↔ PID 변환 (Serial Key ↔ PID)
# ============================================================================

# 32진수 문자 매핑 테이블
# - 시각적으로 헷갈리는 문자(0,1,5,I,O,L,S)는 제외합니다.
# - 따라서 문자 집합은 32개로 유지되되, 혼동 위험을 낮춥니다.
BASE_CHARACTERS = [
    "2", "3", "4", "6", "7", "8", "9",
    "A", "B", "C", "D", "E", "F", "G", "H",
    "J", "K", "M", "N", "P", "Q", "R", "T", "U",
    "V", "W", "X", "Y", "Z",
]


def pid2_to_pid(pid2: str) -> str:
    """
    PID2(31자리 숫자열)를 PID(=Serial Key 표기)로 변환합니다.

    주의:
    - 현재 구현은 "완전한" PID2 → PID 역변환이 아닌, PID2 → Serial Key까지만 수행합니다.
    - 반환값은 'XXXXX-XXXXX-XXXXX-XXXXX' 형태의 Serial 문자열이며, 본 도구에서는 이를 PID로 간주합니다.

    Args:
        pid2: 하이픈 포함 가능하나 총 31자여야 하는 숫자 문자열

    Returns:
        PID 형식(5자×4블록, 하이픈 포함) 문자열
    """
    if len(pid2) != 31:
        raise ValueError(f"PID2는 정확히 31자리여야 합니다. (현재: {len(pid2)}자리)")
    
    # 1단계: PID2를 Serial Key로 변환
    serial = pid2_to_serial(pid2)
    
    # 2단계: Serial Key를 PID로 변환 (임시 로직)
    # 실제로는 Serial Key에서 PID로의 역변환 알고리즘이 필요
    # 현재는 Serial Key를 그대로 PID 형식으로 반환
    return serial


def pid_to_pid2(pid: str) -> str:
    """
    PID(=Serial Key 표기, 23자)을 PID2(31자 숫자열)로 변환합니다.

    단계 요약:
    1) 하이픈을 제거하고 각 문자를 32진 알파벳의 인덱스로 치환합니다.
    2) 인덱스 20개를 10개 정수(0~1023)로 역결합(q*32 + r).
       - 단, i=3 위치는 예외 규칙으로 인코딩되어 있었기 때문에 sec6/sec7 조합으로 비트를 복원합니다.
         (sec6=2 또는 28, sec7=23 또는 27)
    3) 10개 숫자를 사전 정의된 인덱스 규칙에 따라 31자 숫자열에 분산합니다.
    4) 최종 31자 숫자열을 7-7-7-7-3 패턴으로 하이픈을 넣어 표기합니다.

    제한 사항:
    - 입력 PID는 BASE_CHARACTERS에 포함된 문자만 사용해야 합니다. 포함되지 않은 문자가 있으면 오류가 발생합니다.

    Args:
        pid: 'XXXXX-XXXXX-XXXXX-XXXXX' 형태의 23자 문자열

    Returns:
        'XXXXXXX-XXXXXXX-XXXXXXX-XXXXXXX' 형태의 31자 문자열
    """
    if len(pid) != 23 or pid.count('-') != 3:
        raise ValueError(f"PID는 정확히 23자리(하이픈 3개)여야 합니다. (현재: {len(pid)}자리)")
    
    # 1단계: PID를 Serial Key로 변환 (PID가 이미 Serial Key 형식)
    serial_key = pid
    
    # 2단계: Serial Key를 32진수 인덱스로 변환
    indices = []
    for char in serial_key.replace('-', ''):
        try:
            index = BASE_CHARACTERS.index(char)
            indices.append(index)
        except ValueError:
            raise ValueError(f"지원하지 않는 문자: {char}")
    
    # 3단계: 20개 인덱스를 10개 숫자로 역변환
    newnumbers = []
    for i in range(0, 20, 2):
        if i == 6:  # 인덱스 3의 특별 규칙 역변환
            # sec6 = 2 if (newnumbers[3] // 2) == 1 else 28
            # sec7 = 23 if (newnumbers[3] % 2) == 1 else 27
            # 역변환: sec6와 sec7로부터 newnumbers[3] 복원
            sec6 = indices[6]
            sec7 = indices[7]
            
            if sec6 == 2 and sec7 == 23:
                newnumbers.append(1)  # newnumbers[3] = 1
            elif sec6 == 28 and sec7 == 27:
                newnumbers.append(0)  # newnumbers[3] = 0
            else:
                # 다른 경우들 처리
                if sec6 == 2:
                    newnumbers.append(1)
                else:
                    newnumbers.append(0)
        else:
            # 일반적인 32진수 역변환
            q = indices[i]
            r = indices[i + 1]
            number = q * 32 + r
            newnumbers.append(number)
    
    # 4단계: 10개 숫자를 31자리 문자열로 역변환
    # - 원본 알고리즘의 인덱스 규칙을 역으로 적용하여 각 숫자의 3자리 문자열을 흩뿌립니다.
    numbers = [''] * 31
    
    # 인덱스 규칙 역변환
    # 0: idx[30] + idx[0] + idx[2] → numbers[30], numbers[0], numbers[2]에 분배
    # 1: idx[4] + idx[6] + idx[9] → numbers[4], numbers[6], numbers[9]에 분배
    # 2: idx[11] + idx[13] + idx[16] → numbers[11], numbers[13], numbers[16]에 분배
    # 3: idx[18] → numbers[18]에 할당
    # 4: idx[20] + idx[22] + idx[25] → numbers[20], numbers[22], numbers[25]에 분배
    # 5: idx[27] + idx[29] + idx[1] → numbers[27], numbers[29], numbers[1]에 분배
    # 6: idx[3] + idx[5] + idx[8] → numbers[3], numbers[5], numbers[8]에 분배
    # 7: idx[10] + idx[12] + idx[14] → numbers[10], numbers[12], numbers[14]에 분배
    # 8: idx[17] + idx[19] + idx[21] → numbers[17], numbers[19], numbers[21]에 분배
    # 9: idx[24] + idx[26] + idx[28] → numbers[24], numbers[26], numbers[28]에 분배
    
    # 단일 숫자인 경우 (인덱스 3)
    numbers[18] = str(newnumbers[3])
    
    # 3자리 연결된 경우들 처리
    # - 각 newnumber를 3자리 문자열로 변환(zfill(3))하고 각 위치에 분배합니다.
    connections = [
        (0, [30, 0, 2]),    # newnumbers[0] → numbers[30,0,2]
        (1, [4, 6, 9]),     # newnumbers[1] → numbers[4,6,9]
        (2, [11, 13, 16]),  # newnumbers[2] → numbers[11,13,16]
        (4, [20, 22, 25]),  # newnumbers[4] → numbers[20,22,25]
        (5, [27, 29, 1]),   # newnumbers[5] → numbers[27,29,1]
        (6, [3, 5, 8]),     # newnumbers[6] → numbers[3,5,8]
        (7, [10, 12, 14]),  # newnumbers[7] → numbers[10,12,14]
        (8, [17, 19, 21]),  # newnumbers[8] → numbers[17,19,21]
        (9, [24, 26, 28]),  # newnumbers[9] → numbers[24,26,28]
    ]
    
    for newnum_idx, positions in connections:
        value = str(newnumbers[newnum_idx]).zfill(3)  # 3자리로 패딩
        for i, pos in enumerate(positions):
            if i < len(value):
                numbers[pos] = value[i]
            else:
                numbers[pos] = '0'  # 부족한 경우 0으로 채움
    
    # 31자리 문자열에 하이픈 추가 (7-7-7-7-3 형식)
    result = ''.join(numbers)
    formatted_pid2 = f"{result[:7]}-{result[7:14]}-{result[14:21]}-{result[21:28]}"
    return formatted_pid2


def pid2_to_serial(pid2: str) -> str:
    """
    PID2(31자 숫자열)를 20자 Serial Key(PID 표기 형태)로 변환합니다.

    단계 요약:
    1) 31자 숫자열에서 사전 정의된 인덱스 규칙대로 10개의 숫자 문자열을 만듭니다.
       - 대부분은 3자리 연결(예: idx[30]+idx[0]+idx[2])이고, 하나(i=3)는 단일 자리입니다.
    2) 각 숫자를 32로 나눈 몫(q), 나머지(r)로 분해하여 총 20개의 0~31 인덱스를 만듭니다.
       - 단, i=3은 예외 규칙으로 sec6/sec7 두 칸에 특수하게 인코딩됩니다.
    3) 각 인덱스를 BASE_CHARACTERS의 문자로 치환하여 총 20자를 만든 뒤 5자마다 하이픈을 삽입합니다.

    Args:
        pid2: 총 길이 31자의 숫자 문자열

    Returns:
        'XXXXX-XXXXX-XXXXX-XXXXX' 형태의 Serial Key 문자열
    """
    if len(pid2) != 31:
        raise ValueError(f"PID2는 정확히 31자리여야 합니다. (현재: {len(pid2)}자리)")
    
    # 1단계: 문자열을 개별 문자로 분해
    numbers = list(pid2)
    
    # 2단계: 특정 인덱스 규칙에 따라 재배열
    newnumbers_str = [
        numbers[30] + numbers[0] + numbers[2],   # 0: 인덱스 30,0,2 연결
        numbers[4] + numbers[6] + numbers[9],    # 1: 인덱스 4,6,9 연결
        numbers[11] + numbers[13] + numbers[16], # 2: 인덱스 11,13,16 연결
        numbers[18],                             # 3: 인덱스 18 (단일 숫자)
        numbers[20] + numbers[22] + numbers[25], # 4: 인덱스 20,22,25 연결
        numbers[27] + numbers[29] + numbers[1],  # 5: 인덱스 27,29,1 연결
        numbers[3] + numbers[5] + numbers[8],    # 6: 인덱스 3,5,8 연결
        numbers[10] + numbers[12] + numbers[14], # 7: 인덱스 10,12,14 연결
        numbers[17] + numbers[19] + numbers[21], # 8: 인덱스 17,19,21 연결
        numbers[24] + numbers[26] + numbers[28], # 9: 인덱스 24,26,28 연결
    ]
    newnumbers = [int(value) for value in newnumbers_str]
    
    # 3단계: 32진수 변환
    secondnumbers = [0] * 20
    for i in range(10):
        if i != 3:
            q = newnumbers[i] // 32  # 몫
            r = newnumbers[i] % 32   # 나머지
            secondnumbers[i * 2] = q
            secondnumbers[i * 2 + 1] = r
        else:
            # 인덱스 3의 특별한 변환 규칙
            sec6 = 2 if (newnumbers[3] // 2) == 1 else 28
            sec7 = 23 if (newnumbers[3] % 2) == 1 else 27
            secondnumbers[6] = sec6
            secondnumbers[7] = sec7
    
    # 4단계: 문자 매핑 및 Serial Key 생성
    chars = []
    for index in secondnumbers:
        try:
            chars.append(BASE_CHARACTERS[index])
        except IndexError:
            raise IndexError(f"인덱스 {index}가 문자 테이블 범위를 벗어났습니다.")
    
    serial = "".join(chars)
    # 5자리마다 하이픈 삽입 (4개 그룹)
    return "-".join(serial[i : i + 5] for i in range(0, 20, 5))


# ============================================================================
# 메인 변환 함수
# ============================================================================

def convert_key(input_key: str) -> str:
    """
    입력 키를 분석하여 적절한 변환을 수행합니다.

    감지 규칙:
    - PID: 하이픈 3개, 총 23자 → ECDATA + PID2
    - PID2: 총 31자(하이픈 포함 가능) → ECDATA + PID(=Serial)
    - ECDATA: 하이픈 없음, 총 20자 → PID + PID2
    - 그 외: 상세한 안내 메시지와 함께 오류 처리

    Args:
        input_key: PID / ECDATA / PID2 중 하나의 문자열

    Returns:
        변환 결과 문자열(사람이 읽기 쉬운 라벨 포함)
    """
    # 입력 형식 분석
    hyphen_count = input_key.count('-')
    total_length = len(input_key)
    
    print(f"입력 분석: '{input_key}' (길이: {total_length}, 하이픈: {hyphen_count})")
    
    # 케이스 1: PID 입력 → ECDATA + PID2 출력
    if hyphen_count == 3 and total_length == 23:
        print("→ PID 형식 감지: ECDATA + PID2 변환")
        try:
            ecd = pid_to_ecd(input_key)
            pid2 = pid_to_pid2(input_key)
            return f"ECDATA: {ecd}\nPID2: {pid2}"
        except Exception as e:
            raise ValueError(f"PID 변환 중 오류: {e}")
    
    # 케이스 2: PID2 입력 → ECDATA + PID 출력
    elif total_length == 31:
        print("→ PID2 형식 감지: ECDATA + PID 변환")
        try:
            # PID2 → PID → ECDATA 순서로 변환
            pid = pid2_to_pid(input_key)
            ecd = pid_to_ecd(pid)
            return f"ECDATA: {ecd}\nPID: {pid}"
        except Exception as e:
            raise ValueError(f"PID2 변환 중 오류: {e}")
    
    # 케이스 3: ECDATA 입력 → PID + PID2 출력 (하이픈이 없고 20자리인 경우)
    elif hyphen_count == 0 and total_length == 20:
        print("→ ECDATA 형식 감지: PID + PID2 변환")
        try:
            pid = ecd_to_pid(input_key)
            pid2 = pid_to_pid2(pid)
            return f"PID: {pid}\nPID2: {pid2}"
        except Exception as e:
            raise ValueError(f"ECDATA 변환 중 오류: {e}")
    
    else:
        # 길이 불일치 시 구체적인 안내 메시지
        if total_length < 23:
            expected = "PID: 23자리(하이픈 3개), ECDATA: 20자리, PID2: 31자리"
        elif total_length > 31:
            expected = "PID: 23자리(하이픈 3개), ECDATA: 20자리, PID2: 31자리"
        else:
            expected = "PID: 23자리(하이픈 3개), ECDATA: 20자리, PID2: 31자리"
        
        raise ValueError(
            f"길이가 맞지 않습니다. 값을 제대로 입력해주세요.\n"
            f"현재 입력: {total_length}자리 (하이픈 {hyphen_count}개)\n"
            f"지원 형식:\n"
            f"  - PID: XXXXX-XXXXX-XXXXX-XXXXX (23자리, 하이픈 3개)\n"
            f"  - ECDATA: 20자리 문자열 (하이픈 없음)\n"
            f"  - PID2: 31자리 문자열 (하이픈 포함 가능)\n"
            f"예상 형식: {expected}"
        )


def main() -> None:
    """메인 함수"""
    print("=" * 60)
    print("한컴 오피스 제품키 변환 도구 (통합 버전)")
    print("=" * 60)
    print("지원하는 변환:")
    print("PID (23자리) → ECDATA + PID2")
    print("PID2 (31자리) → ECDATA + PID")
    print("ECDATA (20자리) → PID + PID2")
    print("=" * 60)
    
    try:
        input_key = input("변환할 키를 입력하세요: ").strip()
        if not input_key:
            print("입력이 비어있습니다.")
            return
        
        result = convert_key(input_key)
        print(f"\n변환 결과:\n{result}")
        
    except Exception as exc:
        print(f"오류: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
