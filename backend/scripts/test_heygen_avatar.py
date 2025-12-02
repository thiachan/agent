"""
Test script to find a working HeyGen avatar ID
This script tests avatars from the listing to find one that actually works for video generation.

Usage:
    python -m scripts.test_heygen_avatar
"""

import asyncio
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from app.services.heygen_service import heygen_service
from app.core.config import settings


async def test_avatars():
    """Test avatars to find one that works"""
    print("=" * 80)
    print("Testing HeyGen Avatars for Video Generation")
    print("=" * 80)
    print()
    
    if not settings.HEYGEN_API_KEY:
        print("[ERROR] HEYGEN_API_KEY not configured!")
        return
    
    # Get list of avatars
    print("Fetching avatars...")
    avatars = await heygen_service.list_avatars()
    
    if not avatars:
        print("[ERROR] No avatars found!")
        return
    
    print(f"Found {len(avatars)} avatars. Testing first 20...")
    print()
    
    # Test script (minimal)
    test_script = "Hello, this is a test video."
    
    # Get a working voice ID
    voices = await heygen_service.list_voices()
    if not voices:
        print("[ERROR] No voices found!")
        return
    
    voice_id = voices[0].get("voice_id") or voices[0].get("id")
    print(f"Using voice ID: {voice_id}")
    print()
    
    # Test avatars
    endpoint = f"{settings.HEYGEN_API_URL.rstrip('/')}/v2/video/generate"
    headers = {
        "X-Api-Key": settings.HEYGEN_API_KEY,
        "Content-Type": "application/json"
    }
    
    working_avatars = []
    failed_avatars = []
    
    for i, avatar in enumerate(avatars[:20], 1):
        avatar_id = avatar.get("avatar_id") or avatar.get("id")
        avatar_name = avatar.get("name", "Unnamed")
        
        if not avatar_id:
            continue
        
        print(f"Testing {i}/20: {avatar_name} (ID: {avatar_id})...", end=" ")
        
        payload = {
            "video_inputs": [
                {
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_id,
                        "avatar_style": "normal"
                    },
                    "voice": {
                        "type": "text",
                        "input_text": test_script,
                        "voice_id": voice_id
                    },
                    "background": {
                        "type": "color",
                        "value": "#FAFAFA"
                    }
                }
            ]
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(endpoint, json=payload, headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    video_id = result.get("data", {}).get("video_id")
                    if video_id:
                        print("[OK] Works!")
                        working_avatars.append({
                            "id": avatar_id,
                            "name": avatar_name,
                            "video_id": video_id
                        })
                    else:
                        print("[WARNING] 200 but no video_id")
                        failed_avatars.append({"id": avatar_id, "name": avatar_name, "reason": "No video_id"})
                elif response.status_code == 404:
                    error_data = response.json()
                    error_code = error_data.get("error", {}).get("code", "")
                    if error_code == "avatar_not_found":
                        print("[FAIL] Avatar not found")
                        failed_avatars.append({"id": avatar_id, "name": avatar_name, "reason": "Not found"})
                    else:
                        print(f"[FAIL] {error_code}")
                        failed_avatars.append({"id": avatar_id, "name": avatar_name, "reason": error_code})
                else:
                    print(f"[FAIL] Status {response.status_code}")
                    failed_avatars.append({"id": avatar_id, "name": avatar_name, "reason": f"Status {response.status_code}"})
        except Exception as e:
            print(f"[ERROR] {str(e)[:50]}")
            failed_avatars.append({"id": avatar_id, "name": avatar_name, "reason": str(e)[:50]})
    
    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()
    
    if working_avatars:
        print(f"[SUCCESS] Found {len(working_avatars)} working avatar(s):\n")
        for avatar in working_avatars:
            print(f"  ✓ {avatar['name']}")
            print(f"    ID: {avatar['id']}")
            print(f"    Video ID: {avatar['video_id']}")
            print()
        
        print("\n" + "=" * 80)
        print("RECOMMENDED CONFIGURATION")
        print("=" * 80)
        print(f"\nAdd to your .env file:")
        print(f"  HEYGEN_AVATAR_ID={working_avatars[0]['id']}")
        print(f"  HEYGEN_VOICE_ID={voice_id}")
    else:
        print("[ERROR] No working avatars found!")
        print("\nFailed avatars:")
        for avatar in failed_avatars[:5]:
            print(f"  - {avatar['name']} ({avatar['id']}): {avatar['reason']}")
    
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_avatars())





