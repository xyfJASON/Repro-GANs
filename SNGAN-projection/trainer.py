import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tqdm import tqdm
import matplotlib.pyplot as plt
import imageio
import torch
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
import torchvision.datasets as dset
import torchvision.transforms as T
import torchvision.utils

import models
from utils.general_utils import parse_config


class Trainer:
    def __init__(self, config_path: str):
        self.config, self.device, self.log_root = parse_config(config_path)
        if not os.path.exists(os.path.join(self.log_root, 'samples')):
            os.makedirs(os.path.join(self.log_root, 'samples'))
        self.dataset, self.dataloader, self.img_channels, self.c_dim = self._get_data()
        self.G, self.D, self.optimizerG, self.optimizerD = self._prepare_training()
        self.writer = SummaryWriter(os.path.join(self.log_root, 'tensorboard'))
        self.sample_z = torch.randn((5 * self.c_dim, self.config['z_dim'], 1, 1), device=self.device)
        self.sample_c = torch.arange(0, self.c_dim, device=self.device).repeat(5, )

    def _get_data(self):
        print('==> Getting data...')
        if self.config['dataset'] == 'mnist':
            transforms = T.Compose([T.Resize((64, 64)), T.ToTensor(), T.Normalize(mean=[0.5], std=[0.5])])
            dataset = dset.MNIST(root=self.config['dataroot'], train=True, transform=transforms, download=False)
            img_channels = 1
            c_dim = 10
        elif self.config['dataset'] == 'fashion_mnist':
            transforms = T.Compose([T.Resize((64, 64)), T.ToTensor(), T.Normalize(mean=[0.5], std=[0.5])])
            dataset = dset.FashionMNIST(root=self.config['dataroot'], train=True, transform=transforms, download=False)
            img_channels = 1
            c_dim = 10
        else:
            raise ValueError(f"Dataset {self.config['dataset']} is not supported now.")
        dataloader = DataLoader(dataset, batch_size=self.config['batch_size'], shuffle=True, num_workers=4, pin_memory=True)
        return dataset, dataloader, img_channels, c_dim

    def _prepare_training(self):
        print('==> Preparing training...')
        G = models.Generator(self.config['z_dim'], self.c_dim, self.img_channels)
        D = models.Discriminator(self.c_dim, self.img_channels)
        G.to(device=self.device)
        D.to(device=self.device)
        optimizerG = optim.Adam(G.parameters(), lr=self.config['optimizer']['adam']['lr'], betas=self.config['optimizer']['adam']['betas'])
        optimizerD = optim.Adam(D.parameters(), lr=self.config['optimizer']['adam']['lr'], betas=self.config['optimizer']['adam']['betas'])
        return G, D, optimizerG, optimizerD

    def load_model(self, model_path):
        ckpt = torch.load(model_path, map_location='cpu')
        self.G.load_state_dict(ckpt['G'])
        self.D.load_state_dict(ckpt['D'])
        self.G.to(device=self.device)
        self.D.to(device=self.device)

    def save_model(self, model_path):
        torch.save({'G': self.G.state_dict(), 'D': self.D.state_dict()}, model_path)

    def train(self):
        print('==> Training...')
        sample_paths = []
        for ep in range(self.config['epochs']):
            self.train_one_epoch(ep)

            if self.config['sample_per_epochs'] and (ep + 1) % self.config['sample_per_epochs'] == 0:
                self.sample_generator(ep, os.path.join(self.log_root, 'samples', f'epoch_{ep}.png'))
                sample_paths.append(os.path.join(self.log_root, 'samples', f'epoch_{ep}.png'))

        self.save_model(os.path.join(self.log_root, 'model.pt'))
        self.generate_gif(sample_paths, os.path.join(self.log_root, f'samples.gif'))
        self.writer.close()

    def train_one_epoch(self, ep):
        self.G.train()
        self.D.train()
        with tqdm(self.dataloader, desc=f'Epoch {ep}', ncols=120) as pbar:
            for it, (X, y) in enumerate(pbar):
                X = X.to(device=self.device, dtype=torch.float32)
                y = y.to(device=self.device, dtype=torch.long)

                # --------- train discriminator --------- #
                # min E[max(0, 1 - D(X, y))] + E[max(0, 1 + D(G(z, y), y))]
                z = torch.randn((X.shape[0], self.config['z_dim'], 1, 1), device=self.device)
                fake = self.G(z, y).detach()
                d_real, d_fake = self.D(X, y), self.D(fake, y)
                lossD = torch.mean(F.relu(1 - d_real) + F.relu(1 + d_fake))
                self.optimizerD.zero_grad()
                lossD.backward()
                self.optimizerD.step()
                self.writer.add_scalar('D/loss', lossD.item(), it + ep * len(self.dataloader))

                # --------- train generator --------- #
                # min -D(G(z, y), y)
                if (it + 1) % self.config['d_iters'] == 0:
                    z = torch.randn((X.shape[0], self.config['z_dim'], 1, 1), device=self.device)
                    fake = self.G(z, y)
                    lossG = -torch.mean(self.D(fake, y))
                    self.optimizerG.zero_grad()
                    lossG.backward()
                    self.optimizerG.step()
                    self.writer.add_scalar('G/loss', lossG.item(), it + ep * len(self.dataloader))

    @torch.no_grad()
    def sample_generator(self, ep, savepath):
        self.G.eval()
        X = self.G(self.sample_z, self.sample_c).cpu()
        X = X.view(-1, self.img_channels, 64, 64)
        X = torchvision.utils.make_grid(X, nrow=self.c_dim, normalize=True, value_range=(-1, 1))
        fig, ax = plt.subplots(1, 1)
        ax.imshow(torch.permute(X, [1, 2, 0]))
        ax.set_axis_off()
        ax.set_title(f'Epoch {ep}')
        fig.savefig(savepath, dpi=150, bbox_inches='tight')
        plt.close(fig)

    @staticmethod
    def generate_gif(img_paths, savepath, duration=0.1):
        images = [imageio.imread(p) for p in img_paths]
        imageio.mimsave(savepath, images, 'GIF', duration=duration)
