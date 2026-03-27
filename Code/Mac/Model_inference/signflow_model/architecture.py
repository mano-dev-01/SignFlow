from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class LandmarkEmbedding(nn.Module):
    def __init__(self, in_features, units):
        super().__init__()
        self.empty_embedding = nn.Parameter(torch.zeros(units))
        self.proj = nn.Sequential(
            nn.Linear(in_features, units, bias=False),
            nn.GELU(),
            nn.Linear(units, units, bias=False),
        )

    def forward(self, x):
        out = self.proj(x)
        mask = x.abs().sum(dim=-1, keepdim=True) == 0
        return torch.where(mask, self.empty_embedding, out)


class LandmarkTransformerEmbedding(nn.Module):
    def __init__(self, max_frames, units, lips_units, hands_units, pose_units):
        super().__init__()
        self.positional_embedding = nn.Embedding(max_frames + 1, units)
        nn.init.zeros_(self.positional_embedding.weight)
        self.lips_embedding = LandmarkEmbedding(40 * 3, lips_units)
        self.lh_embedding = LandmarkEmbedding(21 * 3, hands_units)
        self.rh_embedding = LandmarkEmbedding(21 * 3, hands_units)
        self.pose_embedding = LandmarkEmbedding(10 * 3, pose_units)
        self.landmark_weights = nn.Parameter(torch.zeros(4))
        self.fc = nn.Sequential(
            nn.Linear(max(lips_units, hands_units, pose_units), units, bias=False),
            nn.GELU(),
            nn.Linear(units, units, bias=False),
        )
        self.max_frames = max_frames

    def forward(self, frames, non_empty_frame_idxs):
        x = frames
        lips = x[:, :, 0:40, :].reshape(x.shape[0], x.shape[1], 40 * 3)
        lh = x[:, :, 40:61, :].reshape(x.shape[0], x.shape[1], 21 * 3)
        rh = x[:, :, 61:82, :].reshape(x.shape[0], x.shape[1], 21 * 3)
        pose = x[:, :, 82:92, :].reshape(x.shape[0], x.shape[1], 10 * 3)
        lips_emb = self.lips_embedding(lips)
        lh_emb = self.lh_embedding(lh)
        rh_emb = self.rh_embedding(rh)
        pose_emb = self.pose_embedding(pose)
        mu = max(lips_emb.shape[-1], lh_emb.shape[-1], rh_emb.shape[-1], pose_emb.shape[-1])
        if lips_emb.shape[-1] < mu:
            lips_emb = F.pad(lips_emb, (0, mu - lips_emb.shape[-1]))
        if lh_emb.shape[-1] < mu:
            lh_emb = F.pad(lh_emb, (0, mu - lh_emb.shape[-1]))
        if rh_emb.shape[-1] < mu:
            rh_emb = F.pad(rh_emb, (0, mu - rh_emb.shape[-1]))
        if pose_emb.shape[-1] < mu:
            pose_emb = F.pad(pose_emb, (0, mu - pose_emb.shape[-1]))
        stacked = torch.stack([lips_emb, lh_emb, rh_emb, pose_emb], dim=-1)
        weights = torch.softmax(self.landmark_weights, dim=0)
        fused = (stacked * weights).sum(dim=-1)
        fused = self.fc(fused)
        max_idx = non_empty_frame_idxs.max(dim=1, keepdim=True).values.clamp(min=1)
        pos_indices = torch.where(
            non_empty_frame_idxs == -1.0,
            torch.tensor(self.max_frames, device=frames.device, dtype=torch.long),
            (non_empty_frame_idxs / max_idx * self.max_frames)
            .long()
            .clamp(0, self.max_frames - 1),
        )
        return fused + self.positional_embedding(pos_indices)


class TransformerBlock(nn.Module):
    def __init__(self, units, num_heads, mlp_ratio=4, dropout=0.1):
        super().__init__()
        self.norm1 = nn.LayerNorm(units)
        self.attn = nn.MultiheadAttention(
            units,
            num_heads,
            dropout=dropout,
            batch_first=True,
        )
        self.norm2 = nn.LayerNorm(units)
        self.mlp = nn.Sequential(
            nn.Linear(units, units * mlp_ratio),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(units * mlp_ratio, units),
            nn.Dropout(dropout),
        )

    def forward(self, x, key_padding_mask=None):
        normed = self.norm1(x)
        attn_out, _ = self.attn(normed, normed, normed, key_padding_mask=key_padding_mask)
        x = x + attn_out
        return x + self.mlp(self.norm2(x))


class LandmarkTransformer(nn.Module):
    def __init__(
        self,
        num_classes,
        max_frames=64,
        units=512,
        num_blocks=4,
        num_heads=8,
        mlp_ratio=4,
        dropout=0.2,
        emb_dropout=0.1,
        lips_units=384,
        hands_units=384,
        pose_units=256,
    ):
        super().__init__()
        self.embedding = LandmarkTransformerEmbedding(
            max_frames,
            units,
            lips_units,
            hands_units,
            pose_units,
        )
        self.emb_dropout = nn.Dropout(emb_dropout)
        self.blocks = nn.ModuleList(
            TransformerBlock(units, num_heads, mlp_ratio, dropout)
            for _ in range(num_blocks)
        )
        self.norm = nn.LayerNorm(units)
        self.head_dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(units, num_classes)
        self._init_weights()

    def _init_weights(self):
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.trunc_normal_(module.weight, std=0.02)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.LayerNorm):
                nn.init.ones_(module.weight)
                nn.init.zeros_(module.bias)

    def forward(self, frames, non_empty_frame_idxs):
        x = self.embedding(frames, non_empty_frame_idxs)
        x = self.emb_dropout(x)
        key_padding_mask = non_empty_frame_idxs == -1.0
        for block in self.blocks:
            x = block(x, key_padding_mask=key_padding_mask)
        x = self.norm(x)
        mask = (~key_padding_mask).unsqueeze(-1).float()
        denom = mask.sum(dim=1).clamp(min=1e-6)
        x = (x * mask).sum(dim=1) / denom
        x = self.head_dropout(x)
        return self.classifier(x)


def build_landmark_transformer(num_classes: int, config: dict) -> LandmarkTransformer:
    return LandmarkTransformer(
        num_classes=num_classes,
        max_frames=config.get("max_frames", 64),
        units=config.get("units", 512),
        num_blocks=config.get("num_blocks", 8),
        num_heads=config.get("num_heads", 8),
        dropout=config.get("dropout", 0.35),
    )
