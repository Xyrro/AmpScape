"""2-D Fourier Neural Operator baseline (Li et al. 2021; brief §12.3): lifting, L spectral layers with a pointwise
skip, projection. Resolution-agnostic; the number of retained modes is the only spatial hyper-parameter."""

from __future__ import annotations

import torch
from torch import nn


class SpectralConv2d(nn.Module):
    def __init__(self, cin: int, cout: int, modes: int):
        super().__init__()
        self.modes = modes
        scale = 1.0 / (cin * cout)
        self.w1 = nn.Parameter(scale * torch.randn(cin, cout, modes, modes, dtype=torch.cfloat))
        self.w2 = nn.Parameter(scale * torch.randn(cin, cout, modes, modes, dtype=torch.cfloat))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, C, H, W = x.shape
        m = min(self.modes, H // 2, W // 2 + 1)
        xf = torch.fft.rfft2(x.float(), norm="ortho")
        out = torch.zeros(B, self.w1.shape[1], H, W // 2 + 1, dtype=torch.cfloat, device=x.device)
        out[:, :, :m, :m] = torch.einsum("bixy,ioxy->boxy", xf[:, :, :m, :m], self.w1[:, :, :m, :m])
        out[:, :, -m:, :m] = torch.einsum(
            "bixy,ioxy->boxy", xf[:, :, -m:, :m], self.w2[:, :, :m, :m]
        )
        return torch.fft.irfft2(out, s=(H, W), norm="ortho")


class FNO2d(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int = 1,
        width: int = 32,
        modes: int = 16,
        layers: int = 4,
    ):
        super().__init__()
        self.lift = nn.Conv2d(in_channels + 2, width, 1)
        self.spec = nn.ModuleList([SpectralConv2d(width, width, modes) for _ in range(layers)])
        self.skip = nn.ModuleList([nn.Conv2d(width, width, 1) for _ in range(layers)])
        self.proj = nn.Sequential(
            nn.Conv2d(width, 4 * width, 1), nn.GELU(), nn.Conv2d(4 * width, out_channels, 1)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, _, H, W = x.shape
        gy = torch.linspace(0, 1, H, device=x.device).view(1, 1, H, 1).expand(B, 1, H, W)
        gx = torch.linspace(0, 1, W, device=x.device).view(1, 1, 1, W).expand(B, 1, H, W)
        h = self.lift(torch.cat([x, gy, gx], dim=1))
        for s, k in zip(self.spec, self.skip, strict=True):
            h = nn.functional.gelu(s(h) + k(h))
        return self.proj(h)
