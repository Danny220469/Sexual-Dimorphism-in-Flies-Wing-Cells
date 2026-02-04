import os
import cv2
import numpy as np
import torch
from segment_anything import sam_model_registry, SamPredictor
import tkinter as tk
from tkinter import filedialog

# --- 📁 CONFIGURE YOUR MODEL PATH HERE ---
MODEL_TYPE = "vit_b"
CHECKPOINT_PATH = "sam_vit_b_01ec64.pth"

# Global variables for the mouse callback
click_points = []
click_labels = []
display_image = None
base_image = None

def select_input_file():
    """Opens a file explorer dialog to select the input image."""
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select an Image to Segment",
        filetypes=[("Image files", "*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp")]
    )
    return file_path

def select_save_directory():
    """Opens a dialog to choose the destination folder."""
    root = tk.Tk()
    root.withdraw()
    folder_selected = filedialog.askdirectory(title="Select Folder to Save Mask")
    return folder_selected

def mouse_callback(event, x, y, flags, param):
    """Handles mouse clicks for selecting points."""
    global click_points, click_labels, display_image

    if event == cv2.EVENT_LBUTTONDOWN:  # Left Click = Positive (Green)
        click_points.append([x, y])
        click_labels.append(1)
        cv2.circle(display_image, (x, y), 5, (0, 255, 0), -1) 
        cv2.imshow("Single Image Segmenter", display_image)

    elif event == cv2.EVENT_RBUTTONDOWN: # Right Click = Negative (Red)
        click_points.append([x, y])
        click_labels.append(0)
        cv2.circle(display_image, (x, y), 5, (0, 0, 255), -1)
        cv2.imshow("Single Image Segmenter", display_image)

def process_single_image():
    global display_image, base_image, click_points, click_labels

    print("--- Single Image SAM Segmenter ---")

    # 1. Select Input File
    image_path = select_input_file()
    if not image_path:
        print("No file selected. Exiting.")
        return

    # 2. Load Model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading SAM model on: {device}...")
    try:
        sam = sam_model_registry[MODEL_TYPE](checkpoint=CHECKPOINT_PATH)
        sam.to(device=device)
        predictor = SamPredictor(sam)
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    # 3. Load Image
    image = cv2.imread(image_path)
    if image is None:
        print("Could not load image.")
        return

    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    predictor.set_image(image_rgb)
    base_image = image.copy()
    display_image = image.copy()

    # 4. Interactive UI
    cv2.namedWindow("Single Image Segmenter")
    cv2.setMouseCallback("Single Image Segmenter", mouse_callback)

    print("\n--- 🖱️ CONTROLS ---")
    print("Left Click  : Add Positive Point (Green)")
    print("Right Click : Add Negative Point (Red)")
    print("SPACE       : Preview Mask")
    print("R           : Reset Points")
    print("ENTER       : Confirm and CHOOSE SAVE FOLDER")
    print("Q           : Quit")

    preview_mask = None

    while True:
        if preview_mask is not None:
            overlay = display_image.copy()
            overlay[preview_mask > 0] = [0, 0, 255] 
            combined = cv2.addWeighted(overlay, 0.5, display_image, 0.5, 0)
            cv2.imshow("Single Image Segmenter", combined)
        else:
            cv2.imshow("Single Image Segmenter", display_image)

        key = cv2.waitKey(1) & 0xFF

        if key == 32: # SPACE: Preview
            if not click_points: continue
            pts, lbls = np.array(click_points), np.array(click_labels)
            masks, _, _ = predictor.predict(point_coords=pts, point_labels=lbls, multimask_output=False)
            preview_mask = masks[0]

        elif key == ord('r'): # Reset
            click_points, click_labels = [], []
            display_image = base_image.copy()
            preview_mask = None

        elif key == 13: # ENTER: Save
            if not click_points:
                print("⚠️ Select points first.")
                continue
            
            # Final prediction
            pts, lbls = np.array(click_points), np.array(click_labels)
            masks, _, _ = predictor.predict(point_coords=pts, point_labels=lbls, multimask_output=False)
            binary_mask = (masks[0] > 0).astype(np.uint8) * 255
            
            # 5. Choose Save Folder
            dest_folder = select_save_directory()
            if dest_folder:
                # Get the original filename and combine with the new path
                original_filename = os.path.basename(image_path)
                name_only = os.path.splitext(original_filename)[0]
                save_path = os.path.join(dest_folder, f"{name_only}_mask.png")
                
                cv2.imwrite(save_path, binary_mask)
                print(f"✅ Saved to: {save_path}")
            else:
                print("Save cancelled (no folder selected).")
            break

        elif key == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    process_single_image()