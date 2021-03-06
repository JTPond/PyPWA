import pytest
import PyPWA.data.memory_wrapper
import numpy
import os

TEMP_KV_FILE = os.path.join(os.path.dirname(__file__), "memory/test_docs/kv_test_data_tmp.txt")
TEMP_KV_FLOAT_FILE = os.path.join(os.path.dirname(__file__), "memory/test_docs/kv_floats_test_data.txt")
TEMP_KV_BOOL_FILE = os.path.join(os.path.dirname(__file__), "memory/test_docs/kv_bool_test_data.txt")


def test_abstract_methods():
    abstract = PyPWA.data.memory_wrapper.DataInterface()
    with pytest.raises(NotImplementedError):
        abstract.parse(TEMP_KV_FILE)
    with pytest.raises(NotImplementedError):
        abstract.write(TEMP_KV_FILE, [12])
    with pytest.raises(NotImplementedError):
        PyPWA.data.memory_wrapper.DataInterface.parse(TEMP_KV_FILE)
    with pytest.raises(NotImplementedError):
        PyPWA.data.memory_wrapper.DataInterface.write(TEMP_KV_FILE, [12])


def test_kv_interface():
    data = {"something": numpy.random.rand(50), "to": numpy.random.rand(50), "write": numpy.random.rand(50)}

    kv_interface = PyPWA.data.memory_wrapper.Kv()
    kv_interface.write(TEMP_KV_FILE, data)
    read = kv_interface.parse(TEMP_KV_FILE)

    numpy.testing.assert_array_almost_equal(data["something"], read["something"])
    os.remove(TEMP_KV_FILE)

    read_float = kv_interface.parse(TEMP_KV_FLOAT_FILE)
    assert read_float[5] == 0.888493, "Expecting 0.888493, got {0} instead!".format(read_float[5])

    read_bool = kv_interface.parse(TEMP_KV_BOOL_FILE)

    assert read_bool[2] == False, "Expecting False, got {0} instead!".format(read_bool[2])
