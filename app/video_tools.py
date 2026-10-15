"""Video generation tools for SproutCare using veo-3.1-lite-generate-001 and Cloud Storage."""
import time
import uuid
import datetime
from typing import Dict, Any, Optional
from google import genai
from google.genai import types
from google.cloud import storage
from google.adk.tools import ToolContext

PROJECT_ID = "qwiklabs-gcp-03-dd214ec01318"
BUCKET_NAME = "sproutcare-storage-qwiklabs-gcp-03-dd214ec01318"
MODEL_NAME = "veo-3.1-lite-generate-001"
LOCATION = "us-central1"


def generate_plant_video(
    prompt: str,
    tool_context: ToolContext,
    plant_name: Optional[str] = None,
    duration_seconds: int = 4
) -> Dict[str, Any]:
    """반려식물 또는 가드닝 관련 짧은 동영상(타임랩스, 케어/물주기 모션)을 생성하고 공개 Cloud Storage에 저장합니다.

    Args:
        prompt: 생성할 비디오에 대한 설명 (예: '몬스테라 새 잎이 천천히 펼쳐지는 햇살 속 타임랩스', '화분에 물을 주는 싱그러운 모습')
        tool_context: ADK 도구 컨텍스트 (Playground 아티팩트 보관용 시스템 주입 파라미터)
        plant_name: 관련 식물 이름 (선택 사항, 파일명 및 메타데이터용)
        duration_seconds: 영상 길이(초). 기본값: 4 (지원값: 4, 6, 8)

    Returns:
        상태, 공개 HTTP URL, 파일명, 사용된 프롬프트 정보
    """
    try:
        # Validate duration
        if duration_seconds not in (4, 6, 8):
            duration_seconds = 4

        client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

        full_prompt = (
            f"A beautiful, realistic cinematic video showing {prompt}. "
            f"Soft natural sunlight, lush green botanical aesthetics, smooth camera motion."
        )

        op = client.models.generate_videos(
            model=MODEL_NAME,
            source=types.GenerateVideosSource(prompt=full_prompt),
            config=types.GenerateVideosConfig(
                duration_seconds=duration_seconds,
                aspect_ratio="16:9",
                number_of_videos=1,
            )
        )

        # Poll operation until completion (timeout ~120 seconds)
        max_attempts = 24
        video_bytes = None
        mime_type = "video/mp4"

        for _ in range(max_attempts):
            time.sleep(5)
            status = client.operations.get(op)
            if status.done:
                if status.error:
                    return {"error": f"비디오 생성 중 오류 발생: {status.error}"}
                if status.response and status.response.generated_videos:
                    gv = status.response.generated_videos[0]
                    if gv.video and gv.video.video_bytes:
                        video_bytes = gv.video.video_bytes
                        if gv.video.mime_type:
                            mime_type = gv.video.mime_type
                break

        if not video_bytes:
            return {"error": "비디오 생성 시간 초과 또는 유효한 비디오 데이터를 받지 못했습니다."}

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        # Clean slug to alphanumeric ASCII characters for clean GCS object names
        import re, urllib.parse
        clean_slug = re.sub(r"[^a-zA-Z0-9_]+", "", (plant_name or "plant_video").replace(" ", "_"))
        if not clean_slug:
            clean_slug = "plant_video"
        filename = f"{clean_slug}_{timestamp}_{unique_id}.mp4"

        # 1. Save artifact to ToolContext for ADK Playground
        try:
            artifact_part = types.Part(
                inline_data=types.Blob(
                    mime_type=mime_type,
                    data=video_bytes
                )
            )
            import asyncio
            asyncio.create_task(
                tool_context.save_artifact(
                    filename=filename,
                    artifact=artifact_part,
                    custom_metadata={"prompt": prompt, "plant_name": plant_name or "", "type": "video"}
                )
            )
        except Exception as e:
            print(f"Warning: tool_context.save_artifact failed: {e}")

        # 2. Upload to public Cloud Storage bucket
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        encoded_filename = urllib.parse.quote(filename)
        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{encoded_filename}"

        return {
            "status": "success",
            "message": f"'{plant_name or prompt}'의 식물 비디오가 성공적으로 생성되었습니다.",
            "public_url": public_url,
            "filename": filename,
            "duration_seconds": duration_seconds,
            "prompt_used": prompt
        }
    except Exception as e:
        return {"error": f"비디오 생성 도구 실행 실패: {str(e)}"}
