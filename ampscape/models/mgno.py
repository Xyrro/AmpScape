# ruff: noqa: E701, E741, B007
"""MgNO baseline (He, Liu & Xu, "MgNO: Efficient Parameterization of Linear Operators via Multigrid", ICLR 2024,
arXiv 2310.19809) — vendored official implementation plus a thin AmpScape adapter.

Origin
------
Source: https://github.com/xlliu2017/MgNO, file ``models.py`` at commit 3a68a900bcccdb2246fd86ede4b001440a56c152
(``3a68a90``, "Update LICENSE.txt", 2024-03-15), fetched 2026-10-04 from
https://raw.githubusercontent.com/xlliu2017/MgNO/3a68a900bcccdb2246fd86ede4b001440a56c152/models.py
(sha256 174ba2acbb8042d892cd76427db82d4d70f0ab047ec66034c52c67b6eed1c54c). Licence: MIT, Copyright (c) 2024
Xinliang Liu (``LICENSE.txt`` in that repository; notice reproduced below). Selection rationale and the
line-by-line comparison against ``main`` are in ``docs/wp6_implementations.md``.

What was copied: the classes ``MgIte``, ``MgIte_init``, ``Restrict``, ``MgConv_DC`` and ``MgNO_DC`` (the Darcy
model used by the README ``darcy.py`` commands), verbatim, inside the ``# fmt: off`` block.

What was changed relative to upstream:
  * dropped the repository-local imports (``numpy``, ``torch.nn.functional as F``, ``torchinfo.summary``,
    ``utilities3.count_params``) — only ``torch`` and ``torch.nn`` are used;
  * ``MgNO_DC.__init__``: the output head ``nn.Conv2d(num_channel_u, 1, ...)`` now uses ``output_dim``
    (upstream accepts the argument but ignores it); marked with an ``# AmpScape change`` comment;
  * trailing whitespace stripped; nothing else (no reformatting — the block is excluded from ``ruff format``).

Adapter: ``MgNO`` (below) builds ``MgNO_DC`` with ``num_channel_f = in_channels``, ``output_dim = out_channels``,
``normalizer=None`` (target standardisation lives in our loader) and the README Darcy configuration by default
(6 levels, 24 channels, 4 layers, ``num_iteration = [[1, 0]] * 5 + [[2, 0]]``). Input ``(B, C, H, W)`` →
output ``(B, out_channels, H, W)``. The V-cycle needs H and W divisible by 2 ** (levels - 1) (= 32 for 6 levels);
other sizes are zero-padded at the bottom/right edge and the output is cropped back.

MIT License
-----------
Copyright (c) 2024 Xinliang Liu

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from __future__ import annotations

import torch
from torch import nn


# ----------------------------------------------------------------------------------------------------------------
# Vendored from xlliu2017/MgNO models.py @ 3a68a90 (MIT). Verbatim except as listed in the module docstring.
# ----------------------------------------------------------------------------------------------------------------
# fmt: off
class MgIte(nn.Module):
    def __init__(self, A, S):
        super().__init__()

        self.A = A
        self.S = S

    def forward(self, out):

        if isinstance(out, tuple):
            u, f = out
            u = u + (self.S(f-self.A(u)))
        else:
            f = out
            u = self.S(f)

        out = (u, f)
        return out

class MgIte_init(nn.Module):
    def __init__(self, S):
        super().__init__()

        self.S = S

    def forward(self, f):
        u = self.S(f)
        return (u, f)

class Restrict(nn.Module):
    def __init__(self, Pi=None, R=None, A=None):
        super().__init__()
        self.Pi = Pi
        self.R = R
        self.A = A
    def forward(self, out):
        u, f = out
        if self.A is not None:
            f = self.R(f-self.A(u))
        else:
            f = self.R(f)
        u = self.Pi(u)
        out = (u,f)
        return out

class MgConv_DC(nn.Module):
    def __init__(self, num_iteration, num_channel_u, num_channel_f, padding_mode='zeros', bias=False, use_res=False,):
        super().__init__()
        self.num_iteration = num_iteration
        self.num_channel_u = num_channel_u
        self.padding_mode = padding_mode

        self.RTlayers = nn.ModuleList()
        for j in range(len(num_iteration)-1):
            self.RTlayers.append(nn.ConvTranspose2d(num_channel_u, num_channel_u, kernel_size=4, stride=2, padding=1, bias=False))

        layers = []
        for l, num_iteration_l in enumerate(num_iteration): #l: l-th layer.   num_iteration_l: the number of iterations of l-th layer
            post_smooth_layers = []
            for i in range(num_iteration_l[0]):
                S = nn.Conv2d(num_channel_f, num_channel_u, kernel_size=3, stride=1, padding=1, bias=bias, padding_mode=padding_mode)
                if l==0 and i==0:
                    layers.append(MgIte_init(S))
                else:
                    A = nn.Conv2d(num_channel_u, num_channel_f, kernel_size=3, stride=1, padding=1, bias=bias, padding_mode=padding_mode)
                    layers.append(MgIte(A, S))
            if not num_iteration_l[1] == 0:
                for i in range(num_iteration_l[1]):
                    S = nn.Conv2d(num_channel_f, num_channel_u, kernel_size=3, stride=1, padding=1, bias=bias, padding_mode=padding_mode)
                    A = nn.Conv2d(num_channel_u, num_channel_f, kernel_size=3, stride=1, padding=1, bias=bias, padding_mode=padding_mode)
                    post_smooth_layers.append(MgIte(A, S))
            else:
                post_smooth_layers.append(nn.Identity())

            setattr(self, 'layer'+str(l), nn.Sequential(*layers))
            setattr(self, 'post_smooth_layer'+str(l), nn.Sequential(*post_smooth_layers))
            if l < len(num_iteration)-1:
                A = nn.Conv2d(num_channel_u, num_channel_f, kernel_size=3, stride=1, padding=1, bias=bias, padding_mode=padding_mode)
                Pi= nn.Conv2d(num_channel_u, num_channel_u, kernel_size=3, stride=2, padding=1, bias=False, padding_mode=padding_mode)
                R = nn.Conv2d(num_channel_f, num_channel_f, kernel_size=3, stride=2, padding=1, bias=False, padding_mode=padding_mode)
                if use_res:
                    layers= [Restrict(Pi, R, A)]
                else:
                    layers= [Restrict(Pi=Pi, R=R)]

    def forward(self, f):
        out_list = [0] * len(self.num_iteration)
        out = f

        for l in range(len(self.num_iteration)):
            out = getattr(self, 'layer'+str(l))(out)
            out_list[l] = out
        # upblock
        for j in range(len(self.num_iteration)-2,-1,-1):
            u, f = out_list[j][0], out_list[j][1]
            u_post = u + self.RTlayers[j](out_list[j+1][0])
            out = (u_post, f)
            out_list[j] = getattr(self, 'post_smooth_layer'+str(j))(out)

        return out_list[0][0]

class MgNO_DC(nn.Module):
    def __init__(self, num_layer, num_channel_u, num_channel_f, num_classes, num_iteration,
    in_chans=1,  normalizer=None, output_dim=1, activation='gelu', padding_mode='zeros', ):
        super().__init__()
        self.num_layer = num_layer
        self.num_channel_u = num_channel_u
        self.num_channel_f = num_channel_f
        self.num_classes = num_classes
        self.num_iteration = num_iteration

        self.conv_list = nn.ModuleList([])
        self.linear_list = nn.ModuleList([])
        self.linear_list.append(nn.Conv2d(num_channel_f, num_channel_u, kernel_size=1, stride=1, padding=0, bias=True))
        self.conv_list.append(MgConv_DC(num_iteration, num_channel_u, num_channel_f, padding_mode=padding_mode))
        for _ in range(num_layer-1):
            self.conv_list.append(MgConv_DC(num_iteration, num_channel_u, num_channel_u, padding_mode=padding_mode))
            self.linear_list.append(nn.Conv2d(num_channel_u, num_channel_u, kernel_size=1, stride=1, padding=0, bias=True))

        # AmpScape change: output head width = output_dim (upstream hard-codes 1)
        self.linear = nn.Conv2d(num_channel_u, output_dim, kernel_size=1, bias=False)
        self.normalizer = normalizer

        if activation == 'relu':
            self.act = nn.ReLU()
        elif activation == 'gelu':
            self.act = nn.GELU()
        elif activation == 'tanh':
            self.act = nn.Tanh()
        elif activation == 'silu':
            self.act = nn.SiLU()
        else: raise NameError('invalid activation')

    def forward(self, u):

        for i in range(self.num_layer):
            u = self.act(self.conv_list[i](u) + self.linear_list[i](u))
        u = self.normalizer.decode(self.linear(u)) if self.normalizer else self.linear(u)
        return u

# fmt: on
# ----------------------------------------------------------------------------------------------------------------
# End of vendored code.
# ----------------------------------------------------------------------------------------------------------------


class MgNO(nn.Module):
    """AmpScape adapter around ``MgNO_DC`` (paper Darcy configuration by default).

    ``num_iteration`` is the per-level ``[pre, post]`` smoothing-step list (length = ``levels``); the default is the
    README Darcy setting ``[[1, 0]] * (levels - 1) + [[2, 0]]``. Parameter count for ``MgNO(3)``: 578,685
    (572,661 with a single input channel, the paper's 0.57 M).
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int = 1,
        levels: int = 6,
        width: int = 24,
        layers: int = 4,
        num_iteration=None,
    ):
        super().__init__()
        if num_iteration is None:
            num_iteration = [[1, 0]] * (levels - 1) + [[2, 0]]
        if len(num_iteration) != levels:
            raise ValueError(
                f"num_iteration has {len(num_iteration)} entries, expected levels={levels}"
            )
        self.multiple = 2 ** (levels - 1)
        self.net = MgNO_DC(
            num_layer=layers,
            num_channel_u=width,
            num_channel_f=in_channels,
            num_classes=out_channels,
            num_iteration=[list(it) for it in num_iteration],
            normalizer=None,
            output_dim=out_channels,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        H, W = x.shape[-2:]
        ph, pw = (-H) % self.multiple, (-W) % self.multiple
        if ph or pw:
            x = nn.functional.pad(x, (0, pw, 0, ph))
        y = self.net(x)
        return y[..., :H, :W] if (ph or pw) else y
