import torch
import torch.nn as nn
import torchvision.models as models


def build_model(num_classes: int) -> nn.Module:
    """
    ResNet18 fine-tuned for closed-world pill classification.
    num_classes = number of unique pills in the trial protocol.
    
    Architecture rationale:
    - ResNet18 is lightweight enough for CPU inference at the point of care
    - ImageNet pretrained weights give strong low-level feature extraction
      (edges, textures, colors) which transfer well to pill images
    - Only the final FC layer is replaced — all other weights are fine-tuned
    """
    model = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)

    # Freeze early layers — only fine-tune layer4 + FC
    for name, param in model.named_parameters():
        if not name.startswith("layer4") and not name.startswith("fc"):
            param.requires_grad = False

    # Replace final classification head
    in_features = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Dropout(0.3),
        nn.Linear(in_features, num_classes)
    )

    return model
