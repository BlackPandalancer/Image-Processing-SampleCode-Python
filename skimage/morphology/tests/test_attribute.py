import math
import unittest

import numpy as np
from skimage.morphology import attribute
from skimage.morphology import extrema
from skimage.measure import label
from scipy import ndimage as ndi

import skimage.io
import time

eps = 1e-12


def diff(a, b):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    t = ((a - b)**2).sum()
    return math.sqrt(t)

def _full_type_test(img, param, expected, func, param_scale=False):

    # images as they are
    out = func(img, param)
    error = diff(out, expected)
    if error > eps:
        pdb.set_trace()
    assert error < eps

    # unsigned int
    for dt in [np.uint32, np.uint64]: 
        img_cast = img.astype(dt)
        out = func(img_cast, param)
        exp_cast = expected.astype(dt)
        error = diff(out, exp_cast)
        assert error < eps

    # float
    data_float = img.astype(np.float64)
    data_float = data_float / 255.0
    expected_float = expected.astype(np.float64)
    expected_float = expected_float / 255.0
    if param_scale:
        param_cast = param / 255.0
    else:
        param_cast = param
    for dt in [np.float32, np.float64]: 
        data_cast = data_float.astype(dt)
        out = func(data_cast, param_cast)
        exp_cast = expected_float.astype(dt)
        error_img = 255.0 * exp_cast - 255.0 * out
        error = (error_img >= 1.0).sum()
        assert error < eps

    # signed images
    img_signed = img.astype(np.int16)
    img_signed = img_signed - 128
    exp_signed = expected.astype(np.int16)
    exp_signed = exp_signed - 128
    for dt in [np.int8, np.int16, np.int32, np.int64]:
        img_s = img_signed.astype(dt)
        out = func(img_s, param)
        exp_s = exp_signed.astype(dt)
        error = diff(out, exp_s)
        assert error < eps


