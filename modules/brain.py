import os
import json
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from google import genai
from dotenv import load_dotenv
from config import MODEL_CONFIG, VIDEO_CONFIG
import time

load_dotenv()


class ContentBrain:
    def __init__(
        self,
        api_key: str,
        model_name: str | None = None,
        topic_prompt: str | None = None,
        script_extra_instructions: str = "",
    ):
        if not (api_key or "").strip():
            raise ValueError("Gemini API key is required.")
        self.client = genai.Client(api_key=api_key.strip())
        self.model_name = (model_name or "").strip() or MODEL_CONFIG["models"][0]["name"]
        self.topic_prompt = (topic_prompt or "").strip()
        self.script_extra_instructions = (script_extra_instructions or "").strip()

    def _generate(self, contents, max_retries: int = 4):
        model = self.model_name
        delay = MODEL_CONFIG["retry_delay_seconds"]
        last_err = None
        for attempt in range(max_retries):
            try:
                return self.client.models.generate_content(model=model, contents=contents)
            except Exception as e:
                last_err = e
                err = str(e)
                if ("429" in err or "RESOURCE_EXHAUSTED" in err) and attempt < max_retries - 1:
                    print(f"⚠️ Model {model} quota/rate limit — đợi {delay}s (lần {attempt + 1}/{max_retries})...")
                    time.sleep(delay)
                    continue
                raise
        if last_err:
            raise last_err
        raise RuntimeError("generate_content failed")

    def get_trending_topic(self):
        """
        Gemini chọn 1 topic viral theo prompt cấu hình.
        """
        if not self.topic_prompt:
            raise ValueError("topic_prompt trống — hãy cấu hình trong UI hoặc settings.")
        response = self._generate(contents=self.topic_prompt)
        topic = response.text.strip()
        print(f"🎯 Selected Topic: {topic}")
        return topic

    def generate_script(self, topic):
        """
        Generates a structured JSON script with visual cues.
        """
        mode = VIDEO_CONFIG["mode"]
        if mode == "long":
            min_scenes = VIDEO_CONFIG["long_mode"]["min_scenes"]
            max_scenes = VIDEO_CONFIG["long_mode"]["max_scenes"]
            words_per_scene = VIDEO_CONFIG["long_mode"]["words_per_scene"]
        else:
            min_scenes = VIDEO_CONFIG["short_mode"]["min_scenes"]
            max_scenes = VIDEO_CONFIG["short_mode"]["max_scenes"]
            words_per_scene = VIDEO_CONFIG["short_mode"]["words_per_scene"]

        mode_label = "LONG FORM" if mode == "long" else "SHORT FORM"

        print(f"📝 Writing script for: {topic} ({mode_label} - {min_scenes}-{max_scenes} scenes)...")

        extra_block = ""
        if self.script_extra_instructions:
            extra_block = f"""
    ### USER ADDITIONAL INSTRUCTIONS:
    {self.script_extra_instructions}

    """

        prompt = f"""
    You are the lead scriptwriter for a high-retention "Edutainment" YouTube Shorts channel.
    Topic: {topic}

    ### GOAL:
    Create a script where every sentence has a "Visual Switch". 
    To keep retention high, we need TWO different stock videos for every single scene.

    ### 1. SCRIPT REQUIREMENTS (The Voiceover):
    - **Perspective:** Strictly **3rd Person** ("Scientists found...", "The ocean hides...").
    - **Tone:** Engaging, fast-paced, logical. No fluff.
    - **Structure:** {min_scenes}-{max_scenes} Scenes total.
    - **Sentence Length:** {words_per_scene} words per scene.
    - **Flow:** Hook -> Context -> Mechanism (How it works) -> Twist -> Outro.

    ### 2. VISUAL REQUIREMENTS (Dual Visuals):
    - For EVERY scene, provide TWO distinct search terms:
      - **visual_1:** Matches the *start* of the sentence.
      - **visual_2:** Matches the *end* of the sentence or provides a reaction/context.
    - **Strictly Literal:** If the text is "The economy crashed," do NOT search "sad man". Search "Stock market red chart".
{extra_block}
    ### OUTPUT FORMAT (Strict JSON):
    [
        {{
            "id": 1,
            "text": "In 1995, fourteen wolves were released into Yellowstone Park, and they changed the rivers.",
            "visual_1": "wolves running snow aerial",
            "visual_2": "river flowing forest drone",
            "mood": "intriguing" 
        }},
        {{
            "id": 2,
            "text": "It sounds impossible, but the biology is actually simple math.",
            "visual_1": "person shocked looking at camera",
            "visual_2": "blackboard math equations chalk",
            "mood": "educational"
        }}
    ]
    """

        response = self._generate(contents=prompt)

        clean_text = response.text.replace("```json", "").replace("```", "").strip()

        try:
            script_data = json.loads(clean_text)
            return script_data
        except json.JSONDecodeError:
            print("❌ Error parsing JSON. Raw output:")
            print(clean_text)
            return None


if __name__ == "__main__":
    from settings_store import load_settings, effective_gemini_model, DEFAULT_TOPIC_PROMPT

    s = load_settings()
    brain = ContentBrain(
        api_key=s["gemini_api_key"],
        model_name=effective_gemini_model(s),
        topic_prompt=s.get("topic_prompt") or DEFAULT_TOPIC_PROMPT,
        script_extra_instructions=s.get("script_extra_instructions", ""),
    )
    topic = brain.get_trending_topic()
    script = brain.generate_script(topic)

    with open("script.json", "w") as f:
        json.dump(script, f, indent=4)
        print("✅ Script saved to script.json")
