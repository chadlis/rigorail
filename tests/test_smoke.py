import rigorail


def test_version_is_exposed():
    assert isinstance(rigorail.__version__, str)
    assert rigorail.__version__
