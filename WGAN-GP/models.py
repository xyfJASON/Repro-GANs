import torch
import torch.nn as nn


def weights_init(m):
    classname = m.__class__.__name__
    if classname.find('Linear') != -1:
        nn.init.normal_(m.weight, mean=0, std=0.02)
    elif classname.find('BatchNorm') != -1:
        nn.init.constant_(m.weight, 1)
        nn.init.constant_(m.bias, 0)


class Discriminator(nn.Module):
    def __init__(self, in_dim: int) -> None:
        super().__init__()
        self.disc = nn.Sequential(
            nn.Linear(in_dim, 256),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(256, 256),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(256, 256),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(256, 1),
        )
        self.apply(weights_init)

    def forward(self, X: torch.Tensor) -> torch.Tensor:
        return self.disc(X)


class Generator(nn.Module):
    def __init__(self, z_dim: int, data_dim: int) -> None:
        super().__init__()
        self.gen = nn.Sequential(
            nn.Linear(z_dim, 256),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(256, 512),
            nn.BatchNorm1d(512),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(512, 1024),
            nn.BatchNorm1d(1024),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Linear(1024, data_dim),
            nn.Tanh(),
        )
        self.apply(weights_init)

    def forward(self, X: torch.Tensor) -> torch.Tensor:
        return self.gen(X)


if __name__ == '__main__':
    G = Generator(100, 1000)
    D = Discriminator(1000)
    z = torch.randn(10, 100)
    fakeX = G(z)
    score = D(fakeX)
    print(fakeX)
    print(score)
