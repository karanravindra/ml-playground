import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision
import lightning.pytorch as pl
from pytorch_lightning.loggers import WandbLogger
from torchmetrics.classification import Accuracy


class ConvolutionalNN(nn.Module):
    """Simple Convolutional Neural Network"""

    def __init__(self) -> None:
        super(ConvolutionalNN, self).__init__()
        self.layers = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2),
            nn.Flatten(),
            nn.Linear(64 * 7 * 7, 128),
            nn.ReLU(inplace=True),
            nn.Linear(128, 10),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.view(x.size(0), -1)
        return self.layers(x)


class LitClassifer(pl.LightningModule):
    """PyTorch Lightning module for training a simple MLP on CIFAR10 dataset."""

    def __init__(self, lr=1e-4, batch_size=64):
        super(LitClassifer, self).__init__()
        self.model = ConvolutionalNN()
        self.lr = lr
        self.batch_size = batch_size

        self.criterion = F.cross_entropy

        self.accuracy = Accuracy(task="multiclass", num_classes=10)
        self.save_hyperparameters()

    def forward(self, x):
        return self.model(x)

    def training_step(self, batch, batch_idx):
        x, y = batch

        y_hat = self(x)

        loss = self.criterion(y_hat, y)
        acc = self.accuracy(y_hat, y)

        self.log("train_loss", loss, on_step=True, prog_bar=True)
        self.log("train_acc", acc, on_step=True)

        return loss

    def validation_step(self, batch, batch_idx):
        x, y = batch

        y_hat = self(x)

        loss = self.criterion(y_hat, y)
        acc = self.accuracy(y_hat, y)

        self.log("val_loss", loss)
        self.log("val_acc", acc)

        return loss

    def configure_optimizers(self):
        return torch.optim.SGD(self.parameters(), lr=self.lr, momentum=0.9)

    def prepare_data(self):
        torchvision.datasets.QMNIST(root="qmnist/data", what="train", download=True)
        torchvision.datasets.QMNIST(root="qmnist/data", what="test", download=True)

    def train_dataloader(self):
        return torch.utils.data.DataLoader(
            torchvision.datasets.CIFAR10(
                root="data",
                train=True,
                transform=torchvision.transforms.ToTensor(),
            ),
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=4,
            persistent_workers=True,
        )

    def val_dataloader(self):
        return torch.utils.data.DataLoader(
            torchvision.datasets.CIFAR10(
                root="data",
                train=False,
                transform=torchvision.transforms.ToTensor(),
            ),
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=2,
            persistent_workers=True,
        )


if __name__ == "__main__":
    model = LitClassifer()
    logger = WandbLogger(
        project="cifar10", save_dir="logs", log_model=True, save_code=True
    )
    logger.watch(model, log="all")
    trainer = pl.Trainer(
        logger=logger,
        max_epochs=20,
        default_root_dir="logs",
        val_check_interval=0.5,
    )
    trainer.fit(model)
