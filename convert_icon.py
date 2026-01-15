
from PIL import Image
import os

# Update to use the local app.png as source which should now be the transparent one
source_image = r"d:\Projects\生词本\app.png"
dest_ico = r"d:\Projects\生词本\app.ico"

def convert_png_to_high_quality_ico(png_path, ico_path):
    try:
        print(f"Opening {png_path}...")
        img = Image.open(png_path) # Now using the local app.png
        
        # Ensure RGBA
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
            
        icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
        
        print(f"Saving high-quality ICO to {ico_path}...")
        img.save(ico_path, format='ICO', sizes=icon_sizes)
        print(f"Successfully converted to {ico_path}")
        
    except Exception as e:
        print(f"Error converting image: {e}")

if __name__ == "__main__":
    if os.path.exists(source_image):
        convert_png_to_high_quality_ico(source_image, dest_ico)
    else:
        print(f"Source image not found at {source_image}")
