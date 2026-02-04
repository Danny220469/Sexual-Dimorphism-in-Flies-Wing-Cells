import os
import cv2
import numpy as np
import torch
from segment_anything import sam_model_registry, SamPredictor
import time
import tkinter as tk
from tkinter import filedialog

# --- SAM Model Configuration ---
MODEL_TYPE = "vit_b"
CHECKPOINT_PATH = "sam_vit_b_01ec64.pth"

# Global variables for the mouse callback
click_points = []
click_labels = []
display_image = None
base_image = None

def mouse_callback(event, x, y, flags, param):
    """Handles mouse clicks for selecting points."""
    global click_points, click_labels, display_image, base_image

    if event == cv2.EVENT_LBUTTONDOWN:  # Left Click = Positive (Green)
        click_points.append([x, y])
        click_labels.append(1)
        # Draw a solid green circle
        cv2.circle(display_image, (x, y), 5, (0, 255, 0), -1) 
        cv2.imshow("Select Points", display_image)

    elif event == cv2.EVENT_RBUTTONDOWN: # Right Click = Negative (Red)
        click_points.append([x, y])
        click_labels.append(0)
        # Draw a solid red circle
        cv2.circle(display_image, (x, y), 5, (0, 0, 255), -1)
        cv2.imshow("Select Points", display_image)

def interactive_setup(first_image_path, predictor):
    """
    Opens a window to let the user select points on the first image.
    Returns calculated relative points and labels.
    """
    global display_image, base_image, click_points, click_labels

    print(f"\n--- 🖱️ INTERACTIVE MODE ---")
    print("1. Left Click  = Positive Point (Include this area)")
    print("2. Right Click = Negative Point (Exclude this area)")
    print("3. Press 'SPACE' to PREVIEW the mask")
    print("4. Press 'R'     to RESET points")
    print("5. Press 'ENTER' to CONFIRM and start batch processing")
    print("6. Press 'Q'     to QUIT")

    # Load first image
    image = cv2.imread(first_image_path)
    if image is None:
        raise ValueError(f"Could not load the image at: {first_image_path}")
    
    # Keep original for SAM, create copy for display
    original_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    base_image = image.copy()
    display_image = image.copy()
    h, w = image.shape[:2]

    # Set image in SAM
    predictor.set_image(original_rgb)

    cv2.namedWindow("Select Points")
    cv2.setMouseCallback("Select Points", mouse_callback)
    
    preview_mask = None

    while True:
        # If we have a preview mask, overlay it
        if preview_mask is not None:
            # Create a red overlay
            overlay = display_image.copy()
            overlay[preview_mask > 0] = [0, 0, 255] # Red mask
            # Blend it
            combined = cv2.addWeighted(overlay, 0.5, display_image, 0.5, 0)
            cv2.imshow("Select Points", combined)
        else:
            cv2.imshow("Select Points", display_image)

        key = cv2.waitKey(1) & 0xFF

        # --- CONTROLS ---
        
        # SPACE: Generate Preview
        if key == 32: 
            if len(click_points) == 0:
                print("Please click at least one point first.")
                continue
            
            print("generating preview...")
            pts = np.array(click_points)
            lbls = np.array(click_labels)
            
            masks, _, _ = predictor.predict(
                point_coords=pts,
                point_labels=lbls,
                multimask_output=False
            )
            preview_mask = masks[0]
            print("Preview updated.")

        # R: Reset
        elif key == ord('r'):
            click_points = []
            click_labels = []
            display_image = base_image.copy()
            preview_mask = None
            print("Points reset.")
            cv2.imshow("Select Points", display_image)

        # ENTER: Confirm and Proceed
        elif key == 13: 
            if len(click_points) == 0:
                print("⚠️ Please select points before confirming.")
                continue
            print("✅ Selection confirmed. Calculating relative coordinates...")
            cv2.destroyAllWindows()
            
            # Convert absolute pixels to relative coordinates (0.0 to 1.0)
            relative_points = np.array(click_points, dtype=float)
            relative_points[:, 0] /= w # Divide x by width
            relative_points[:, 1] /= h # Divide y by height
            
            return relative_points, np.array(click_labels)

        # Q: Quit
        elif key == ord('q'):
            print("Quitting...")
            cv2.destroyAllWindows()
            exit()

