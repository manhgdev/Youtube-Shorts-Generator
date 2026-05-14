# AI Model Configuration - Ordered by priority (first = preferred)
MODEL_CONFIG = {
    "models": [
        {"name": "gemini-3.1-flash-lite", "rpd": 500},    # Best quota
        {"name": "gemini-2.5-flash", "rpd": 20},           # Good quality
        {"name": "gemini-2.5-flash-lite", "rpd": 20},     # Lightweight
    ],
    "current_model_index": 0,  # Start with first model
    "retry_delay_seconds": 60,  # Wait time after 429 error
}


def gemini_model_presets():
    """Danh sách model mặc định cho UI / combobox."""
    return [m["name"] for m in MODEL_CONFIG["models"]]


# Video Duration Configuration
VIDEO_CONFIG = {
    # "short" = ~40-50 seconds (8-9 scenes)
    # "long" = ~60-90 seconds (15-20 scenes)
    "mode": "short",  # Change to "long" for videos > 1 minute
    
    # Scene settings based on mode
    "short_mode": {
        "min_scenes": 8,
        "max_scenes": 9,
        "target_duration": 45,  # seconds
        "words_per_scene": "10-15",
    },
    
    "long_mode": {
        "min_scenes": 10,
        "max_scenes": 12,
        "target_duration": 60,  # seconds
        "words_per_scene": "15-20",
    },
    
    # Audio settings
    "voice": "en-US-AvaNeural",
    "speech_rate": "+10%",  # Use "+0%" or "-5%" for slower/longer audio
    
    # Video settings
    "resolution": (1080, 1920),  # 9:16 Shorts format
    "fps": 30,
}
