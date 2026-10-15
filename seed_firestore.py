"""Seed initial plant catalog data into Firestore for SproutCare."""
from google.cloud import firestore

# NOTE: Project ID is hardcoded as required for Agent Platform runtime compatibility.
PROJECT_ID = "qwiklabs-gcp-03-dd214ec01318"

def seed():
    db = firestore.Client(project=PROJECT_ID)
    plants_ref = db.collection("plants")

    sample_plants = [
        {
            "id": "monstera-deliciosa",
            "name": "몬스테라 델리시오사 (Monstera Deliciosa)",
            "botanical_name": "Monstera deliciosa",
            "category": "관엽식물",
            "price": 32000,
            "light_requirement": "밝은 간접광 (직사광선 피하기)",
            "water_frequency_days": 7,
            "difficulty": "쉬움",
            "pet_safe": False,
            "description": "잎에 멋진 구멍과 갈라짐이 생기는 대표적인 인테리어 플랜트입니다. 초보자도 쉽게 키울 수 있습니다.",
            "care_tips": "겉흙이 마르면 화분 밑으로 물이 흘러나올 때까지 듬뿍 주세요. 과습에 주의합니다."
        },
        {
            "id": "snake-plant",
            "name": "산세베리아 (Snake Plant)",
            "botanical_name": "Sansevieria trifasciata",
            "category": "다육식물/공기정화",
            "price": 18000,
            "light_requirement": "반음지~밝은 빛 모두 적응 가능 (저조도 강함)",
            "water_frequency_days": 21,
            "difficulty": "매우 쉬움",
            "pet_safe": False,
            "description": "공기 정화 능력이 탁월하고 물을 자주 주지 않아도 잘 자라 관리가 가장 쉬운 반려식물입니다.",
            "care_tips": "흙이 완전히 말랐을 때 물을 줍니다. 겨울철에는 물주기를 한 달 이상 건너뛰어도 좋습니다."
        },
        {
            "id": "boston-fern",
            "name": "보스턴 고사리 (Boston Fern)",
            "botanical_name": "Nephrolepis exaltata",
            "category": "양치식물",
            "price": 22000,
            "light_requirement": "부드러운 간접광",
            "water_frequency_days": 4,
            "difficulty": "보통",
            "pet_safe": True,
            "description": "반려동물(강아지/고양이)에게 100% 안전한 식물로, 풍성하고 시원한 잎이 매력적인 식물입니다.",
            "care_tips": "높은 습도를 좋아하므로 잎 주변에 자주 분무해 주시고, 흙이 촉촉하게 유지되도록 해주세요."
        },
        {
            "id": "peperomia-obtusifolia",
            "name": "청페페 (Baby Rubber Plant)",
            "botanical_name": "Peperomia obtusifolia",
            "category": "소형 관엽",
            "price": 15000,
            "light_requirement": "중간~밝은 간접광",
            "water_frequency_days": 10,
            "difficulty": "쉬움",
            "pet_safe": True,
            "description": "도톰하고 둥근 잎을 가진 작고 귀여운 식물입니다. 고양이와 강아지에게 무해하며 테이블 위에 두기 좋습니다.",
            "care_tips": "잎에 수분을 저장하므로 겉흙이 바짝 말랐을 때 물을 주는 것이 좋습니다."
        },
        {
            "id": "peace-lily",
            "name": "스파티필름 (Peace Lily)",
            "botanical_name": "Spathiphyllum",
            "category": "꽃/공기정화",
            "price": 25000,
            "light_requirement": "중간 간접광~반음지",
            "water_frequency_days": 5,
            "difficulty": "쉬움",
            "pet_safe": False,
            "description": "하얗고 우아한 꽃대(불염포)를 피우며 공기 중 유해물질을 제거하는 능력이 우수합니다.",
            "care_tips": "물이 부족하면 잎이 축 처져 물주기 신호를 직관적으로 알려줍니다."
        }
    ]

    for p in sample_plants:
        doc_id = p["id"]
        plants_ref.document(doc_id).set(p)
        print(f"Added plant: {p['name']} ({doc_id})")

    # Sample user garden
    garden_ref = db.collection("gardens").document("demo_user")
    garden_ref.set({
        "user_id": "demo_user",
        "user_name": "초보식집사",
        "lighting_condition": "남동향 거실 (밝은 간접광)",
        "has_pets": True,
        "pet_type": "고양이",
        "plants": [
            {
                "plant_id": "peperomia-obtusifolia",
                "nickname": "페페",
                "acquired_date": "2026-09-01",
                "last_watered": "2026-10-10",
                "notes": "새 잎이 잘 돋아나고 있음"
            }
        ]
    })
    print("Added sample garden for demo_user")

if __name__ == "__main__":
    seed()
