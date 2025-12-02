"""
Utility script to list available HeyGen avatars and voices
Run this script to see what avatar IDs and voice IDs are available in your HeyGen account.

Usage:
    python -m scripts.list_heygen_resources
    or
    python backend/scripts/list_heygen_resources.py
"""

import asyncio
import sys
import os
from pathlib import Path

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.heygen_service import heygen_service
from app.core.config import settings


async def list_resources():
    """List available HeyGen avatars and voices"""
    print("=" * 80)
    print("HeyGen Available Resources")
    print("=" * 80)
    print()
    
    # Check API key
    if not settings.HEYGEN_API_KEY:
        print("[ERROR] HEYGEN_API_KEY not configured!")
        print("   Please set HEYGEN_API_KEY in your .env file or environment variables.")
        return
    
    print(f"[OK] API Key: {'*' * (len(settings.HEYGEN_API_KEY) - 8)}{settings.HEYGEN_API_KEY[-8:]}")
    print(f"[OK] API URL: {settings.HEYGEN_API_URL}")
    print()
    
    # List Avatars
    print("-" * 80)
    print("AVATARS")
    print("-" * 80)
    try:
        avatars = await heygen_service.list_avatars()
        if avatars:
            print(f"\n[OK] Found {len(avatars)} avatar(s):\n")
            for i, avatar in enumerate(avatars, 1):
                avatar_id = avatar.get("avatar_id") or avatar.get("id") or "N/A"
                avatar_name = avatar.get("name") or avatar.get("avatar_name") or "Unnamed"
                avatar_type = avatar.get("type") or avatar.get("avatar_type") or "unknown"
                gender = avatar.get("gender", "N/A")
                
                print(f"  {i}. {avatar_name}")
                print(f"     ID: {avatar_id}")
                print(f"     Type: {avatar_type}")
                print(f"     Gender: {gender}")
                if avatar.get("preview_url"):
                    print(f"     Preview: {avatar.get('preview_url')}")
                print()
            
            # Show recommended configuration
            print("\n" + "=" * 80)
            print("RECOMMENDED CONFIGURATION")
            print("=" * 80)
            photo_avatars = [a for a in avatars if "photo" in (a.get("type") or a.get("avatar_type") or "").lower()]
            if photo_avatars:
                recommended = photo_avatars[0]
                recommended_id = recommended.get("avatar_id") or recommended.get("id")
                print(f"\nRecommended Photo Avatar (first found):")
                print(f"  HEYGEN_AVATAR_ID={recommended_id}")
                print(f"  Name: {recommended.get('name', 'N/A')}")
            else:
                # Use first avatar if no photo avatars found
                recommended = avatars[0]
                recommended_id = recommended.get("avatar_id") or recommended.get("id")
                print(f"\nRecommended Avatar (first available):")
                print(f"  HEYGEN_AVATAR_ID={recommended_id}")
                print(f"  Name: {recommended.get('name', 'N/A')}")
        else:
            print("[ERROR] No avatars found. Check your API key and account permissions.")
    except Exception as e:
        print(f"[ERROR] Error fetching avatars: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # List Voices
    print("-" * 80)
    print("VOICES")
    print("-" * 80)
    try:
        voices = await heygen_service.list_voices()
        if voices:
            print(f"\n[OK] Found {len(voices)} voice(s):\n")
            # Show first 10 voices as examples
            for i, voice in enumerate(voices[:10], 1):
                try:
                    voice_id = voice.get("voice_id") or voice.get("id") or "N/A"
                    voice_name = voice.get("name") or voice.get("voice_name") or "Unnamed"
                    # Remove emojis and special characters that cause encoding issues
                    voice_name = voice_name.encode('ascii', 'ignore').decode('ascii').strip()
                    if not voice_name:
                        voice_name = "Unnamed"
                    voice_gender = voice.get("gender", "N/A")
                    voice_language = voice.get("language") or voice.get("locale", "N/A")
                    
                    print(f"  {i}. {voice_name}")
                    print(f"     ID: {voice_id}")
                    print(f"     Gender: {voice_gender}")
                    print(f"     Language: {voice_language}")
                    if voice.get("preview_url"):
                        print(f"     Preview: {voice.get('preview_url')}")
                    print()
                except Exception as e:
                    # Skip voices with encoding issues
                    voice_id = voice.get("voice_id") or voice.get("id") or "N/A"
                    print(f"  {i}. [Voice ID: {voice_id}] (name encoding issue)")
                    print()
            
            if len(voices) > 10:
                print(f"  ... and {len(voices) - 10} more voices (total: {len(voices)})\n")
            
            # Show recommended configuration
            if voices:
                recommended_voice = voices[0]
                recommended_voice_id = recommended_voice.get("voice_id") or recommended_voice.get("id")
                print("\n" + "=" * 80)
                print("RECOMMENDED CONFIGURATION")
                print("=" * 80)
                print(f"\nRecommended Voice (first found):")
                print(f"  HEYGEN_VOICE_ID={recommended_voice_id}")
                print(f"  Name: {recommended_voice.get('name', 'N/A')}")
        else:
            print("[ERROR] No voices found. Check your API key and account permissions.")
    except Exception as e:
        print(f"[ERROR] Error fetching voices: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 80)
    print("CONFIGURATION INSTRUCTIONS")
    print("=" * 80)
    print("\nTo use specific avatar/voice, add to your .env file:")
    print("  HEYGEN_AVATAR_ID=your_avatar_id_here")
    print("  HEYGEN_VOICE_ID=your_voice_id_here")
    print("\nIf not configured, the system will automatically use the first available.")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(list_resources())

