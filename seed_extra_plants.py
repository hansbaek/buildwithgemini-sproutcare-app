#!/usr/bin/env python3
import os
from google.cloud import firestore

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-03-dd214ec01318")

EXTRA_PLANTS = [
    {
        "id": "pothos-njoy",
        "name": "엔조이 스킨답서스 (Pothos N'Joy)",
        "botanical_name": "Epipremnum aureum 'N-Joy'",
        "category": "덩굴식물",
        "price": 14000,
        "difficulty": "쉬움",
        "light_requirement": "밝은 간접광",
        "water_frequency_days": 7,
        "pet_safe": False,
        "description": "선명한 화이트와 그린의 콤팩트한 패치 무늬가 귀여운 소형 스킨답서스입니다.",
        "care_tips": "잎이 작고 아담하여 책상 위나 작은 선반에 잘 어울립니다."
    },
    {
        "id": "pothos-neon",
        "name": "형광 스킨답서스 / 네온 포토스 (Neon Pothos)",
        "botanical_name": "Epipremnum aureum 'Neon'",
        "category": "덩굴식물",
        "price": 13000,
        "difficulty": "매우 쉬움",
        "light_requirement": "반음지~간접광",
        "water_frequency_days": 7,
        "pet_safe": False,
        "description": "눈이 시릴 정도로 맑고 화사한 라임 형광빛 잎을 자랑하는 공기정화 식물입니다.",
        "care_tips": "빛이 너무 없으면 짙은 녹색으로 변할 수 있으니 밝은 실내에 두세요."
    },
    {
        "id": "dracaena-reflexa-song-of-india",
        "name": "인디아목 / 송오브인디아 (Song of India)",
        "botanical_name": "Dracaena reflexa",
        "category": "드라세나",
        "price": 26000,
        "difficulty": "쉬움",
        "light_requirement": "밝은 간접광",
        "water_frequency_days": 8,
        "pet_safe": False,
        "description": "황금빛 노란 테두리를 두른 부드러운 곡선의 잎들이 빽빽하게 자라나는 관목입니다.",
        "care_tips": "새집증후군 유해물질 제거에 탁월하며 수형이 멋스럽습니다."
    },
    {
        "id": "ficus-triangularis-variegata",
        "name": "삼각잎상수리 / 무늬 삼각고무나무 (Variegated Triangle Ficus)",
        "botanical_name": "Ficus triangularis 'Variegata'",
        "category": "목본/고무나무",
        "price": 38000,
        "difficulty": "보통",
        "light_requirement": "밝은 간접광",
        "water_frequency_days": 7,
        "pet_safe": False,
        "description": "완벽한 역삼각형 하트 모양 잎에 크림색 마블링이 들어간 감성 고무나무입니다.",
        "care_tips": "빛 부족이나 건조 시 잎을 떨굴 수 있으니 채광 좋은 창가에 두세요."
    },
    {
        "id": "fittonia-albivenis",
        "name": "화이트스타 / 레드스타 피토니아 (Fittonia Nerve Plant)",
        "botanical_name": "Fittonia albivenis",
        "category": "소형관엽/테라리움",
        "price": 7000,
        "difficulty": "보통",
        "light_requirement": "반음지~간접광",
        "water_frequency_days": 4,
        "pet_safe": True,
        "description": "그물망처럼 섬세한 흰색/붉은색 잎맥이 돋보이며 습도를 좋아하는 테라리움 식물입니다.",
        "care_tips": "물이 마르면 잎이 기절하듯 처지며, 물을 주면 1~2시간 만에 다시 일어납니다."
    },
    {
        "id": "hypoestes-phyllostachya",
        "name": "하이포에스테스 / 주근깨풀 (Polka Dot Plant)",
        "botanical_name": "Hypoestes phyllostachya",
        "category": "소형관엽",
        "price": 6000,
        "difficulty": "쉬움",
        "light_requirement": "밝은 간접광",
        "water_frequency_days": 4,
        "pet_safe": True,
        "description": "핑크, 레드, 화이트 색상의 주근깨 점박이 무늬가 잎 전체에 뿌려져 있습니다.",
        "care_tips": "빛을 많이 받아야 점박이 색상이 짙어지며 순지르기를 해주면 덤불처럼 자랍니다."
    },
    {
        "id": "spathiphyllum-domino",
        "name": "스파티필름 도미노 (Variegated Peace Lily)",
        "botanical_name": "Spathiphyllum 'Domino'",
        "category": "개화/희귀식물",
        "price": 28000,
        "difficulty": "쉬움",
        "light_requirement": "반음지~간접광",
        "water_frequency_days": 5,
        "pet_safe": False,
        "description": "주름진 잎 위에 눈송이가 내린 듯 하얀 마블링이 들어간 희귀 무늬 스파티필름입니다.",
        "care_tips": "일반 스파티필름처럼 공기정화 능력이 탁월하고 키우기 무던합니다."
    },
    {
        "id": "sansevieria-cylindrica",
        "name": "스투키 / 실린드리카 (Sansevieria Cylindrica)",
        "botanical_name": "Dracaena cylindrica",
        "category": "다육/공기정화",
        "price": 18000,
        "difficulty": "매우 쉬움",
        "light_requirement": "음지~양지",
        "water_frequency_days": 30,
        "pet_safe": False,
        "description": "원통형 오이 모양의 튼튼한 줄기가 곧게 뻗어 음이온 방출량이 극대화된 국민 식물입니다.",
        "care_tips": "한 달에 한 번 정도만 관수하고 속흙까지 바짝 말려야 무르지 않습니다."
    },
    {
        "id": "crassula-tetragona",
        "name": "미니 소나무 다육 / 크라슐라 테트라고나 (Mini Pine Tree)",
        "botanical_name": "Crassula tetragona",
        "category": "다육식물",
        "price": 9000,
        "difficulty": "매우 쉬움",
        "light_requirement": "양지~간접광",
        "water_frequency_days": 18,
        "pet_safe": False,
        "description": "작은 미니어처 소나무를 닮아 동양적인 멋과 피톤치드 숲 느낌을 주는 다육입니다.",
        "care_tips": "햇빛을 듬뿍 쬐어주면 목대가 단단하고 짱짱하게 굳어집니다."
    },
    {
        "id": "pachyphytum-oviferum",
        "name": "미인 다육 / 문스톤 (Moonstone Succulent)",
        "botanical_name": "Pachyphytum oviferum",
        "category": "다육식물",
        "price": 8000,
        "difficulty": "쉬움",
        "light_requirement": "풍부한 양지",
        "water_frequency_days": 20,
        "pet_safe": True,
        "description": "하얀 분가루를 뒤집어쓴 통통한 조약돌이나 사탕 같은 달콤한 비주얼의 다육입니다.",
        "care_tips": "잎에 분가루가 지워지지 않도록 손으로 만지지 말고 흙에 물을 주세요."
    }
]

db = firestore.Client(project=PROJECT_ID)
plants_ref = db.collection("plants")
batch = db.batch()
for plant in EXTRA_PLANTS:
    batch.set(plants_ref.document(plant["id"]), plant, merge=True)
batch.commit()
print(f"Added {len(EXTRA_PLANTS)} extra plants successfully.")
