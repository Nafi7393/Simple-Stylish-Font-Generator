import os
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Cache for storing calculated font sizes
font_size_cache = {}


def create_unique_folder(base_path, folder_name):
    unique_folder_path = os.path.join(base_path, folder_name)
    counter = 1
    while os.path.exists(unique_folder_path):
        unique_folder_path = os.path.join(base_path, f"{folder_name}_{counter}")
        counter += 1
    os.makedirs(unique_folder_path)
    return unique_folder_path


def get_paths(folder_path, only_folder=False):
    paths = []
    for root, dirs, files in os.walk(folder_path):
        if only_folder:
            for directory in dirs:
                paths.append(os.path.join(root, directory))
        else:
            for file in files:
                paths.append(os.path.join(root, file))
    return paths


def get_details(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
        # Extract title and subtitle from the first line
        if len(lines) > 0:
            first_line = lines[0].strip()
            # Assuming title and subtitle are separated by ' - '
            if ' - ' in first_line:
                title, sub_title = map(str.strip, first_line.split(' - ', 1))

        # Extract keywords from the last non-empty line
        for line in reversed(lines):
            stripped_line = line.strip()
            if stripped_line:  # Check if the line is not empty
                keywords = stripped_line
                break

        return title, sub_title, keywords


def transform_image(image):
    # Define the possible rotations
    rotations = [0, 90, 180, 270]
    # Define the possible flips
    flips = ['none', 'left_right', 'top_bottom']

    # Randomly select a rotation
    rotation = random.choice(rotations)
    # Apply the rotation to the image
    image = image.rotate(rotation, expand=True)

    # Randomly select a flip
    flip = random.choice(flips)
    # Apply the flip to the image
    if flip == 'left_right':
        image = image.transpose(Image.FLIP_LEFT_RIGHT)
    elif flip == 'top_bottom':
        image = image.transpose(Image.FLIP_TOP_BOTTOM)

    return image


def get_max_font_size(font_path, image_width, image_height):
    cache_key = (font_path, image_width, image_height)
    if cache_key in font_size_cache:
        return font_size_cache[cache_key]

    font_size = 1
    draw = ImageDraw.Draw(Image.new('RGB', (image_width, image_height), 'white'))

    while True:
        font = ImageFont.truetype(font_path, font_size)
        text_bbox = draw.textbbox((0, 0), 'A', font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        if text_width > image_width or text_height > image_height:
            font_size -= 1
            break
        font_size += 1

    font_size_cache[cache_key] = font_size
    return font_size


def create_letter_image(letter, font_path, font_size):
    font = ImageFont.truetype(font_path, font_size)

    bbox = font.getbbox(letter)
    text_width = int(bbox[2] - bbox[0])
    text_height = int(bbox[3] - bbox[1])
    image = Image.new('RGBA', (text_width, text_height), (255, 255, 255, 0))

    draw = ImageDraw.Draw(image)
    draw.text((-bbox[0], -bbox[1]), letter, font=font, fill=(0, 0, 0, 255))

    return image


def create_image_with_letter(letter, font_path, font_size=None, padding=100,
                             image_width=1024, image_height=1024):
    image = Image.new('RGBA', (image_width, image_height), (0, 0, 0, 0))

    if font_size is None:
        font_size = get_max_font_size(font_path, image_width, image_height)

    letter_img = create_letter_image(letter=letter, font_path=font_path, font_size=font_size)
    letter_width, letter_height = letter_img.size

    max_letter_width = image_width - 2 * padding
    max_letter_height = image_height - 2 * padding
    if letter_width > max_letter_width or letter_height > max_letter_height:
        scale = min(max_letter_width / letter_width, max_letter_height / letter_height)
        new_size = (int(letter_width * scale), int(letter_height * scale))
        letter_img = letter_img.resize(new_size, Image.LANCZOS)
        letter_width, letter_height = new_size

    x = (image_width - letter_width) // 2
    y = (image_height - letter_height) // 2

    image.paste(letter_img, (x, y), letter_img)

    return image


def apply_mask(transparent_image, colorful_image_path):
    # Load the colorful image
    colorful_image = Image.open(colorful_image_path).convert("RGBA")

    # Ensure the colorful image and transparent image have the same size
    if colorful_image.size != transparent_image.size:
        colorful_image = colorful_image.resize(transparent_image.size, Image.LANCZOS)

    # Create a mask from the black pixels in the transparent image
    mask = Image.new("L", transparent_image.size, 0)
    for x in range(transparent_image.width):
        for y in range(transparent_image.height):
            if transparent_image.getpixel((x, y)) == (0, 0, 0, 255):
                mask.putpixel((x, y), 255)

    # Dilate the mask to cover thin lines
    mask = mask.filter(ImageFilter.MaxFilter(5))  # Increase size if necessary

    # Apply the mask to the colorful image
    result_image = Image.composite(colorful_image, transparent_image, mask)

    return result_image


def process_the_folder(path_folder, output_base_path="output"):
    all_letter = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    img_files = [file for file in get_paths(folder_path=path_folder, only_folder=False) if
                 file.lower().endswith(('.png', '.jpg', '.jpeg', ".webp"))]
    info_file_path = f"{path_folder}\\__INFO.txt"

    this_title, this_sub_title, this_keywords = get_details(file_path=info_file_path)

    # Create the main output folder
    main_output_folder = create_unique_folder(output_base_path, this_title)

    # Create subfolders inside the main output folder
    subfolders = {
        "0-9": os.path.join(main_output_folder, "0-9"),
        "a-z lower": os.path.join(main_output_folder, "a-z lower"),
        "A-Z UPPER": os.path.join(main_output_folder, "A-Zss UPPER")
    }
    for subfolder in subfolders.values():
        os.makedirs(subfolder, exist_ok=True)

    for let in all_letter:
        ran_mask = random.choice(img_files)
        l_img = create_image_with_letter(letter=let, font_path="font/Fresh Juice.ttf", font_size=None, padding=100,
                                         image_width=1024, image_height=1024)
        mask_img = apply_mask(l_img, ran_mask)

        # Determine the correct subfolder based on the letter
        if let.isdigit():
            subfolder_name = "0-9"
        elif let.islower():
            subfolder_name = "a-z lower"
        else:
            subfolder_name = "A-Z UPPER"

        # Save the masked image to the appropriate subfolder
        output_file = os.path.join(subfolders[subfolder_name], f"{let}.png")
        mask_img.save(output_file)


def main():
    folders = get_paths(folder_path="input", only_folder=True)
    for folder in folders:
        process_the_folder(path_folder=folder)


if __name__ == "__main__":
    #main()
    transform_image(Image.open("test.png").convert("RGBA")).show()
