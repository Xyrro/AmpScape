"""Grid-as-graph GNN baseline (brief §12.5): nodes = valid pixels, 8-neighbour edges weighted by Circuitscape's
average-conductance rule (row-normalised); L residual message-passing layers
    h_i <- h_i + MLP([h_i, sum_j w_ij (h_j - h_i)])
so the update uses the exact graph structure (conductance-weighted neighbour differences, the discrete gradient of
Kirchhoff's law). Receptive field = L hops, the known limitation of local message passing on large grids."""
from __future__ import annotations

import torch
from torch import nn


class MPLayer(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.mlp = nn.Sequential(nn.Linear(2 * dim, dim), nn.GELU(), nn.Linear(dim, dim))
        self.norm = nn.LayerNorm(2 * dim)

    def forward(self, h: torch.Tensor, ei: torch.Tensor, w: torch.Tensor) -> torch.Tensor:
        src, dst = ei[0], ei[1]
        msg = ((h[src] - h[dst]) * w[:, None]).to(h.dtype)
        agg = torch.zeros_like(h).index_add_(0, dst, msg)
        return h + self.mlp(self.norm(torch.cat([h, agg], dim=1)))


class GridGNN(nn.Module):
    def __init__(self, in_channels: int, out_channels: int = 1, dim: int = 64, layers: int = 12):
        super().__init__()
        self.enc = nn.Sequential(nn.Linear(in_channels, dim), nn.GELU(), nn.Linear(dim, dim))
        self.layers = nn.ModuleList([MPLayer(dim) for _ in range(layers)])
        self.dec = nn.Sequential(nn.Linear(dim, dim), nn.GELU(), nn.Linear(dim, out_channels))

    def forward(self, x: torch.Tensor, node_index: torch.Tensor, edge_index: torch.Tensor, edge_weight: torch.Tensor) -> torch.Tensor:
        """x (B, C, H, W); node_index (B, H, W) with global node ids (-1 = NoData); edge_index (2, E) global ids."""
        B, C, H, W = x.shape
        valid = node_index >= 0
        feats = x.permute(0, 2, 3, 1)[valid]                       # (N, C) in global node order (row-major per sample)
        h = self.enc(feats)
        for layer in self.layers:
            h = layer(h, edge_index, edge_weight)
        out = torch.zeros(B, H, W, self.dec[-1].out_features, device=x.device, dtype=h.dtype)
        out[valid] = self.dec(h)
        return out.permute(0, 3, 1, 2)
