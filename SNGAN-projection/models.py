import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.utils.parametrizations import spectral_norm


def weights_init(m):
    classname = m.__class__.__name__
    if classname.find('Conv') != -1:
        nn.init.normal_(m.weight, mean=0, std=0.02)
    elif classname.find('Linear') != -1:
        nn.init.normal_(m.weight, mean=0, std=0.02)
    elif classname.find('BatchNorm') != -1:
        nn.init.constant_(m.weight, 1)
        nn.init.constant_(m.bias, 0)


class Discriminator(nn.Module):
    def __init__(self, c_dim: int, img_channels: int) -> None:
        super().__init__()
        self.c_dim = c_dim
        self.phi = nn.Sequential(
            spectral_norm(nn.Conv2d(img_channels, 64, (4, 4), stride=(2, 2), padding=1)),  # 32x32
            nn.LeakyReLU(0.2, inplace=True),
            spectral_norm(nn.Conv2d(64, 128, (4, 4), stride=(2, 2), padding=1)),  # 16x16
            nn.LeakyReLU(0.2, inplace=True),
            spectral_norm(nn.Conv2d(128, 256, (4, 4), stride=(2, 2), padding=1)),  # 8x8
            nn.LeakyReLU(0.2, inplace=True),
            spectral_norm(nn.Conv2d(256, 512, (4, 4), stride=(2, 2), padding=1)),  # 4x4
            nn.LeakyReLU(0.2, inplace=True),
            spectral_norm(nn.Conv2d(512, 1024, (4, 4), stride=(1, 1), padding=0)),  # 1x1
            nn.Flatten(),
        )
        self.classifier = spectral_norm(nn.Linear(1024, c_dim))
        self.psi = spectral_norm(nn.Linear(1024, 1))
        self.apply(weights_init)

    def forward(self, X: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        """
        Args:
            X: (N, C, H, W)
            y: (N, )
        """
        phiX = self.phi(X)
        f1 = torch.sum(F.one_hot(y, num_classes=self.c_dim) * self.classifier(phiX), dim=1, keepdim=True)
        f2 = self.psi(phiX)
        return f1 + f2


class Generator(nn.Module):
    def __init__(self, z_dim: int, c_dim: int, img_channels: int) -> None:
        super().__init__()
        self.c_dim = c_dim
        self.gen = nn.Sequential(
            nn.ConvTranspose2d(z_dim + c_dim, 1024, (4, 4), stride=(1, 1), padding=(0, 0)),  # 4x4
            nn.BatchNorm2d(1024),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(1024, 512, (4, 4), stride=(2, 2), padding=(1, 1)),  # 8x8
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(512, 256, (4, 4), stride=(2, 2), padding=(1, 1)),  # 16x16
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(256, 128, (4, 4), stride=(2, 2), padding=(1, 1)),  # 32x32
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(128, img_channels, (4, 4), stride=(2, 2), padding=(1, 1)),  # 64x64
            nn.Tanh(),
        )
        self.apply(weights_init)

    def forward(self, X: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        """
        Args:
            X: (N, z_dim, 1, 1)
            y: (N, )
        """
        y = F.one_hot(y, num_classes=self.c_dim)
        y = y.view(*y.shape, 1, 1)
        return self.gen(torch.cat([X, y], dim=1))


def _test():
    G = Generator(z_dim=100, c_dim=10, img_channels=3)
    D = Discriminator(c_dim=10, img_channels=3)
    z = torch.randn(10, 100, 1, 1)
    y = torch.randint(0, 10, (10, ))
    fakeX = G(z, y)
    score = D(fakeX, y)
    print(fakeX.shape)
    print(score.shape)


if __name__ == '__main__':
    _test()
