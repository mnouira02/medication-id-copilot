import argparse
import json
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from pathlib import Path
from model.cnn_pill_classifier import build_model


def train(data_dir: str, protocol_path: str, epochs: int, output_path: str):
    protocol = json.loads(Path(protocol_path).read_text())
    class_names = [p["id"] for p in protocol["expected_pills"]]
    num_classes = len(class_names)

    print(f"Training CNN for {num_classes} classes: {class_names}")

    transform_train = transforms.Compose([
        transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225])
    ])

    transform_val = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225])
    ])

    # ImageFolder expects: data_dir/pill_001/*.jpg, data_dir/placebo/*.jpg
    # Folder names must match pill IDs in protocol.json
    train_ds = datasets.ImageFolder(root=f"{data_dir}/train", transform=transform_train)
    val_ds = datasets.ImageFolder(root=f"{data_dir}/val", transform=transform_val)

    train_loader = DataLoader(train_ds, batch_size=32, shuffle=True, num_workers=4)
    val_loader = DataLoader(val_ds, batch_size=32, shuffle=False, num_workers=4)

    model = build_model(num_classes)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=1e-4)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)

    best_val_acc = 0.0

    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()

        # Validation
        model.eval()
        correct = total = 0
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                _, predicted = torch.max(outputs, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()

        val_acc = correct / total
        scheduler.step()
        print(f"Epoch {epoch+1}/{epochs} | Loss: {running_loss/len(train_loader):.4f} | Val Acc: {val_acc:.4f}")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), output_path)
            print(f"  ✅ Best model saved to {output_path} (acc={val_acc:.4f})")

    print(f"\nTraining complete. Best validation accuracy: {best_val_acc:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to data dir with train/ and val/ subfolders")
    parser.add_argument("--protocol", default="config/protocol.json")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--output", default="model/model.pt")
    args = parser.parse_args()
    train(args.data, args.protocol, args.epochs, args.output)
