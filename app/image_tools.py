"""Image generation tools for SproutCare using gemini-3.1-flash-lite-image and Cloud Storage."""
import uuid
import datetime
from typing import Dict, Any, Optional
from google import genai
from google.genai import types
from google.cloud import storage
from google.adk.tools import ToolContext

# Hardcoded project and bucket names to prevent project number resolution issues in Agent Platform
PROJECT_ID = "qwiklabs-gcp-03-dd214ec01318"
BUCKET_NAME = "sproutcare-storage-qwiklabs-gcp-03-dd214ec01318"
MODEL_NAME = "gemini-3.1-flash-lite-image"
LOCATION = "global"

def generate_plant_image(
    prompt: str,
    tool_context: ToolContext,
    aspect_ratio: str = "1:1",
    plant_name: Optional[str] = None
) -> Dict[str, Any]:
    """반려식물 또는 가드닝 관련 고화질 이미지를 생성하고 공개 Cloud Storage에 저장합니다.

    Args:
        prompt: 생성할 이미지에 대한 상세 설명 (예: '싱그러운 초록색 몬스테라 화분, 자연광이 드는 밝은 거실')
        tool_context: ADK 도구 컨텍스트 (Playground Artifacts 저장을 위해 시스템 주입)
        aspect_ratio: 이미지 가로세로 비율 (예: '1:1', '4:3', '16:9', 기본값: '1:1')
        plant_name: 관련 식물 이름 (선택 사항, 파일명 및 메타데이터용)

    Returns:
        생성 상태, 공개 HTTP URL, 파일명, 프롬프트 정보
    """
    try:
        client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

        full_prompt = (
            f"Generate a beautiful, high-quality, vibrant photograph of {prompt}. "
            f"Clean background, soft natural lighting, realistic gardening aesthetic."
        )

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=full_prompt,
        )

        image_bytes = None
        mime_type = "image/png"

        for candidate in response.candidates:
            if not candidate.content or not candidate.content.parts:
                continue
            for part in candidate.content.parts:
                if part.inline_data and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    if part.inline_data.mime_type:
                        mime_type = part.inline_data.mime_type
                    break
            if image_bytes:
                break

        if not image_bytes:
            return {"error": "모델로부터 이미지를 생성하지 못했습니다."}

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        slug = (plant_name or "plant").lower().replace(" ", "_")
        filename = f"{slug}_{timestamp}_{unique_id}.png"

        # 1. Save artifact to ToolContext for ADK Playground Artifacts tab
        try:
            artifact_part = types.Part(
                inline_data=types.Blob(
                    mime_type=mime_type,
                    data=image_bytes
                )
            )
            tool_context.save_artifact(
                filename=filename,
                artifact=artifact_part,
                custom_metadata={"prompt": prompt, "plant_name": plant_name or ""}
            )
        except Exception as e:
            # Artifact saving non-blocking
            print(f"Warning: tool_context.save_artifact failed: {e}")

        # 2. Upload to public Cloud Storage bucket
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

        return {
            "status": "success",
            "message": f"'{plant_name or prompt}'의 식물 이미지가 성공적으로 생성되었습니다.",
            "public_url": public_url,
            "filename": filename,
            "prompt_used": prompt
        }

    except Exception as e:
        return {"error": f"이미지 생성 또는 업로드 중 오류 발생: {str(e)}"}
