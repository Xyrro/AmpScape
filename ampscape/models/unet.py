"""U-Net baseline (brief §12.2): 4-level encoder-decoder, GroupNorm + GELU, ~2 M parameters at base width 32."""

from __future__ import annotations

import torch
from torch import nn


def _block(cin: int, cout: int) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv2d(cin, cout, 3, padding=1),
        nn.GroupNorm(8, cout),
        nn.GELU(),
        nn.Conv2d(cout, cout, 3, padding=1),
        nn.GroupNorm(8, cout),
        nn.GELU(),
    )


class UNet(nn.Module):
    def __init__(self, in_channels: int, out_channels: int = 1, base: int = 32, levels: int = 4):
        super().__init__()
        chs = [base * 2**i for i in range(levels + 1)]
        self.enc = nn.ModuleList(
            [_block(in_channels if i == 0 else chs[i - 1], chs[i]) for i in range(levels + 1)]
        )
        self.up = nn.ModuleList(
            [nn.ConvTranspose2d(chs[i + 1], chs[i], 2, stride=2) for i in range(levels)]
        )
        self.dec = nn.ModuleList([_block(chs[i] * 2, chs[i]) for i in range(levels)])
        self.head = nn.Conv2d(chs[0], out_channels, 1)
        self.levels = levels

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        skips = []
        for i, e in enumerate(self.enc):
            x = e(x)
            if i < self.levels:
                skips.append(x)
                x = nn.functional.max_pool2d(x, 2)
        for i in reversed(range(self.levels)):
            x = self.up[i](x)
            x = self.dec[i](torch.cat([x, skips[i]], dim=1))
        return self.head(x)
