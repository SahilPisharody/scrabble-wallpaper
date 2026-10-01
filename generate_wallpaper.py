import os
import random
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from datetime import datetime, timedelta
import json

def get_scrabble_word():
    # Load custom words list
    with open('words.json', 'r') as f:
        words = json.load(f)
    
    # Calculate word index based on target upcoming hour (+10 minutes buffer)
    target_time = datetime.now() + timedelta(minutes=10)
    hourly_index = int(target_time.timestamp() // 3600)
    return words[hourly_index % len(words)]

def fetch_unsplash_image():
    access_key = os.environ.get("UNSPLASH_ACCESS_KEY")
    url = f"https://api.unsplash.com/photos/random?query=foggy,misty,nature,moody&orientation=portrait&client_id={access_key}"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    image_url = data['urls']['regular']
    img_data = requests.get(image_url).content
    with open('temp_bg.jpg', 'wb') as handler:
        handler.write(img_data)
    return 'temp_bg.jpg'

def generate_wallpaper():
    word_info = get_scrabble_word()
    bg_path = fetch_unsplash_image()
    
    img = Image.open(bg_path)
    
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
        [(0, int(target_height * 0.60)), (target_width, int(target_height * 0.90))],
        fill=(10, 20, 25, 160)
    )
    overlay = overlay.filter(ImageFilter.GaussianBlur(40))
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')

    # Prepare Canvas & Fonts
    draw = ImageDraw.Draw(img)

    try:
        font_word = ImageFont.truetype("DejaVuSans.ttf", 62)
        font_points = ImageFont.truetype("DejaVuSans.ttf", 26)
        font_def = ImageFont.truetype("DejaVuSans.ttf", 24)
    except IOError:
        try:
            font_word = ImageFont.truetype("georgia.ttf", 62)
            font_points = ImageFont.truetype("georgia.ttf", 26)
            font_def = ImageFont.truetype("arial.ttf", 24)
        except IOError:
            font_word = font_points = font_def = ImageFont.load_default()

    # Draw Text Elements (Positioned right below Spotify player)
    start_y = int(target_height * 0.62)
    
    word_text = word_info['word'].upper()
    points_text = f"({word_info.get('points', 0)} pts)"
    def_text = word_info['definition']

    # Draw Word & Points
    draw.text((80, start_y), word_text, font=font_word, fill=(255, 255, 255))
    draw.text((80, start_y + 70), points_text, font=font_points, fill=(200, 220, 210))

    # Wrap Definition (Restricted to 420px max width so it stays on left side of fingerprint icon)
    max_width = 420
    lines = []
    words = def_text.split()
    current_line = ""

    for w in words:
        test_line = f"{current_line} {w}".strip()
        bbox = font_def.getbbox(test_line)
        line_w = bbox[2] - bbox[0]
        if line_w <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = w
    if current_line:
        lines.append(current_line)

    def_y = start_y + 110
    for line in lines:
        draw.text((80, def_y), line, font=font_def, fill=(220, 220, 220))
        def_y += 32

    # Save final output image
    img.save('daily_wallpaper.jpg', 'JPEG', quality=95)
    
    # Cleanup temporary download file
    if os.path.exists('temp_bg.jpg'):
        os.remove('temp_bg.jpg')

if __name__ == "__main__":
    generate_wallpaper()
