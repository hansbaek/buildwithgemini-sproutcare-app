"""Domain calculation and gardening care utilities for SproutCare."""
import math
from typing import Dict, Any

def calculate_soil_mix_and_fertilizer(
    plant_type: str,
    pot_diameter_cm: float,
    pot_height_cm: float,
    water_volume_liters: float = 1.0
) -> Dict[str, Any]:
    """화분 크기와 식물 유형에 따른 최적의 흙 배합비(L)와 비료 희석량(ml)을 계산합니다.

    Args:
        plant_type: 식물 종류나 특성 (예: '몬스테라', '다육이', '산세베리아', '고사리', '관엽식물')
        pot_diameter_cm: 원형 화분의 상단 지름 (단위: cm, 예: 20)
        pot_height_cm: 화분의 높이 (단위: cm, 예: 25)
        water_volume_liters: 물을 줄 때 사용할 물의 양 (단위: L, 기본값: 1.0L)

    Returns:
        화분 용량(L), 흙 종류별 필요 리터(상토, 펄라이트, 바크/마사토), 액체 비료 추천 희석량(ml/방울)
    """
    # Calculate volume of cylinder in cubic centimeters (cm^3) -> convert to Liters
    radius = pot_diameter_cm / 2.0
    volume_cm3 = math.pi * (radius ** 2) * pot_height_cm
    # Practical usable potting volume (excluding top margin 10%)
    volume_liters = round((volume_cm3 / 1000.0) * 0.9, 2)

    plant_lower = plant_type.lower()
    
    # Soil mix ratio rules
    # 1. Succulent / Snake plant (High drainage): 상토 30%, 마사/펄라이트 70%
    if any(k in plant_lower for k in ["다육", "선인장", "산세베리아", "스네이크", "succulent", "cactus"]):
        soil_profile = "배수 극대화형 (다육식물/산세베리아용)"
        potting_soil_pct = 0.30
        perlite_pct = 0.40
        drainage_stone_pct = 0.30
        fertilizer_dilution_ratio = "2000:1 (매우 연하게)"
        fertilizer_ml_per_liter = 0.5
    # 2. Fern / Moisture-loving (Moisture retention): 상토 60%, 펄라이트 30%, 피트모스/바크 10%
    elif any(k in plant_lower for k in ["고사리", "양치", "fern", "보스턴"]):
        soil_profile = "보습 & 통기 균형형 (고사리/양치식물용)"
        potting_soil_pct = 0.60
        perlite_pct = 0.25
        drainage_stone_pct = 0.15
        fertilizer_dilution_ratio = "1500:1"
        fertilizer_ml_per_liter = 0.7
    # 3. Monstera / Tropical / Aroid (Aerial roots, good aeration): 상토 50%, 펄라이트 25%, 바크 25%
    else:
        soil_profile = "표준 열대 관엽형 (몬스테라/필로덴드론용)"
        potting_soil_pct = 0.50
        perlite_pct = 0.25
        drainage_stone_pct = 0.25
        fertilizer_dilution_ratio = "1000:1 (표준)"
        fertilizer_ml_per_liter = 1.0

    potting_soil_l = round(volume_liters * potting_soil_pct, 2)
    perlite_l = round(volume_liters * perlite_pct, 2)
    drainage_stone_l = round(volume_liters * drainage_stone_pct, 2)
    fertilizer_ml = round(fertilizer_ml_per_liter * water_volume_liters, 2)

    return {
        "pot_specs": {
            "diameter_cm": pot_diameter_cm,
            "height_cm": pot_height_cm,
            "total_soil_volume_liters": volume_liters
        },
        "soil_mix_recipe": {
            "profile_name": soil_profile,
            "potting_soil_liters": potting_soil_l,
            "perlite_liters": perlite_l,
            "bark_or_gravel_liters": drainage_stone_l,
            "instructions": f"상토 {potting_soil_l}L, 펄라이트 {perlite_l}L, 바크/마사 {drainage_stone_l}L를 골고루 섞어 화분에 채워주세요."
        },
        "fertilizer_guide": {
            "target_water_volume_l": water_volume_liters,
            "dilution_ratio": fertilizer_dilution_ratio,
            "recommended_fertilizer_ml": fertilizer_ml,
            "instructions": f"물 {water_volume_liters}L당 액체비료 {fertilizer_ml}ml(약 {int(fertilizer_ml * 20)}방울)을 희석하여 시비하세요."
        }
    }
