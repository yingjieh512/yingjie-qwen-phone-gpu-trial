import numpy as np

from qpnpu.quant import pack_int4, symmetric_int4_quantize, unpack_int4


def test_pack_unpack_roundtrip_for_all_int4_values() -> None:
    values = np.arange(-8, 8, dtype=np.int8)
    packed = pack_int4(values)
    unpacked = unpack_int4(packed, count=values.size)
    np.testing.assert_array_equal(unpacked, values)


def test_quantize_small_2d_matrix_shapes() -> None:
    matrix = np.array(
        [
            [-1.0, -0.5, 0.0, 0.5, 1.0],
            [2.0, 1.0, 0.0, -1.0, -2.0],
        ],
        dtype=np.float32,
    )
    packed, scales = symmetric_int4_quantize(matrix, group_size=3)
    assert packed.dtype == np.uint8
    assert packed.shape == (5,)
    assert scales.shape == (2, 2)
    assert np.all(scales > 0)

