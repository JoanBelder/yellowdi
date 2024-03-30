from yellowdi import Container, yellowdi


def test_yellowdi_is_the_default_container():
    assert isinstance(yellowdi, Container)
