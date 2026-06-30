"""Lightweight int4 helpers for Phase 0 tests and fixtures."""

from __future__ import annotations

import math

import numpy as np


def pack_int4(values: np.ndarray) -> np.ndarray:
    """Pack signed int4 values into uint8 bytes using two nibbles per byte."""

    array = np.asarray(values)
    if not np.issubdtype(array.dtype, np.integer):
        raise TypeError("values must be an integer NumPy array")

    flat = array.astype(np.int16, copy=False).reshape(-1)
    if flat.size and (flat.min() < -8 or flat.max() > 7):
        raise ValueError("int4 values must be in range [-8, 7]")

    if flat.size % 2:
        flat = np.concatenate([flat, np.zeros(1, dtype=np.int16)])

    nibbles = (flat.astype(np.int16) & 0x0F).astype(np.uint8)
    low = nibbles[0::2]
    high = nibbles[1::2] << 4
    return (low | high).astype(np.uint8)


def unpack_int4(packed: np.ndarray, count: int) -> np.ndarray:
    """Unpack signed int4 values from uint8 bytes."""

    if count < 0:
        raise ValueError("count must be non-negative")

    bytes_array = np.asarray(packed, dtype=np.uint8).reshape(-1)
    if count > bytes_array.size * 2:
        raise ValueError("count exceeds packed int4 capacity")

    unpacked = np.empty(bytes_array.size * 2, dtype=np.int8)
    unpacked[0::2] = _decode_signed_nibble(bytes_array & 0x0F)
    unpacked[1::2] = _decode_signed_nibble((bytes_array >> 4) & 0x0F)
    return unpacked[:count]


def symmetric_int4_quantize(matrix: np.ndarray, group_size: int = 128) -> tuple[np.ndarray, np.ndarray]:
    """Quantize a small 2D matrix with groupwise symmetric int4 scales."""

    if group_size <= 0:
        raise ValueError("group_size must be positive")

    array = np.asarray(matrix, dtype=np.float32)
    if array.ndim != 2:
        raise ValueError("matrix must be 2D")

    rows, cols = array.shape
    groups = math.ceil(cols / group_size)
    scales = np.empty((rows, groups), dtype=np.float32)
    quantized = np.empty_like(array, dtype=np.int8)

    for row in range(rows):
        for group in range(groups):
            start = group * group_size
            end = min(start + group_size, cols)
            block = array[row, start:end]
            max_abs = float(np.max(np.abs(block))) if block.size else 0.0
            scale = max_abs / 7.0 if max_abs > 0.0 else 1.0
            scales[row, group] = scale
            quantized[row, start:end] = np.clip(np.rint(block / scale), -8, 7).astype(np.int8)

    return pack_int4(quantized), scales


def _decode_signed_nibble(values: np.ndarray) -> np.ndarray:
    decoded = values.astype(np.int8)
    decoded[decoded >= 8] -= 16
    return decoded

