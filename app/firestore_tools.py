"""Firestore database tools for SproutCare."""
import datetime
from typing import Optional, Dict, Any, List
from google.cloud import firestore

# NOTE: Project ID is explicitly hardcoded as required for Agent Platform runtime compatibility.
PROJECT_ID = "qwiklabs-gcp-03-dd214ec01318"

def _get_db() -> firestore.Client:
    return firestore.Client(project=PROJECT_ID)

def search_plant_catalog(query: Optional[str] = None, pet_safe_only: Optional[bool] = None) -> List[Dict[str, Any]]:
    """반려식물 카탈로그에서 식물을 검색합니다.

    Args:
        query: 식물 이름이나 설명에 포함된 검색어 (예: '몬스테라', '초보', '고사리'). 없을 시 전체 조회.
        pet_safe_only: True일 경우 고양이/강아지 등 반려동물에게 무해한 식물만 필터링합니다.

    Returns:
        조건에 맞는 식물 목록 (이름, 가격, 난이도, 물주기 주기, 광량 조건, 반려동물 안전 여부 등)
    """
    db = _get_db()
    plants_ref = db.collection("plants")
    docs = plants_ref.stream()

    results = []
    for doc in docs:
        data = doc.to_dict()
        # Filter pet safe
        if pet_safe_only is True and not data.get("pet_safe", False):
            continue
        # Filter query string
        if query:
            q = query.lower()
            name = str(data.get("name", "")).lower()
            botanical = str(data.get("botanical_name", "")).lower()
            desc = str(data.get("description", "")).lower()
            cat = str(data.get("category", "")).lower()
            if q not in name and q not in botanical and q not in desc and q not in cat:
                continue
        results.append(data)
    return results

def get_plant_care_details(plant_name_or_id: str) -> Dict[str, Any]:
    """특정 식물의 상세 관리 가이드 및 특성을 조회합니다.

    Args:
        plant_name_or_id: 식물 이름(예: '몬스테라', '보스턴 고사리') 또는 식물 ID (예: 'monstera-deliciosa')

    Returns:
        식물 상세 정보 (광량 요건, 권장 물주기 주기, 관리 팁, 반려동물 독성 여부)
    """
    db = _get_db()
    plants_ref = db.collection("plants")
    
    # Try direct ID lookup
    doc = plants_ref.document(plant_name_or_id.lower()).get()
    if doc.exists:
        return doc.to_dict()

    # Search by partial name
    q = plant_name_or_id.lower()
    for d in plants_ref.stream():
        data = d.to_dict()
        if q in str(data.get("name", "")).lower() or q in str(data.get("botanical_name", "")).lower():
            return data

    return {"error": f"'{plant_name_or_id}'에 해당하는 식물을 찾을 수 없습니다."}

def get_user_garden(user_id: str = "demo_user") -> Dict[str, Any]:
    """사용자가 키우고 있는 내 정원(보유 식물 목록 및 최근 관리 일자)을 조회합니다.

    Args:
        user_id: 사용자 식별자 (기본값: 'demo_user')

    Returns:
        사용자의 집 환경(채광, 반려동물 정보) 및 보유 중인 식물 목록과 최근 물 준 날짜
    """
    db = _get_db()
    doc = db.collection("gardens").document(user_id).get()
    if not doc.exists:
        return {"user_id": user_id, "plants": [], "message": "등록된 정원 정보가 없습니다."}
    return doc.to_dict()

def record_plant_watering(plant_nickname_or_id: str, user_id: str = "demo_user") -> Dict[str, Any]:
    """사용자가 키우는 식물에 물을 준 날짜를 오늘로 기록/업데이트합니다.

    Args:
        plant_nickname_or_id: 물을 준 식물의 별명 또는 ID (예: '페페', 'peperomia-obtusifolia')
        user_id: 사용자 식별자 (기본값: 'demo_user')

    Returns:
        업데이트 결과 상태 및 갱신된 물주기 일자
    """
    db = _get_db()
    doc_ref = db.collection("gardens").document(user_id)
    doc = doc_ref.get()
    
    today_str = datetime.date.today().isoformat()
    if not doc.exists:
        return {"error": f"사용자 '{user_id}'의 정원 정보가 없습니다."}

    data = doc.to_dict()
    plants = data.get("plants", [])
    updated = False
    target_plant = None

    for p in plants:
        if (plant_nickname_or_id.lower() in p.get("nickname", "").lower() or 
            plant_nickname_or_id.lower() in p.get("plant_id", "").lower()):
            p["last_watered"] = today_str
            target_plant = p
            updated = True
            break

    if not updated:
        return {"error": f"정원에서 '{plant_nickname_or_id}' 식물을 찾을 수 없습니다."}

    doc_ref.update({"plants": plants})
    return {
        "status": "success",
        "message": f"'{target_plant.get('nickname')}'의 마지막 물 준 날짜가 오늘({today_str})로 기록되었습니다.",
        "plant": target_plant
    }

def add_plant_to_garden(
    nickname: str,
    plant_type: str,
    notes: Optional[str] = None,
    user_id: str = "demo_user"
) -> Dict[str, Any]:
    """사용자의 정원에 새로운 반려식물을 입양/등록합니다.

    Args:
        nickname: 사용자가 붙여준 식물 애칭/별명 (예: '몬이', '초록이')
        plant_type: 식물 종류 또는 이름 (예: '몬스테라', '보스턴 고사리', 'monstera-deliciosa')
        notes: 화분 위치나 특이사항 등 메모 (예: '거실 창가에 배치함')
        user_id: 사용자 식별자 (기본값: 'demo_user')

    Returns:
        등록 결과 및 등록된 반려식물 상세 정보
    """
    db = _get_db()
    doc_ref = db.collection("gardens").document(user_id)
    doc = doc_ref.get()

    today_str = datetime.date.today().isoformat()
    if not doc.exists:
        # Create garden if not exists
        data = {
            "user_id": user_id,
            "user_name": "식집사",
            "plants": []
        }
    else:
        data = doc.to_dict()

    plants = data.get("plants", [])
    
    # Check if duplicate nickname
    for p in plants:
        if p.get("nickname", "").lower() == nickname.lower():
            return {"error": f"이미 정원에 '{nickname}'라는 이름의 반려식물이 있습니다."}

    new_plant_entry = {
        "plant_id": plant_type.lower().replace(" ", "-"),
        "nickname": nickname,
        "plant_type": plant_type,
        "acquired_date": today_str,
        "last_watered": today_str,
        "notes": notes or "새로 입양한 반려식물"
    }
    plants.append(new_plant_entry)
    
    doc_ref.set({"plants": plants}, merge=True)
    return {
        "status": "success",
        "message": f"새 반려식물 '{nickname}'({plant_type})이(가) 정원에 성공적으로 등록되었습니다!",
        "plant": new_plant_entry
    }

