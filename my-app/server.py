from flask import Flask, request, jsonify
from langchain_community.llms import Ollama
from flask_cors import CORS
import google.generativeai as genai
import re
from PIL import Image
import base64
from io import BytesIO
import time
import requests
import io
from huggingface_hub import InferenceClient
import os
import shutil

app = Flask(__name__)
CORS(app)

client = InferenceClient("stabilityai/stable-diffusion-xl-base-1.0", token="")
genai.configure(api_key="")
model = genai.GenerativeModel("gemini-2.5-flash")


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    return response


# ============ STORYTELLER CORE LOGIC (AGE-BASED) ============

def storyTeller(input_text, age=10):
    # Get age-appropriate story instructions
    story_instructions = get_age_appropriate_story_instructions(age)

    response = model.generate_content(
        f"{story_instructions}\n\nTell a story in exactly 4 paragraphs based on the given context: {input_text}"
    )

    ImageGen(response.text)  # Uncomment if you want to generate images automatically
    return response.text


# Helper function to provide age-appropriate story instructions
def get_age_appropriate_story_instructions(age):
    age = int(age)

    if age < 7:
        return """
        Create a story for young children (under 7 years):
        - Use very simple words and short sentences
        - Include repetitive phrases and predictable patterns
        - Focus on basic emotions and clear moral lessons
        - Use lots of action words and sound effects
        - Keep the story fun, colorful, and easy to follow
        - Include friendly characters and happy endings
        - Vocabulary should be at preschool/kindergarten level
        - Make it engaging with simple adventures
        """
    elif age >= 7 and age < 13:
        return """
        Create a story for children aged 7-12 years:
        - Use age-appropriate vocabulary with some challenging words
        - Include more detailed descriptions and character development
        - Create a clear plot with beginning, middle, and end
        - Add some mild conflict or problem-solving elements
        - Include themes like friendship, courage, teamwork, or learning
        - Make characters relatable with realistic emotions
        - Keep the story engaging with some suspense or excitement
        - End with a satisfying resolution and positive message
        """
    elif age >= 13 and age <= 20:
        return """
        Create a story for teenagers aged 13-20 years:
        - Use sophisticated vocabulary and varied sentence structures
        - Develop complex characters with deeper motivations
        - Include nuanced themes like identity, relationships, or personal growth
        - Create compelling conflicts with realistic resolutions
        - Add layers of meaning and subtle symbolism
        - Balance action with emotional depth and introspection
        - Make the story thought-provoking while still entertaining
        - Address age-appropriate challenges and life lessons
        """
    else:
        return """
        Create a story for adults (20+ years):
        - Use advanced literary language and sophisticated prose
        - Develop multi-dimensional characters with psychological depth
        - Explore complex themes such as ambition, morality, love, loss, or existential questions
        - Create intricate plots with subtle foreshadowing and symbolism
        - Include moral ambiguity and nuanced perspectives
        - Use literary devices like metaphor, irony, and subtext
        - Balance narrative with philosophical or emotional resonance
        - Craft an ending that is meaningful and thought-provoking, not necessarily happy
        - Make the story intellectually and emotionally engaging
        """


# ============ QUIZBOT CORE LOGIC (AGE-BASED) ============

def quizBot(input_text, age=10):
    # Get age-appropriate quiz instructions
    age_instructions = get_age_appropriate_quiz_instructions(age)

    text = f"""
    Generate 10 multiple-choice questions based on the provided story. For each question, include:
    1. The question text.
    2. Four options (labeled a, b, c, d).
    3. skip 2 lines before starting the next question.

    {age_instructions}

    Use this exact format for the response:
    Question 1: [Your question here]
    a) [Option 1]
    b) [Option 2]
    c) [Option 3]
    d) [Option 4]
    Correct Answer: [Letter of the correct answer]

    Repeat for all 10 questions.
    """

    response = model.generate_content(
        f"in the following format: {text} \n Frame 10 questions and give 4 options with one correct answer on the following story: {input_text}"
    )

    print(response.text)
    quiz_data = parse_quiz_response(response.text)
    print(quiz_data)

    return quiz_data


