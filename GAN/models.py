import torch
import torch.nn as nn


class Discriminator(nn.Module):
    def __init__(self, in_dim: int) -> None:
        super().__init__()
        self.disc = nn.Sequential(
            nn.Linear(in_dim, 256),
            nn.LeakyReLU(),
            nn.Linear(256, 256),
            nn.LeakyReLU(),
            nn.Linear(256, 256),
            nn.LeakyReLU(),
            nn.Linear(256, 1),
            nn.Sigmoid(),
        )

    def forward(self, X: torch.Tensor) -> torch.Tensor:
        return self.disc(X)


class Generator(nn.Module):
    def __init__(self, z_dim: int, data_dim: int) -> None:
        super().__init__()
        self.gen = nn.Sequential(
            nn.Linear(z_dim, 256),
            nn.LeakyReLU(),
            nn.Linear(256, 256),
            nn.LeakyReLU(),
            nn.Linear(256, 256),
            nn.LeakyReLU(),
            nn.Linear(256, data_dim),
            nn.Tanh(),
        )

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