"""Google Maps Geocoding & Places API (New) tools for SproutCare."""
import os
import urllib.parse
import urllib.request
import json
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

def _get_api_key() -> str:
    key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not key or key == "PASTE_KEY_HERE":
        raise ValueError("GOOGLE_MAPS_API_KEY 환경 변수가 설정되지 않았거나 유효하지 않습니다. .env 파일에 올바른 API 키를 입력해 주세요.")
    return key

def geocode_address(address: str) -> Dict[str, Any]:
    """주소나 도시 이름을 위도/경도 좌표로 변환합니다 (Geocoding API).

    Args:
        address: 검색할 주소 또는 장소명 (예: '서울시 강남구 테헤란로', 'San Francisco, CA')

    Returns:
        변환된 주소, 위도(lat), 경도(lng) 및 포맷된 전체 주소 정보
    """
    api_key = _get_api_key()
    encoded_addr = urllib.parse.quote(address)
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_addr}&key={api_key}"

    req = urllib.request.Request(url, headers={"User-Agent": "SproutCare/1.0"})
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("status") != "OK" or not data.get("results"):
                return {"error": f"주소 변환 실패: {data.get('status', 'NO_RESULTS')}", "raw": data}
            
            first = data["results"][0]
            loc = first["geometry"]["location"]
            return {
                "status": "success",
                "formatted_address": first.get("formatted_address"),
                "latitude": loc["lat"],
                "longitude": loc["lng"],
                "place_id": first.get("place_id")
            }
    except Exception as e:
        return {"error": f"Geocoding 요청 중 오류 발생: {str(e)}"}

def search_nearby_places(
    latitude: float,
    longitude: float,
    radius_meters: float = 3000.0,
    place_type: str = "florist",
    max_results: int = 5
) -> List[Dict[str, Any]]:
    """특정 좌표 주변의 관심 장소(꽃집, 식물원, 묘목장 등)를 검색합니다 (Places API New).

    Args:
        latitude: 중심 위도 (예: 37.4979)
        longitude: 중심 경도 (예: 127.0276)
        radius_meters: 검색 반경 (미터 단위, 기본값: 3000m)
        place_type: 검색할 장소 유형 (기본값: 'florist' / 꽃집, 정원용품점 등)
        max_results: 반환할 최대 결과 수 (기본값: 5)

    Returns:
        주변 장소 목록 (이름, 포맷된 주소, 위치 좌표, 평점 등)
    """
    api_key = _get_api_key()
    url = "https://places.googleapis.com/v1/places:searchNearby"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.primaryType"
    }

    body = {
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "radius": float(radius_meters)
            }
        },
        "includedPrimaryTypes": [place_type],
        "maxResultCount": int(max_results)
    }

    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            places = data.get("places", [])
            results = []
            for p in places:
                results.append({
                    "name": p.get("displayName", {}).get("text", "이름 없음"),
                    "formatted_address": p.get("formattedAddress", "주소 없음"),
                    "latitude": p.get("location", {}).get("latitude"),
                    "longitude": p.get("location", {}).get("longitude"),
                    "rating": p.get("rating"),
                    "user_ratings_total": p.get("userRatingCount"),
                    "type": p.get("primaryType")
                })
            return results
    except Exception as e:
        return [{"error": f"Places API 요청 중 오류 발생: {str(e)}"}]