def get_setup_via_gui():
    """
    1. Asks user to select the specific Template Image.
    2. Derives Input Folder from that image path.
    3. Asks user for Output Folder.
    """
    # Create root window and hide it
    root = tk.Tk()
    root.withdraw()

    print("--- 📂 Selection ---")
    
    # 1. Select The Specific Image (Template)
    print("Please select the REFERENCE IMAGE (Template to click points on)...")
    template_path = filedialog.askopenfilename(
        title="Select Reference Image (Template)",
        filetypes=[("Image Files", "*.png *.jpg *.jpeg *.tif *.tiff *.bmp")]
    )
    
    if not template_path:
        print("❌ No image selected. Exiting.")
        return None, None, None

    # Derive the Input Folder from the chosen image
    input_folder = os.path.dirname(template_path)
    print(f"Reference Image: {template_path}")
    print(f"Input Folder detected: {input_folder}")

    # 2. Select Output Folder
    print("Please select the OUTPUT folder (where to save masks)...")
    output_folder = filedialog.askdirectory(title="Select Output Folder (Save Masks)")
    if not output_folder:
        print("❌ No output folder selected. Exiting.")
        return None, None, None
    print(f"Output selected: {output_folder}")

    return input_folder, output_folder, template_path

def process_images():
    # --- SETUP ---
    print("--- Starting SAM Batch Segmenter (Interactive) ---")
    
    # Get paths from user
    INPUT_FOLDER, OUTPUT_FOLDER, TEMPLATE_PATH = get_setup_via_gui()
    
    if INPUT_FOLDER is None or OUTPUT_FOLDER is None or TEMPLATE_PATH is None:
        return

    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    # Init SAM
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading SAM model on: {device}...")
    try:
        sam = sam_model_registry[MODEL_TYPE](checkpoint=CHECKPOINT_PATH)
        sam.to(device=device)
        predictor = SamPredictor(sam)
    except Exception as e:
        print(f"❌ Error loading SAM model: {e}")
        print(f"Ensure '{CHECKPOINT_PATH}' is in the correct folder.")
        return

    # Get all images in that folder for batching
    image_files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.bmp'))]
    if not image_files:
        print("❌ No images found in the input folder.")
        return

    # --- INTERACTIVE PHASE ---
    # We now use the TEMPLATE_PATH chosen by the user
    relative_points, prompt_labels = interactive_setup(TEMPLATE_PATH, predictor)
    
    print("\n--- 🚀 Starting Batch Processing ---")
    print(f"Calculated Relative Points:\n{relative_points}")
    print(f"Labels: {prompt_labels}")

    # --- BATCH PROCESSING LOOP ---
    for filename in image_files:
        print(f"\nProcessing: {filename}...")
        
        image_path = os.path.join(INPUT_FOLDER, filename)
        
        # Load image
        image = cv2.imread(image_path)
        if image is None: 
            print(f"  - ⚠️ Could not load {filename}")
            continue
        
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        predictor.set_image(image_rgb)
        
        # Calculate absolute coords for THIS specific image size
        h, w = image_rgb.shape[:2]
        absolute_points = (relative_points * [w, h]).astype(int)

        masks, scores, _ = predictor.predict(
            point_coords=absolute_points,
            point_labels=prompt_labels,
            multimask_output=False,
        )
        
        if len(masks) > 0:
            binary_mask = np.where(masks[0] > 0, 255, 0).astype(np.uint8)
            output_path = os.path.join(OUTPUT_FOLDER, os.path.splitext(filename)[0] + "_mask.png")
            cv2.imwrite(output_path, binary_mask)
            print(f"  - ✅ Saved to {output_path}")
        
    print("\n--- Batch processing complete! ---")

if __name__ == "__main__":
    process_images()