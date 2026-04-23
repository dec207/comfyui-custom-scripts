# 캐릭터 이미지 생성

## 사용하는 모델

- 기본 체크포인트: `strangeThingMixToon_v3.safetensors`
- 스타일 LoRA: `perfection style.safetensors`
- 포즈 고정용 ControlNet: `OpenPoseXL2.safetensors`

## 파일 구성

- `run.py`: 실행기
- `workflows/`: 기존 캐릭터별 워크플로우
- `workflows/base/`: 캐릭터별 베이스 워크플로우
- `options/poses/`: 재사용할 포즈 옵션
- `options/outfits/`: 재사용할 의상 옵션
- `models/`: 체크포인트와 LoRA 모델

## 생성 과정

1. `run.py`를 실행한다.
2. 캐릭터를 숫자로 고른다.
3. 포즈를 숫자로 고른다.
4. 의상을 숫자로 고른다.
5. 선택한 캐릭터의 베이스 워크플로우에 포즈/의상 옵션을 붙인다.
6. ComfyUI 서버에 워크플로우를 전달한다.
7. 결과 이미지는 `C:\workspace\img_bank`에 저장된다.

## 실행 예시

```powershell
cd C:\workspace\comfyui_custom_repo
C:\workspace\comfyui\venv\Scripts\python.exe run.py
```

명령으로 직접 지정할 수도 있다.

```powershell
C:\workspace\comfyui\venv\Scripts\python.exe run.py --character Da-un --pose front_standing --outfit neutral_underwear
```