class TestExtrema(unittest.TestCase):

    def test_diameter_closing(self):
        "Test for Diameter Closing (2 diameters, all types)"

        # original image
        img = np.array(
            [[240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240],
             [240, 200, 200, 240, 200, 240, 200, 200, 240, 240, 200, 240],
             [240, 200,  40, 240, 240, 240, 240, 240, 240, 240,  40, 240],
             [240, 240, 240, 240, 100, 240, 100, 100, 240, 240, 200, 240],
             [240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240],
             [200, 200, 200, 200, 200, 200, 200, 240, 200, 200, 255, 255],
             [200, 255, 200, 200, 200, 255, 200, 240, 255, 255, 255,  40],
             [200, 200, 200, 100, 200, 200, 200, 240, 255, 255, 255, 255],
             [200, 200, 200, 100, 200, 200, 200, 240, 200, 200, 255, 255],
             [200, 200, 200, 200, 200,  40, 200, 240, 240, 100, 255, 255],
             [200,  40, 255, 255, 255,  40, 200, 255, 200, 200, 255, 255],
             [200, 200, 200, 200, 200, 200, 200, 255, 255, 255, 255, 255]], 
            dtype=np.uint8)

        # expected diameter closing with diameter 2
        expected_2 = np.array(
            [[240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240],
             [240, 200, 200, 240, 240, 240, 200, 200, 240, 240, 200, 240],
             [240, 200, 200, 240, 240, 240, 240, 240, 240, 240, 200, 240],
             [240, 240, 240, 240, 240, 240, 100, 100, 240, 240, 200, 240],
             [240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240],
             [200, 200, 200, 200, 200, 200, 200, 240, 200, 200, 255, 255],
             [200, 255, 200, 200, 200, 255, 200, 240, 255, 255, 255, 255],
             [200, 200, 200, 100, 200, 200, 200, 240, 255, 255, 255, 255],
             [200, 200, 200, 100, 200, 200, 200, 240, 200, 200, 255, 255],
             [200, 200, 200, 200, 200,  40, 200, 240, 240, 200, 255, 255],
             [200, 200, 255, 255, 255,  40, 200, 255, 200, 200, 255, 255],
             [200, 200, 200, 200, 200, 200, 200, 255, 255, 255, 255, 255]], 
            dtype=np.uint8)

        # expected diameter closing with diameter 3
        expected_3 = np.array(
            [[240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240],
             [240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 200, 240],
             [240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 200, 240],
             [240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 200, 240],
             [240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240],
             [200, 200, 200, 200, 200, 200, 200, 240, 240, 240, 255, 255],
             [200, 255, 200, 200, 200, 255, 200, 240, 255, 255, 255, 255],
             [200, 200, 200, 200, 200, 200, 200, 240, 255, 255, 255, 255],
             [200, 200, 200, 200, 200, 200, 200, 240, 200, 200, 255, 255],
             [200, 200, 200, 200, 200, 200, 200, 240, 240, 200, 255, 255],
             [200, 200, 255, 255, 255, 200, 200, 255, 200, 200, 255, 255],
             [200, 200, 200, 200, 200, 200, 200, 255, 255, 255, 255, 255]], 
            dtype=np.uint8)

        # _full_type_test makes a test with many image types.
        _full_type_test(img, 2, expected_2, attribute.diameter_closing)
        _full_type_test(img, 3, expected_3, attribute.diameter_closing)


    def test_area_closing(self):
        "Test for Area Closing (2 diameters, all types)"

        # original image
        img = np.array(
            [[240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240],
             [240, 200, 200, 240, 200, 240, 200, 200, 240, 240, 200, 240],
             [240, 200,  40, 240, 240, 240, 240, 240, 240, 240,  40, 240],
             [240, 240, 240, 240, 100, 240, 100, 100, 240, 240, 200, 240],
             [240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240],
             [200, 200, 200, 200, 200, 200, 200, 240, 200, 200, 255, 255],
             [200, 255, 200, 200, 200, 255, 200, 240, 255, 255, 255,  40],
             [200, 200, 200, 100, 200, 200, 200, 240, 255, 255, 255, 255],
             [200, 200, 200, 100, 200, 200, 200, 240, 200, 200, 255, 255],
             [200, 200, 200, 200, 200,  40, 200, 240, 240, 100, 255, 255],
             [200,  40, 255, 255, 255,  40, 200, 255, 200, 200, 255, 255],
             [200, 200, 200, 200, 200, 200, 200, 255, 255, 255, 255, 255]], 
            dtype=np.uint8)

        # expected area closing with area 2
        expected_2 = np.array(
            [[240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240],
             [240, 200, 200, 240, 240, 240, 200, 200, 240, 240, 200, 240],
             [240, 200, 200, 240, 240, 240, 240, 240, 240, 240, 200, 240],
             [240, 240, 240, 240, 240, 240, 100, 100, 240, 240, 200, 240],
             [240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240],
             [200, 200, 200, 200, 200, 200, 200, 240, 200, 200, 255, 255],
             [200, 255, 200, 200, 200, 255, 200, 240, 255, 255, 255, 255],
             [200, 200, 200, 100, 200, 200, 200, 240, 255, 255, 255, 255],
             [200, 200, 200, 100, 200, 200, 200, 240, 200, 200, 255, 255],
             [200, 200, 200, 200, 200,  40, 200, 240, 240, 200, 255, 255],
             [200, 200, 255, 255, 255,  40, 200, 255, 200, 200, 255, 255],
             [200, 200, 200, 200, 200, 200, 200, 255, 255, 255, 255, 255]],
            dtype=np.uint8)

        # expected diameter closing with diameter 4
        expected_4 = np.array(
            [[240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240],
             [240, 200, 200, 240, 240, 240, 240, 240, 240, 240, 240, 240],
             [240, 200, 200, 240, 240, 240, 240, 240, 240, 240, 240, 240],
             [240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240],
             [240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240],
             [200, 200, 200, 200, 200, 200, 200, 240, 240, 240, 255, 255],
             [200, 255, 200, 200, 200, 255, 200, 240, 255, 255, 255, 255],
             [200, 200, 200, 200, 200, 200, 200, 240, 255, 255, 255, 255],
             [200, 200, 200, 200, 200, 200, 200, 240, 200, 200, 255, 255],
             [200, 200, 200, 200, 200, 200, 200, 240, 240, 200, 255, 255],
             [200, 200, 255, 255, 255, 200, 200, 255, 200, 200, 255, 255],
             [200, 200, 200, 200, 200, 200, 200, 255, 255, 255, 255, 255]], 
            dtype=np.uint8)

        # _full_type_test makes a test with many image types.
        _full_type_test(img, 2, expected_2, attribute.area_closing)
        _full_type_test(img, 4, expected_4, attribute.area_closing)


    def test_volume_fill(self):

        # original image
        img = np.array(
            [[240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240],
             [240, 200, 200, 240, 200, 240, 200, 200, 240, 240, 200, 240],
             [240, 200,  40, 240, 240, 240, 240, 240, 240, 240,  40, 240],
             [240, 240, 240, 240, 100, 240, 100, 100, 240, 240, 200, 240],
             [240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240],
             [200, 200, 200, 200, 200, 200, 200, 240, 200, 200, 255, 255],
             [200, 255, 200, 200, 200, 255, 200, 240, 255, 255, 255,  40],
             [200, 200, 200, 100, 200, 200, 200, 240, 255, 255, 255, 255],
             [200, 200, 200, 100, 200, 200, 200, 240, 200, 200, 255, 255],
             [200, 200, 200, 200, 200,  40, 200, 240, 240, 100, 255, 255],
             [200,  40, 255, 255, 255,  40, 200, 255, 200, 200, 255, 255],
             [200, 200, 200, 200, 200, 200, 200, 255, 255, 255, 255, 255]], 
            dtype=np.uint8)

        # expected volume filling with area 80
        expected_80 = np.array(
            [[240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240],
             [240, 200, 200, 240, 240, 240, 240, 240, 240, 240, 200, 240],
             [240, 200, 120, 240, 240, 240, 240, 240, 240, 240, 120, 240],
             [240, 240, 240, 240, 180, 240, 140, 140, 240, 240, 200, 240],
             [240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240],
             [200, 200, 200, 200, 200, 200, 200, 240, 240, 240, 255, 255],
             [200, 255, 200, 200, 200, 255, 200, 240, 255, 255, 255, 120],
             [200, 200, 200, 140, 200, 200, 200, 240, 255, 255, 255, 255],
             [200, 200, 200, 140, 200, 200, 200, 240, 200, 200, 255, 255],
             [200, 200, 200, 200, 200,  80, 200, 240, 240, 180, 255, 255],
             [200, 120, 255, 255, 255,  80, 200, 255, 200, 200, 255, 255],
             [200, 200, 200, 200, 200, 200, 200, 255, 255, 255, 255, 255]], 
            dtype=np.uint8)

        # expected volume filling with area 201
        expected_201 = np.array(
            [[240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240],
             [240, 211, 211, 240, 240, 240, 240, 240, 240, 240, 214, 240],
             [240, 211, 211, 240, 240, 240, 240, 240, 240, 240, 214, 240],
             [240, 240, 240, 240, 240, 240, 201, 201, 240, 240, 214, 240],
             [240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240],
             [200, 200, 200, 200, 200, 200, 200, 240, 240, 240, 255, 255],
             [200, 255, 200, 200, 200, 255, 200, 240, 255, 255, 255, 241],
             [200, 200, 200, 200, 200, 200, 200, 240, 255, 255, 255, 255],
             [200, 200, 200, 200, 200, 200, 200, 240, 221, 221, 255, 255],
             [200, 200, 200, 200, 200, 141, 200, 240, 240, 221, 255, 255],
             [200, 200, 255, 255, 255, 141, 200, 255, 221, 221, 255, 255],
             [200, 200, 200, 200, 200, 200, 200, 255, 255, 255, 255, 255]], 
            dtype=np.uint8)

        # _full_type_test makes a test with many image types.
        _full_type_test(img, 80, expected_80, attribute.volume_fill, param_scale=True)
        _full_type_test(img, 201, expected_201, attribute.volume_fill, param_scale=True)


if __name__ == "__main__":
    np.testing.run_module_suite()
