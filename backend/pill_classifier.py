import torch
import torchvision.transforms as transforms
from PIL import Image
import io
from pathlib import Path

# Load model once at startup
MODEL_PATH = Path("model/model.pt")
_model = None
_classes = None


def _load_model(num_classes: int):
    import torchvision.models as models
    model = models.resnet18(weights=None)
    model.fc = torch.nn.Linear(model.fc.in_features, num_classes)
    model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
    model.eval()
    return model


def classify_pill(image_bytes: bytes, expected_ids: list[str]) -> dict:
    """
    Runs CNN inference on a raw image bytes input.
    Returns predicted pill_id and confidence score.
    If model.pt does not exist yet (pre-training), returns a safe placeholder.
    """
    global _model, _classes

    if not MODEL_PATH.exists():
        return {
            "predicted_id": "model_not_trained",
            "confidence": 0.0,
            "note": "Run model/train_cnn.py first to generate model.pt"
        }

    if _model is None:
        _classes = expected_ids
        _model = _load_model(len(_classes))

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225])
    ])

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = transform(image).unsqueeze(0)

    with torch.no_grad():
        outputs = _model(tensor)
        probs = torch.softmax(outputs, dim=1)
        confidence, predicted_idx = torch.max(probs, 1)

    return {
        "predicted_id": _classes[predicted_idx.item()],
        "confidence": round(confidence.item(), 4)
    }
