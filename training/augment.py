"""Few-shot augmentation pipeline.

Takes ~10 real photos per class and generates a large augmented dataset
suitable for fine-tuning MobileNetV2. Each source image produces ~50
augmented variants using aggressive but clinically realistic transforms.

Usage:
  python augment.py

Input:   training/data_raw/ip/       (10 real photos)
         training/data_raw/not_ip/   (10 real photos)

Output:  training/data/ip/           (500+ augmented images)
         training/data/not_ip/       (500+ augmented images)

The output folder is what train.py reads.
"""

import os
import cv2
import numpy as np
from pathlib import Path
import random
import itertools

RAW_DIR  = Path("data_raw")
OUT_DIR  = Path("data")
IMG_SIZE = 224
AUGS_PER_IMAGE = 50   # 10 photos x 50 = 500 per class

random.seed(42)
np.random.seed(42)


def load_and_resize(path: Path) -> np.ndarray:
    img = cv2.imread(str(path))
    if img is None:
        raise ValueError(f"Could not load image: {path}")
    return cv2.resize(img, (IMG_SIZE, IMG_SIZE))


# -----------------------------------------------------------------------
# Augmentation functions (all operate on 224x224 BGR numpy arrays)
# -----------------------------------------------------------------------

def random_rotation(img, max_deg=30):
    angle = random.uniform(-max_deg, max_deg)
    M = cv2.getRotationMatrix2D((IMG_SIZE//2, IMG_SIZE//2), angle, 1.0)
    return cv2.warpAffine(img, M, (IMG_SIZE, IMG_SIZE),
                          borderMode=cv2.BORDER_REFLECT)

def random_brightness(img, low=0.4, high=1.8):
    """Simulate range from dim room to bright window light."""
    factor = random.uniform(low, high)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:,:,2] = np.clip(hsv[:,:,2] * factor, 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

def random_contrast(img, low=0.6, high=1.6):
    mean = img.mean()
    return np.clip(mean + (img.astype(np.float32) - mean) * random.uniform(low, high), 0, 255).astype(np.uint8)

def random_blur(img):
    """Simulate 2MP camera blur at different intensities."""
    k = random.choice([0, 1, 3, 5, 7])  # 0 = no blur
    if k == 0:
        return img
    return cv2.GaussianBlur(img, (k, k), 0)

def random_noise(img, intensity=15):
    """Salt-and-pepper + Gaussian noise for degraded sensor simulation."""
    noise = np.random.randint(-intensity, intensity, img.shape, dtype=np.int16)
    return np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

def random_flip(img):
    return cv2.flip(img, random.choice([-1, 0, 1]))

def random_zoom(img, min_crop=0.70):
    """Crop a random sub-region and resize back to 224x224 (zoom effect)."""
    scale = random.uniform(min_crop, 1.0)
    size = int(IMG_SIZE * scale)
    x = random.randint(0, IMG_SIZE - size)
    y = random.randint(0, IMG_SIZE - size)
    cropped = img[y:y+size, x:x+size]
    return cv2.resize(cropped, (IMG_SIZE, IMG_SIZE))

def random_hue_shift(img, max_shift=15):
    """Slight colour shift to handle colour temperature variation."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.int32)
    hsv[:,:,0] = (hsv[:,:,0] + random.randint(-max_shift, max_shift)) % 180
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

def random_perspective(img):
    """Slight perspective warp to simulate hand tilt."""
    margin = int(IMG_SIZE * 0.08)
    src = np.float32([[0,0],[IMG_SIZE,0],[IMG_SIZE,IMG_SIZE],[0,IMG_SIZE]])
    dst = np.float32([
        [random.randint(0, margin),       random.randint(0, margin)],
        [IMG_SIZE - random.randint(0, margin), random.randint(0, margin)],
        [IMG_SIZE - random.randint(0, margin), IMG_SIZE - random.randint(0, margin)],
        [random.randint(0, margin),       IMG_SIZE - random.randint(0, margin)]
    ])
    M = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(img, M, (IMG_SIZE, IMG_SIZE),
                               borderMode=cv2.BORDER_REFLECT)

def add_vignette(img):
    """Darken edges to simulate phone lens falloff."""
    rows, cols = img.shape[:2]
    k_x = cv2.getGaussianKernel(cols, cols * 0.7)
    k_y = cv2.getGaussianKernel(rows, rows * 0.7)
    kernel = k_y * k_x.T
    mask = kernel / kernel.max()
    vignette = (img * mask[:,:,np.newaxis]).astype(np.uint8)
    return vignette


ALL_AUGMENTATIONS = [
    random_rotation,
    random_brightness,
    random_contrast,
    random_blur,
    random_noise,
    random_flip,
    random_zoom,
    random_hue_shift,
    random_perspective,
    add_vignette,
]


def augment_image(img: np.ndarray, n: int) -> list:
    """Generate n augmented variants of a single image."""
    results = []
    for _ in range(n):
        aug = img.copy()
        # Apply 3-5 random augmentations per image (compound transforms)
        chosen = random.sample(ALL_AUGMENTATIONS, k=random.randint(3, 5))
        for fn in chosen:
            aug = fn(aug)
        results.append(aug)
    return results


def process_class(cls: str):
    raw_path = RAW_DIR / cls
    out_path = OUT_DIR / cls
    out_path.mkdir(parents=True, exist_ok=True)

    source_files = list(raw_path.glob("*.jpg")) + \
                   list(raw_path.glob("*.jpeg")) + \
                   list(raw_path.glob("*.png"))

    if not source_files:
        raise FileNotFoundError(f"No images found in {raw_path}. "
                                f"Run capture_tool.py --class {cls} first.")

    print(f"\n[{cls}] Found {len(source_files)} source images. "
          f"Generating {len(source_files) * AUGS_PER_IMAGE} augmented images...")

    total = 0
    for src_file in source_files:
        img = load_and_resize(src_file)

        # Always keep the original too
        cv2.imwrite(str(out_path / f"orig_{src_file.name}"), img)
        total += 1

        augmented = augment_image(img, AUGS_PER_IMAGE)
        for i, aug_img in enumerate(augmented):
            fname = out_path / f"aug_{src_file.stem}_{i:03d}.jpg"
            cv2.imwrite(str(fname), aug_img)
            total += 1

    print(f"  ✅ {total} images written to {out_path}/")
    return total


if __name__ == "__main__":
    print("=" * 55)
    print("Few-Shot Augmentation Pipeline")
    print(f"Source: {RAW_DIR}/   Output: {OUT_DIR}/")
    print(f"Augmentations per image: {AUGS_PER_IMAGE}")
    print("=" * 55)

    for cls in ["ip", "not_ip"]:
        if not (RAW_DIR / cls).exists():
            print(f"  ⚠️  Skipping '{cls}' — {RAW_DIR}/{cls}/ not found.")
            continue
        count = process_class(cls)

    print("\n✅ Augmentation complete. Now run: python train.py")