def get_age_appropriate_quiz_instructions(age):
    age = int(age)

    if age < 7:
        return """
        Age Group: Under 7 years (Young Children)
        - Use very simple vocabulary and short sentences
        - Focus on basic concepts like colors, numbers, characters, and main events
        - Questions should be about obvious and direct details from the story
        - Keep language playful and easy to understand
        - Avoid complex reasoning or abstract concepts
        - Example: "What color was the ball?" or "Who was the main character?"
        """
    elif age >= 7 and age < 13:
        return """
        Age Group: 7-12 years (Elementary to Middle School)
        - Use age-appropriate vocabulary with moderate complexity
        - Include questions about sequence of events, cause and effect, and character feelings
        - Test understanding of story structure and character motivations
        - Mix direct recall questions with some basic inference questions
        - Use clear language but introduce some analytical thinking
        - Example: "Why did the character make that choice?" or "What happened after the big event?"
        """
    elif age >= 13 and age <= 20:
        return """
        Age Group: 13-20 years (Teenagers)
        - Use more sophisticated vocabulary and complex concepts
        - Focus on themes, character development, symbolism, and deeper meanings
        - Test critical thinking, analysis, and interpretation skills
        - Include questions about literary devices and author's purpose
        - Challenge students to think beyond surface-level details
        - Example: "What theme does this story explore?" or "How does the setting influence the plot?"
        """
    else:
        return """
        Age Group: 20+ years (Adults - DIFFICULT LEVEL)
        - Use advanced and sophisticated vocabulary
        - Create challenging questions that require deep analysis and critical thinking
        - Focus on complex themes, subtext, narrative techniques, and philosophical implications
        - Test advanced comprehension including irony, paradox, ambiguity, and nuanced interpretation
        - Include questions about contextual analysis, intertextuality, and comparative literature
        - Challenge with questions that have subtle distinctions between answer choices
        - Require synthesis of multiple story elements and abstract reasoning
        """


def parse_quiz_response(response):
    questions = re.split(r"(?=Question \d+:)", response.strip())
    parsed_questions = []

    for question in questions:
        lines = question.strip().split("\n")

        if len(lines) >= 6:
            question_text = re.sub(r"^Question \d+:\s*", "", lines[0]).strip()
            options = [line.strip() for line in lines[1:5]]
            correct_answer = lines[5].replace("Correct Answer: ", "").strip()

            parsed_questions.append({
                "question": question_text,
                "options": options,
                "correctAnswer": correct_answer
            })

    return parsed_questions


# ============ IMAGE GENERATION ============


def ImageGen(text):
    images_folder = "public/Images"
    public_folder = "public"

    # --- Step 1: Empty the public/Images folder before generating ---
    if os.path.exists(images_folder):
        shutil.rmtree(images_folder)
    os.makedirs(images_folder, exist_ok=True)

    ParaList = text.split("\n\n")

    # --- Step 2: Generate images for each paragraph except the last ---
    for i in range(len(ParaList) - 1):
        PromptImage = model.generate_content(
            f"Generate a scenario-based prompt no more than 20 words to generate an image based on the following context: {ParaList[i]}"
        )
        print(f"🖼️ Prompt {i+1}: {PromptImage.text}")

        try:
            image = client.text_to_image(PromptImage.text)
            image.save(f"{images_folder}/Image{i + 1}.png")
        except Exception as e:
            print(f"❌ Error generating Image{i+1}: {e}")

    # --- Step 3: Use the Stable Diffusion XL model via the new endpoint ---
    try:
        client_1 = InferenceClient(
            "stabilityai/stable-diffusion-xl-base-1.0",
            token=""
        )

        PromptImage = model.generate_content(
            f"Generate a scenario-based very short prompt to generate an image based on the following context: {ParaList[3]}"
        )
        print(f"🖼️ Final Prompt: {PromptImage.text}")

        image = client_1.text_to_image(PromptImage.text)
        image.save(f"{public_folder}/Image4.png")

    except Exception as e:
        print(f"❌ Error generating final image: {e}")


    print("✅ All images generated successfully and saved in /public.")


