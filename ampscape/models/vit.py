"""ViT-based encoder-decoder baseline (brief §12.4, 'Swin-UNet or ViT-based'): patch-4 convolutional embedding,
pre-norm transformer blocks with global attention and a learned positional embedding (bilinearly interpolated for
other grid sizes), a convolutional decoder that upsamples back to pixel resolution with a full-resolution skip."""

from __future__ import annotations

import torch
from torch import nn


class Block(nn.Module):
    def __init__(self, dim: int, heads: int, mlp: int = 4, drop: float = 0.0):
        super().__init__()
        self.n1 = nn.LayerNorm(dim)
        self.attn = nn.MultiheadAttention(dim, heads, dropout=drop, batch_first=True)
        self.n2 = nn.LayerNorm(dim)
        self.mlp = nn.Sequential(nn.Linear(dim, mlp * dim), nn.GELU(), nn.Linear(mlp * dim, dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.n1(x)
        x = x + self.attn(h, h, h, need_weights=False)[0]
        return x + self.mlp(self.n2(x))


class ViTUNet(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int = 1,
        patch: int = 4,
        dim: int = 192,
        depth: int = 6,
        heads: int = 6,
        grid: int = 32,
    ):
        super().__init__()
        self.patch = patch
        self.stem = nn.Sequential(
            nn.Conv2d(in_channels, 32, 3, padding=1),
            nn.GELU(),
            nn.Conv2d(32, 32, 3, padding=1),
            nn.GELU(),
        )
        self.embed = nn.Conv2d(in_channels, dim, patch, stride=patch)
        self.pos = nn.Parameter(torch.zeros(1, dim, grid, grid))
        nn.init.trunc_normal_(self.pos, std=0.02)
        self.blocks = nn.ModuleList([Block(dim, heads) for _ in range(depth)])
        self.norm = nn.LayerNorm(dim)
        ups, c = [], dim
        while patch > 1:
            ups += [nn.ConvTranspose2d(c, c // 2, 2, stride=2), nn.GroupNorm(8, c // 2), nn.GELU()]
            c, patch = c // 2, patch // 2
        self.decoder = nn.Sequential(*ups)
        self.head = nn.Sequential(
            nn.Conv2d(c + 32, 64, 3, padding=1), nn.GELU(), nn.Conv2d(64, out_channels, 1)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, _, H, W = x.shape
        s = self.stem(x)
        t = self.embed(x)
        pos = (
            self.pos
            if self.pos.shape[-2:] == t.shape[-2:]
            else nn.functional.interpolate(
                self.pos, size=t.shape[-2:], mode="bilinear", align_corners=False
            )
        )
        t = t + pos
        h, w = t.shape[-2:]
        z = t.flatten(2).transpose(1, 2)
        for b in self.blocks:
            z = b(z)
        z = self.norm(z).transpose(1, 2).reshape(B, -1, h, w)
        z = self.decoder(z)
        return self.head(torch.cat([z, s], dim=1))
