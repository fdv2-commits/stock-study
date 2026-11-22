"""테스트에서 프로젝트 폴더의 모듈(config, quiz)을 import할 수 있게 경로를 추가한다."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
