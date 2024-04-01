import pickle

from yellowdi import Token


def test_anonymous_tokens_always_different():
    assert Token() is not Token()


def test_named_tokens_are_not_the_same():
    assert Token("A") is not Token("B")


def test_repeated_name_tokens_are_the_same_with_constructor():
    assert Token("A") is Token("A")
    assert Token("B") is Token("B")


def test_repeated_name_tokens_are_the_same_with_accessor():
    assert Token["A"] is Token["A"]
    assert Token["B"] is Token["B"]


def test_can_mix_styles_of_tokens():
    assert Token["A"] is Token("A")
    assert Token("B") is Token["B"]


def test_same_instances_survives_pickling():
    token = Token("A")
    assert pickle.loads(pickle.dumps(token)) is token
