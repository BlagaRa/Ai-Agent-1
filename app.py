import os
import pygame
import requests
import speech_recognition as sr
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Initialize pygame mixer
pygame.mixer.init()

# Load environment variables
load_dotenv()

ELEVEN_LABS_API_KEY = os.getenv('ELEVEN_LABS_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
VOICE_ID = "nPczCjzI2devNBz1zQrb"  # Your ElevenLabs Voice ID

if not ELEVEN_LABS_API_KEY:
    raise ValueError("ELEVEN_LABS_API_KEY environment variable not set.")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set.")

ELEVEN_LABS_API_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"

def generate_speech(text):
    headers = {
        "xi-api-key": ELEVEN_LABS_API_KEY,
        "Content-Type": "application/json"
    }
    data = {"text": text, "model_id": "eleven_monolingual_v1"}

    response = requests.post(ELEVEN_LABS_API_URL, json=data, headers=headers)
    if response.status_code == 200:
        try:
            with open("response_audio.mp3", "wb") as audio_file:
                audio_file.write(response.content)
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
            pygame.mixer.music.load("response_audio.mp3")
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
        except Exception as e:
            print("Error during audio playback:", e)
            try:
                pygame.mixer.quit()
                pygame.mixer.init()
            except Exception as e2:
                print("Error resetting pygame mixer:", e2)
    else:
        try:
            print("Error in voice generation:", response.json())
        except Exception:
            print("Error in voice generation:", response.content)

def select_microphone(force_index=None):
    mic_list = sr.Microphone.list_microphone_names()
    print("\nDetected microphones:")
    for i, name in enumerate(mic_list):
        print(f"  [{i}] {name}")

    # If FORCE_MIC_INDEX is set, use it
    if force_index is not None:
        print(f"\nUsing forced microphone index: {force_index} ({mic_list[force_index]})")
        return force_index

    while True:
        idx = int(input("Enter the device index of your headphones microphone: "))
        try:
            with sr.Microphone(device_index=idx) as test_mic:
                print(f"Using microphone: {mic_list[idx]}")
                return idx
        except Exception as e:
            print(f"Device {idx} not usable ({e}), try another.")

def recognize_speech(mic_index):
    recognizer = sr.Recognizer()
    mic = sr.Microphone(device_index=mic_index)
    print("\nPress Enter and speak your message...")
    input("(Ready) ")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        print("Listening...")
        audio = recognizer.listen(source)
    try:
        text = recognizer.recognize_google(audio)
        print(f"You (recognized): {text}")
        return text
    except sr.UnknownValueError:
        print("Sorry, could not understand audio.")
        return ""
    except sr.RequestError as e:
        print(f"Could not request results from speech recognition service; {e}")
        return ""

def chat_with_gemini_voice():
    client = genai.Client(api_key=GEMINI_API_KEY)
    model = "gemini-2.0-flash"
    conversation_history = [
        types.Content(
            role="user",
            parts=[types.Part(
                text=(
                    "You are a friendly and polite assistant. "
                    "Always answer clearly and directly, saying exactly what needs to be heard. "
                    "Avoid introductory phrases like 'I will do that.' "
                    "My name is Razvan, my girlfriend's name is Alessia, and our cat is Samir. "
                    "Use our names as appropriate and tailor your responses with this knowledge."
                )
            )],
        )
    ]
    print("\nStart voice chatting with Gemini! (Press Enter and speak. Say 'exit' to quit)")

    # Set this to your headphones mic index if you know it (otherwise, None for prompt)
    FORCE_MIC_INDEX = None  # e.g., 1, 5, etc.
    mic_index = select_microphone(force_index=FORCE_MIC_INDEX)

    while True:
        user_input = recognize_speech(mic_index)
        if not user_input:
            continue
        if user_input.lower() in ["exit", "quit", "bye"]:
            print("Ending the conversation. Goodbye!")
            break

        conversation_history.append(
            types.Content(
                role="user",
                parts=[types.Part(text=user_input)],
            )
        )

        generate_content_config = types.GenerateContentConfig(
            response_mime_type="text/plain",
        )
        response = client.models.generate_content_stream(
            model=model,
            contents=conversation_history,
            config=generate_content_config,
        )

        # Collect full reply
        full_reply = ''
        for chunk in response:
            if chunk.text:
                full_reply += chunk.text

        if full_reply:
            reply = full_reply.strip()
            print(f"Gemini: {reply}")
            conversation_history.append(
                types.Content(
                    role="assistant",
                    parts=[types.Part(text=reply)],
                )
            )
            generate_speech(reply)

if __name__ == "__main__":
    chat_with_gemini_voice()