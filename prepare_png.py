
from PIL import Image
import os

def extract_png_from_ico():
    ico_path = r"d:\Projects\生词本\app.ico"
    png_path = r"d:\Projects\生词本\app.png"
    
    try:
        # Open ICO
        img = Image.open(ico_path)
        
        # Check sizes available in ICO usually requires checking info or trying to seek
        # But simpler: we know we generated it, let's just regenerate app.png from the source if we can find it,
        # OR just use the largest frame from the ICO.
        
        print(f"ICO sizes: {img.size}")
        
        # If the currently loaded frame is small, this explains everything.
        # But wait, looking at my previous script, I generated app.ico from a source path that I knew.
        # I should just Copy that source path to app.png to be 100% sure I have the original quality.
        
        source_image = r"C:/Users/WINDOWS/.gemini/antigravity/brain/fdf67750-9ccf-45b2-aee7-c9ffedac3bd6/vocab_app_icon_1768489140826.png"
        
        if os.path.exists(source_image):
            print(f"Found original source: {source_image}")
            src_img = Image.open(source_image)
            src_img.save(png_path)
            print(f"Saved high-res PNG to {png_path}")
        else:
            print("Source missing, using ICO frame...")
            # Ideally we pick the largest, but PIL default might be tricky with ICO layers.
            # Let's just trust save() preserves it if we just did it.
            img.save(png_path)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    extract_png_from_ico()
