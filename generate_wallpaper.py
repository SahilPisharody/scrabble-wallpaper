import json
import os
import random
import requests
from io import BytesIO
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# --- CONFIGURATION ---
# Retrieves key securely from environment variables set in GitHub Actions / Secrets
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY")
SEARCH_KEYWORDS = "misty forest, foggy mountains, moody nature, pine trees"

def fetch_online_background(access_key, query):
    """Fetches a random portrait nature image from Unsplash API."""
    if not access_key:
        raise ValueError("UNSPLASH_ACCESS_KEY environment variable is missing or empty.")

    url = "https://api.unsplash.com/photos/random"
    headers = {"Authorization": f"Client-ID {access_key}"}
    params = {
        "query": query,
        "orientation": "portrait",
        "content_filter": "high"
    }

    response = requests.get(url, headers=headers, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()
    
    # Download high-resolution image into memory
    image_url = data["urls"]["regular"]
    img_response = requests.get(image_url, timeout=15)
    img_response.raise_for_status()
    
    return Image.open(BytesIO(img_response.content))

def generate_scrabble_wallpaper():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    words_file = os.path.join(base_dir, 'words.json')
    output_path = os.path.join(base_dir, 'daily_wallpaper.jpg')

    # Load Word List
    with open(words_file, 'r') as f:
        words = json.load(f)

    # Rotate word based on Day of Year
    day_of_year = datetime.now().timetuple().tm_yday
    word_data = words[day_of_year % len(words)]

    # 1. Fetch live image from Unsplash (Fallback to dark background if request fails)
    try:
        print("Fetching background image from Unsplash...")
        img = fetch_online_background(UNSPLASH_ACCESS_KEY, SEARCH_KEYWORDS)
    except Exception as e:
        print(f"Failed to fetch Unsplash image ({e}). Using dark fallback background.")
        img = Image.new('RGB', (1080, 1920), color=(20, 32, 38))

    # Target resolution (Standard Smartphone 9:16 aspect ratio)
    target_width, target_height = 1080, 1920
    img = img.convert('RGB')

    # Aspect Fill Cropping
    img_ratio = img.width / img.height
    target_ratio = target_width / target_height

    if img_ratio > target_ratio:
        new_width = int(target_height * img_ratio)
        img = img.resize((new_width, target_height), Image.Resampling.LANCZOS)
        left = (new_width - target_width) // 2
        img = img.crop((left, 0, left + target_width, target_height))
    else:
        new_height = int(target_width / img_ratio)
        img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
        top = (new_height - target_height) // 2
        img = img.crop((0, top, target_width, top + target_height))

    # Dark misty vignette overlay behind text
    overlay = Image.new('RGBA', (target_width, target_height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    
    overlay_draw.rectangle(
        [(0, int(target_height * 0.35)), (target_width, int(target_height * 0.75))],
        fill=(10, 20, 25, 150)
    )
    overlay = overlay.filter(ImageFilter.GaussianBlur(40))
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')

    # Prepare Canvas & Fonts
    draw = ImageDraw.Draw(img)

    # Cross-platform font fallback handling
    try:
        font_word = ImageFont.truetype("DejaVuSans.ttf", 85)
        font_points = ImageFont.truetype("DejaVuSans.ttf", 34)
        font_def = ImageFont.truetype("DejaVuSans.ttf", 30)
        font_tip = ImageFont.truetype("DejaVuSans-Oblique.ttf", 26)
    except IOError:
        try:
            font_word = ImageFont.truetype("georgia.ttf", 85)
            font_points = ImageFont.truetype("georgia.ttf", 34)
            font_def = ImageFont.truetype("arial.ttf", 30)
            font_tip = ImageFont.truetype("ariali.ttf", 26)
        except IOError:
            # Universal fallback if TrueType fonts are missing on the Linux environment
            font_word = font_points = font_def = font_tip = ImageFont.load_default()

    # Draw Typography
    center_y = int(target_height * 0.48)
    word_text = word_data["word"]
    points_text = f" [{word_data['points']} pts]"
    
    draw.text((target_width // 2, center_y), word_text, fill=(255, 255, 255), font=font_word, anchor="mm")
    draw.text((target_width // 2, center_y + 70), points_text, fill=(210, 225, 210), font=font_points, anchor="mm")

    # Divider line
    draw.line(
        [(target_width // 2 - 120, center_y + 110), (target_width // 2 + 120, center_y + 110)],
        fill=(255, 255, 255, 180), width=2
    )

    # Text wrapping utility function
    def draw_wrapped_text(text, font, y_start, max_width=800, fill=(240, 240, 240)):
        words_list = text.split()
        lines = []
        current_line = []
        
        for w in words_list:
            current_line.append(w)
            test_line = ' '.join(current_line)
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] > max_width:
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [w]
        lines.append(' '.join(current_line))

        current_y = y_start
        for line in lines:
            draw.text((target_width // 2, current_y), line, fill=fill, font=font, anchor="mm")
            current_y += 42
        return current_y

    # Draw Definition & Scrabble Tip
    next_y = draw_wrapped_text(f"“{word_data['definition']}”", font_def, center_y + 160)
    draw_wrapped_text(f"Scrabble Tip: {word_data['scrabble_tip']}", font_tip, next_y + 10, fill=(180, 205, 190))

    # Save output image
    img.save(output_path, quality=95)
    print(f"Successfully generated wallpaper to: {output_path}")

if __name__ == "__main__":
    generate_scrabble_wallpaper()
