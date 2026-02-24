
import cv2
import os

def draw_grid(image_path, output_path):
    if not os.path.exists(image_path):
        print(f"Image not found: {image_path}")
        return

    img = cv2.imread(image_path)
    if img is None:
        print("Could not read image")
        return

    h, w = img.shape[:2]
    step = 100
    color = (0, 0, 255) # Red
    thickness = 2
    
    # Draw Grid
    for x in range(0, w, step):
        cv2.line(img, (x, 0), (x, h), color, 1)
        cv2.putText(img, str(x), (x + 5, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
    for y in range(0, h, step):
        cv2.line(img, (0, y), (w, y), color, 1)
        cv2.putText(img, str(y), (5, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    cv2.imwrite(output_path, img)
    print(f"Grid image saved to {output_path}")

if __name__ == "__main__":
    # Pick the first image in 'images' folder
    img_dir = "images"
    if os.path.exists(img_dir):
        files = [f for f in os.listdir(img_dir) if f.lower().endswith('.jpg')]
        if files:
            target = os.path.join(img_dir, files[0])
            draw_grid(target, "coordinate_guide.jpg")
        else:
            print("No images found in images/")
    else:
        print("images/ directory not found")
