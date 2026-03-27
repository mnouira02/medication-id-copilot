"""MobileNetV2 binary classifier — few-shot fine-tuning.

Designed for small augmented datasets (~500 images per class).
Uses aggressive regularisation and a frozen base to avoid overfitting.

Classes:
  0 = ip       (Investigational Product)
  1 = not_ip   (Background / wrong pills / hand / empty)

Outputs a TensorFlow.js model to frontend/public/model/
"""

import os
import json
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, Model, regularizers
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from sklearn.metrics import classification_report, confusion_matrix
import tensorflowjs as tfjs

# --- Config ---
DATA_DIR    = "data"          # output of augment.py
OUTPUT_DIR  = "../frontend/public/model"
IMG_SIZE    = (224, 224)
BATCH_SIZE  = 8               # small batch for small dataset
EPOCHS      = 40
CONF_THRESH = 0.90

os.makedirs(OUTPUT_DIR, exist_ok=True)


# --- Data generators ---
# Light augmentation here on top of augment.py — just flips + small shifts
train_gen = ImageDataGenerator(
    rescale=1./255,
    horizontal_flip=True,
    vertical_flip=True,
    rotation_range=10,
    zoom_range=0.1,
    validation_split=0.2
)

val_gen = ImageDataGenerator(
    rescale=1./255,
    validation_split=0.2
)

train_ds = train_gen.flow_from_directory(
    DATA_DIR,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="binary",
    subset="training",
    shuffle=True,
    seed=42
)

val_ds = val_gen.flow_from_directory(
    DATA_DIR,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="binary",
    subset="validation",
    shuffle=False,
    seed=42
)

print(f"Classes: {train_ds.class_indices}")
print(f"Train samples: {train_ds.samples} | Val samples: {val_ds.samples}")
# Expected: {'ip': 0, 'not_ip': 1}


# --- Model: MobileNetV2 — heavily frozen for small dataset ---
base = MobileNetV2(input_shape=(224, 224, 3), include_top=False, weights="imagenet")

# For a small dataset, freeze ALL of the base.
# We only train the new classification head.
# This prevents catastrophic forgetting and overfitting.
base.trainable = False

x = base.output
x = layers.GlobalAveragePooling2D()(x)
x = layers.Dense(128, activation="relu",
                 kernel_regularizer=regularizers.l2(1e-4))(x)
x = layers.Dropout(0.5)(x)
x = layers.Dense(32, activation="relu",
                 kernel_regularizer=regularizers.l2(1e-4))(x)
x = layers.Dropout(0.3)(x)
output = layers.Dense(1, activation="sigmoid")(x)

model = Model(inputs=base.input, outputs=output)

# --- Phase 1: Train head only ---
print("\nPhase 1: Training classification head (base frozen)...")
model.compile(
    optimizer=tf.keras.optimizers.Adam(1e-3),
    loss="binary_crossentropy",
    metrics=["accuracy", tf.keras.metrics.AUC(name="auc")]
)

callbacks_phase1 = [
    tf.keras.callbacks.EarlyStopping(patience=8, restore_best_weights=True, monitor="val_auc"),
    tf.keras.callbacks.ReduceLROnPlateau(factor=0.5, patience=4, monitor="val_loss", verbose=1),
]

model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=EPOCHS,
    callbacks=callbacks_phase1,
    verbose=1
)

# --- Phase 2: Fine-tune top layers of base ---
print("\nPhase 2: Fine-tuning top 30 layers of MobileNetV2 base...")
base.trainable = True
for layer in base.layers[:-30]:
    layer.trainable = False

# Lower LR for fine-tuning to avoid destroying pretrained features
model.compile(
    optimizer=tf.keras.optimizers.Adam(5e-5),
    loss="binary_crossentropy",
    metrics=["accuracy", tf.keras.metrics.AUC(name="auc")]
)

callbacks_phase2 = [
    tf.keras.callbacks.EarlyStopping(patience=10, restore_best_weights=True, monitor="val_auc"),
    tf.keras.callbacks.ReduceLROnPlateau(factor=0.3, patience=4, monitor="val_loss", verbose=1),
]

model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=EPOCHS,
    callbacks=callbacks_phase2,
    verbose=1
)


# --- Evaluate ---
print("\n" + "="*50)
print("FINAL VALIDATION REPORT")
print("="*50)
val_ds.reset()
y_pred_proba = model.predict(val_ds, verbose=0)
y_pred = (y_pred_proba.flatten() < (1 - CONF_THRESH)).astype(int)  # 0=ip
y_true = val_ds.classes[:len(y_pred)]

print(classification_report(y_true, y_pred, target_names=["ip", "not_ip"]))

cm = confusion_matrix(y_true, y_pred)
print("Confusion matrix (rows=actual, cols=predicted):")
print(f"              ip    not_ip")
print(f"  ip        {cm[0][0]:4d}    {cm[0][1]:4d}   (false negatives = {cm[0][1]})")
print(f"  not_ip    {cm[1][0]:4d}    {cm[1][1]:4d}   (false positives = {cm[1][0]})")
print()
print(f"False negative rate (missed IP): {cm[0][1] / cm[0].sum():.1%}")
print(f"False positive rate (wrong pill accepted): {cm[1][0] / cm[1].sum():.1%}")


# --- Export to TensorFlow.js ---
print(f"\nExporting TFJS model to {OUTPUT_DIR}...")
tfjs.converters.save_keras_model(model, OUTPUT_DIR)

class_map = {v: k for k, v in train_ds.class_indices.items()}
with open(os.path.join(OUTPUT_DIR, "class_map.json"), "w") as f:
    json.dump({
        "classes": class_map,
        "conf_threshold": CONF_THRESH,
        "ip_class_index": train_ds.class_indices["ip"]
    }, f, indent=2)

print("\n✅ Done. Model files:")
for f in os.listdir(OUTPUT_DIR):
    size = os.path.getsize(os.path.join(OUTPUT_DIR, f))
    print(f"   {f:40s} {size/1024:.1f} KB")
print("\nNext: cd ../frontend && npm run dev")
