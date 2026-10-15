# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from app.firestore_tools import (
    search_plant_catalog,
    get_plant_care_details,
    get_user_garden,
    record_plant_watering,
    add_plant_to_garden,
)
from app.gardening_tools import calculate_soil_mix_and_fertilizer
from app.maps_tools import geocode_address, search_nearby_places
from app.image_tools import generate_plant_image
from app.video_tools import generate_plant_video
from app.a2ui_utils import a2ui_callback
from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.agents.callback_context import CallbackContext

MODEL = "gemini-2.5-flash"
AGENT_ENGINE_RESOURCE = "projects/625300775459/locations/us-east1/reasoningEngines/7568119953400791040"
SANDBOX_RESOURCE = "projects/625300775459/locations/us-east1/reasoningEngines/7568119953400791040/sandboxEnvironments/8705431691428102144"

# WRITE: 대화가 끝난 후 사용자의 선호도, 키우는 식물, 특이사항을 Memory Bank로 지속 저장
async def generate_memories_callback(callback_context: CallbackContext):
    try:
        await callback_context.add_session_to_memory()
    except Exception as e:
        print(f"Skipping memory bank storage: {e}")
    return None

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "스마트 반려식물 케어 & 가드닝 샵 어시스턴트인 '스프라우트케어(SproutCare)'입니다.\n"
        "[중요: 장기 기억(Memory Bank) 관리 지침]\n"
        "- 사용자의 모든 알레르기(식물/꽃가루 알레르기, 비염, 특정 수액 접촉 피부염 등) 및 식이 제한 사항(채식, 글루텐 프리, 허브/식용 작물 섭취 제한 등)을 반드시 영구 기억으로 유지하세요.\n"
        "- 사용자가 알레르기나 식이/건강상 제한 사항을 언급하면, 이를 명확하게 인지하고 확인하는 답변을 남겨 장기 메모리(Memory Bank)에 즉시 정확히 추출/보존되도록 하세요.\n"
        "- 향후 모든 대화 및 추천(식물 추천, 식용 허브/텃밭 가이드 등)에서 기억된 사용자의 알레르기와 식이 제한 사항을 최우선으로 검토하고 안전한 조언만을 제공하세요.\n\n"
        "제공된 전문 도구들과 격리된 Python 샌드박스를 활용하여 다음을 지원합니다:\n"
        "1. 식물 카탈로그 검색 (search_plant_catalog): 사용자의 조도 환경, 난이도, 반려동물 안전성에 맞춘 식물 추천\n"
        "2. 상세 관리 가이드 (get_plant_care_details): 물주기 주기, 적정 광량, 팁 안내\n"
        "3. 내 정원 관리 (get_user_garden, record_plant_watering, add_plant_to_garden): 식물 목록 조회, 물주기 기록, 새 식물 입양/등록\n"
        "4. 흙 배합비 & 비료 계산 (calculate_soil_mix_and_fertilizer): 화분 크기(지름/높이)와 식물 종류에 맞는 상토/펄라이트/바크 비율 및 비료 희석량 정밀 계산\n"
        "5. 주변 꽃집/식물원 검색 (geocode_address, search_nearby_places): 사용자의 주소나 동네 위치를 좌표로 변환하고 주변 꽃집/가드닝 샵 탐색\n"
        "6. 식물 이미지 생성 (generate_plant_image): 식물이나 인테리어 화분 사진을 생성하여 Cloud Storage 공개 URL과 함께 제공\n"
        "7. 식물 비디오 생성 (generate_plant_video): 식물 성장 타임랩스나 물주기/관리 시연 등의 짧은 영상을 생성하여 Cloud Storage 공개 https URL과 함께 제공\n"
        "8. Python 코드 실행 (Agent Engine Sandbox): 사용자가 코드 실행, 수학 계산, 시뮬레이션, 통계 분석을 요청할 때 가상의 run_code 함수를 호출하지 마시고, 직접 ```python ... ``` 코드 블록을 작성하세요."
    ),
    workflow_description="사용자의 요청을 분석하여 도구를 호출하고, 카드나 요약 정보가 적합한 경우 구조화된 UI(A2UI)로 반환하세요.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    code_executor=AgentEngineSandboxCodeExecutor(
        sandbox_resource_name=SANDBOX_RESOURCE,
        agent_engine_resource_name=AGENT_ENGINE_RESOURCE,
    ),
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
    tools=[
        PreloadMemoryTool(),
        search_plant_catalog,
        get_plant_care_details,
        get_user_garden,
        record_plant_watering,
        add_plant_to_garden,
        calculate_soil_mix_and_fertilizer,
        geocode_address,
        search_nearby_places,
        generate_plant_image,
        generate_plant_video,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