# ============ FLASK ROUTES ============

@app.route("/StoryTeller", methods=["POST"])
def story_teller_route():
    input_data = request.get_json()
    input_text = input_data.get("text", "")
    age = input_data.get("age", 10)
    response = storyTeller(input_text, age)
    return jsonify({"response": response})


@app.route("/QuizBot", methods=["POST"])
def quiz_bot_route():
    input_data = request.get_json()
    input_text = input_data.get("text", "")
    age = input_data.get("age", 10)
    response = quizBot(input_text, age)
    return jsonify({"response": response})


@app.route("/LearnBot", methods=["POST"])
def learnBot():
    input_data = request.get_json()
    input_text = input_data.get("text", "")
    image_base64 = input_data.get("image", "")

    image = None
    if image_base64:
        try:
            if image_base64.startswith("data:image"):
                image_base64 = image_base64.split(",")[1]
            image_data = base64.b64decode(image_base64)
            image = Image.open(BytesIO(image_data))
        except Exception as e:
            print("Error decoding or verifying image:", e)
            return jsonify({"error": "Invalid image data"}), 400

    try:
        if image and input_text:
            prompt = f"You are an Ai Agent; correct user's mistakes if wrong, respond kindly: {input_text}"
            response = model.generate_content([prompt, image])
        elif image:
            prompt = "You are an Ai Agent; correct user's text in the image if wrong, respond kindly."
            response = model.generate_content([prompt, image])
        elif input_text:
            prompt = f"You are an Ai Agent; correct user's text if wrong, respond kindly: {input_text}"
            response = model.generate_content(prompt)
        else:
            return jsonify({"error": "No valid input provided"}), 400

        return jsonify({"response": response.text})
    except Exception as e:
        print("Error generating response:", e)
        return jsonify({"error": "Failed to generate response"}), 500


@app.route("/AiSuggestionBot", methods=["GET"])
def aiSuggestionBot():
    text = """
    Language Development: Language Development suggestion,
    Physical Development: Physical Development suggestion,
    Cognitive Skills: Cognitive Skills suggestion,
    Communication Skills: Communication Skills suggestion,
    """
    response = model.generate_content(
        f"Give 4 brief suggestions for parents on how to improve their child's development: {text}"
    )
    return jsonify({"response": response.text})


def get_downloads_folder():
    home = os.path.expanduser("~")
    downloads_folder = os.path.join(home, "Downloads")
    return downloads_folder


@app.route("/VideoAnalyzer", methods=["GET"])
def videoAnalyzer():
    downloads_path = get_downloads_folder()
    file_name = "Video.mp4"
    video_file_name = os.path.join(downloads_path, file_name)

    print(f"Checking for file {file_name} in Downloads folder...")
    while not os.path.exists(video_file_name):
        print(f"Waiting for {file_name} to be available...")
        time.sleep(5)

    print(f"File {file_name} found. Uploading...")
    video_file = genai.upload_file(path=video_file_name)
    print(f"Completed upload: {video_file.uri}")

    while video_file.state.name == "PROCESSING":
        print('Waiting for video to be processed.')
        time.sleep(10)
        video_file = genai.get_file(video_file.name)

    if video_file.state.name == "FAILED":
        raise ValueError(video_file.state.name)

    print(f'Video processing complete: {video_file.uri}')
    prompt = "Pretend like you're talking to the person in the video"
    model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")

    response = model.generate_content([prompt, video_file], request_options={"timeout": 600})
    print(response.text)
    os.remove(video_file_name)

    return jsonify({"response": response.text})


if __name__ == "__main__":
    app.run(debug=True)
