"""Webcam capture tool for collecting raw training images.

Target: 10 images per class from varied angles and lighting.
The augment.py script will expand these into 500+ training images.

Usage:
  python capture_tool.py --class ip      # 10 photos of the investigational product
  python capture_tool.py --class not_ip  # 10 photos of background / wrong objects

Controls:
  SPACE  = save current frame
  Q      = quit

Tips for 10 good IP shots:
  1. Top-down, well-lit
  2. Slight left tilt
  3. Slight right tilt
  4. Close-up (fill the circle)
  5. Further away (pill smaller in circle)
  6. Dim lighting
  7. Bright/backlit
  8. On dark background
  9. On light background
  10. Held in palm of hand
"""

import cv2
import os
import argparse
import time

parser = argparse.ArgumentParser()
parser.add_argument("--class", dest="cls", required=True, choices=["ip", "not_ip"])
parser.add_argument("--output", default="data_raw")  # raw images → data_raw/
parser.add_argument("--target", type=int, default=10)
args = parser.parse_args()

OUT_DIR = os.path.join(args.output, args.cls)
os.makedirs(OUT_DIR, exist_ok=True)

cap = cv2.VideoCapture(0)
count = len([f for f in os.listdir(OUT_DIR) if f.endswith(('.jpg','.jpeg','.png'))])

print(f"Capturing [{args.cls}] images.")
print(f"Target: {args.target} images. Saved so far: {count}")
print("Controls: SPACE = save | Q = quit")
print()

if args.cls == 'ip':
    tips = [
        "Shot 1: Top-down, well-lit",
        "Shot 2: Slight left tilt",
        "Shot 3: Slight right tilt",
        "Shot 4: Close-up (fill the circle)",
        "Shot 5: Further away",
        "Shot 6: Dim lighting",
        "Shot 7: Bright/backlit",
        "Shot 8: Dark background",
        "Shot 9: Light/white background",
        "Shot 10: Held in palm of hand",
    ]
else:
    tips = [
        "Shot 1: Empty hand",
        "Shot 2: Empty table",
        "Shot 3: Different pill (wrong medication)",
        "Shot 4: Pen or small object",
        "Shot 5: Finger covering ROI",
        "Shot 6: Nothing in frame",
        "Shot 7: Phone face-down",
        "Shot 8: Different pill, dim lighting",
        "Shot 9: Blurry / motion blur",
        "Shot 10: Different pill, held in palm",
    ]

while True:
    ret, frame = cap.read()
    if not ret:
        break

    h, w = frame.shape[:2]
    roi_size = int(min(h, w) * 0.55)
    x1 = (w - roi_size) // 2
    y1 = (h - roi_size) // 2
    x2 = x1 + roi_size
    y2 = y1 + roi_size

    display = frame.copy()
    color = (0, 200, 255) if count < args.target else (0, 255, 100)
    cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)

    tip = tips[min(count, len(tips)-1)]
    cv2.putText(display, f"{count}/{args.target}: {tip}",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    cv2.putText(display, "SPACE=save  Q=quit",
                (10, h-15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,200), 1)

    if count >= args.target:
        cv2.putText(display, f"✅ Target reached! Run augment.py next.",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 100), 2)

    cv2.imshow("Capture Tool", display)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord(' '):
        crop = frame[y1:y2, x1:x2]
        crop_resized = cv2.resize(crop, (224, 224))
        fname = os.path.join(OUT_DIR, f"{args.cls}_{int(time.time()*1000)}.jpg")
        cv2.imwrite(fname, crop_resized)
        count += 1
        print(f"  [{count}/{args.target}] Saved: {fname}")
        if count >= args.target:
            print(f"\n✔ Target reached for [{args.cls}]. Now run: python augment.py")

cap.release()
cv2.destroyAllWindows()
print(f"\nDone. {count} images in {OUT_DIR}/")
