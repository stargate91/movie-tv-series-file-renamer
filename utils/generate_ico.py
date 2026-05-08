import os
from PIL import Image

def generate_ico(source_dir, output_file):
    """
    Combines multiple PNGs into a single ICO file with multiple sizes.
    Expects 16x16.png, 32x32.png, and 96x96.png in the source_dir.
    """
    img_96 = Image.open(os.path.join(source_dir, "96x96.png"))
    img_32 = Image.open(os.path.join(source_dir, "32x32.png"))
    img_16 = Image.open(os.path.join(source_dir, "16x16.png"))
    
    # ICO can contain multiple sizes for better OS scaling
    img_96.save(output_file, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (96, 96), (128, 128), (256, 256)])
    print(f"ICO generated successfully at: {output_file}")

if __name__ == "__main__":
    # Get the project root directory
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    favicon_dir = os.path.join(root, "favicon")
    output_path = os.path.join(root, "favicon.ico")
    
    if os.path.exists(favicon_dir):
        try:
            generate_ico(favicon_dir, output_path)
        except Exception as e:
            print(f"Error generating ICO: {e}")
    else:
        print(f"Favicon directory not found at {favicon_dir}")
