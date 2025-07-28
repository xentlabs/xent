# pyright: reportUnusedExpression=false
import pytest

from xega.common.errors import XegaTypeError
from xega.common.x_string import XString


def test_constructor_and_representation():
    s1 = XString("test")
    assert s1.primary_string == "test"
    assert s1.prefix == ""
    assert str(s1) == "test"
    assert "XString('test'" in repr(s1)

    s2 = XString(s1)
    assert s2.primary_string == s1

    with pytest.raises(XegaTypeError):
        XString(123)  # type: ignore


def test_prefix_decorator():
    s1 = XString("LeftOperand")
    s2 = XString("RightPrefix")
    original_s1_primary = s1.primary_string
    original_s1_prefix = s1.prefix
    original_s2_primary = s2.primary_string
    original_s2_prefix = s2.prefix

    result = s1 | s2

    assert isinstance(result, XString)
    assert result.primary_string == "LeftOperand"
    assert result.prefix == "RightPrefix"
    assert "'LeftOperand'" in repr(result)
    assert "prefix='RightPrefix'" in repr(result)

    assert s1.primary_string == original_s1_primary
    assert s1.prefix == original_s1_prefix
    assert s2.primary_string == original_s2_primary
    assert s2.prefix == original_s2_prefix

    # Test with raw strings
    xs = XString("test")
    raw_string = "raw_string"

    result = xs | raw_string
    assert isinstance(result, XString)
    assert result.primary_string == "test"
    assert result.prefix == "raw_string"

    result = raw_string | xs
    assert isinstance(result, XString)
    assert result.primary_string == "raw_string"
    assert result.prefix == "test"
    # Test with invalid types
    with pytest.raises(XegaTypeError):
        s1 | 123
    with pytest.raises(XegaTypeError):
        123 | s1


def test_operator_cat():
    s1 = XString("Hello")
    s2 = XString("World")
    s_empty = XString("")

    result1 = s1 + s2
    assert isinstance(result1, XString)
    assert result1.primary_string == "HelloWorld"

    result2 = s1 + s_empty
    assert isinstance(result2, XString)
    assert result2.primary_string == "Hello"

    # Test cat with raw strings
    assert s1 + "World" == XString("HelloWorld")
    assert s1 + "" == XString("Hello")
    assert "Hello" + s2 == XString("HelloWorld")
    assert "" + s2 == XString("World")
    assert s_empty + s1 == XString("Hello")
    assert "Hello" + s_empty + "World" == XString("HelloWorld")
    assert "Hello" + s2 + "Hello" == XString("HelloWorldHello")

    # Test with invalid types
    with pytest.raises(XegaTypeError):
        s1 + 123
    with pytest.raises(XegaTypeError):
        123 + s1


def test_operator_cut_front():
    """Tests the '//' operator."""
    s_main = XString("HelloWorldAgain")
    s_world = XString("World")
    s_hello = XString("Hello")
    s_again = XString("Again")
    s_notfound = XString("XYZ")
    s_empty = XString("")
    s_double = XString("abcabc")
    s_b = XString("b")

    res1 = s_main // s_world
    assert isinstance(res1, XString)
    assert res1.primary_string == "Hello"

    res2 = s_main // s_hello
    assert isinstance(res2, XString)
    assert res2.primary_string == ""

    res3 = s_main // s_notfound
    assert isinstance(res3, XString)
    assert res3.primary_string == "HelloWorldAgain"

    res4 = s_main // s_empty
    assert isinstance(res4, XString)
    assert res4.primary_string == "HelloWorldAgain"

    res5 = s_double // s_b
    assert isinstance(res5, XString)
    assert res5.primary_string == "a"

    res6 = s_main // s_again
    assert isinstance(res6, XString)
    assert res6.primary_string == "HelloWorld"

    # Test with raw strings
    xs = XString("hello world")

    result = xs // "world"
    assert isinstance(result, XString)
    assert result.primary_string == "hello "

    result = "before hello world" // xs
    assert isinstance(result, XString)
    assert result.primary_string == "before "

    # Test with invalid types
    with pytest.raises(XegaTypeError):
        xs // 123
    with pytest.raises(XegaTypeError):
        123 // xs


def test_operator_cut_back():
    s_main = XString("HelloWorldAgain")
    s_world = XString("World")
    s_hello = XString("Hello")
    s_again = XString("Again")
    s_notfound = XString("XYZ")
    s_empty = XString("")
    s_double = XString("abcabc")
    s_b = XString("b")

    res1 = s_main % s_hello
    assert isinstance(res1, XString)
    assert res1.primary_string == "WorldAgain"

    res2 = s_main % s_again
    assert isinstance(res2, XString)
    assert res2.primary_string == ""

    res3 = s_main % s_notfound
    assert isinstance(res3, XString)
    assert res3.primary_string == ""

    res4 = s_main % s_empty
    assert isinstance(res4, XString)
    assert res4.primary_string == ""

    res5 = s_double % s_b
    assert isinstance(res5, XString)
    assert res5.primary_string == "cabc"

    res6 = s_main % s_world
    assert isinstance(res6, XString)
    assert res6.primary_string == "Again"

    # Test with raw strings
    xs = XString("hello world")

    result = xs % "hello"
    assert isinstance(result, XString)
    assert result.primary_string == " world"

    # NB: this is because strings already have a % operator defined.
    # Its possible to handle this by monkey patching the string class,
    # but it would be better to avoid this situation by being more
    # careful wrapping all strings in XString.
    with pytest.raises(TypeError):
        "hello world after" % xs  # noqa: UP031

    # Test with invalid types
    with pytest.raises(XegaTypeError):
        xs % 123
    with pytest.raises(XegaTypeError):
        123 % xs


def test_equality_and_inequality():
    s_abc1 = XString("abc")
    s_abc2 = XString("abc")
    s_def = XString("def")

    assert s_abc1 == s_abc2
    assert s_abc1 != s_def
    assert s_abc1 == "abc"
    assert s_abc1 == "abc"  # Test reversed comparison
    assert s_abc1 != "def"
    assert s_abc1 != "def"  # Test reversed comparison
    assert s_abc1 != 123  # Should be False due to NotImplemented
    assert s_abc1 != 123  # Should be False

    assert s_abc1 != s_def
    assert s_abc1 == s_abc2
    assert s_abc1 != "def"
    assert s_abc1 != "def"  # Test reversed comparison
    assert s_abc1 == "abc"
    assert s_abc1 == "abc"  # Test reversed comparison
    assert s_abc1 != 123  # Should be True due to NotImplemented
    assert s_abc1 != 123  # Should be True


def test_constructor_with_optional_params():
    """Tests XString constructor with optional parameters."""
    s1 = XString("test", static=True, public=True, name="test_name")
    assert s1.primary_string == "test"
    assert s1.static is True
    assert s1.public is True
    assert s1.name == "test_name"
    assert s1.prefix == ""

    s2 = XString("hello", static=False, public=True)
    assert s2.primary_string == "hello"
    assert s2.static is False
    assert s2.public is True
    assert s2.name is None

    s3 = XString("default")
    assert s3.primary_string == "default"
    assert s3.static is False
    assert s3.public is False
    assert s3.name is None


def test_len_method():
    s1 = XString("hello")
    assert len(s1) == 5

    s2 = XString("")
    assert len(s2) == 0

    s3 = XString("hello world!")
    assert len(s3) == 12

    s4 = XString("test") | XString("prefix")
    assert len(s4) == 4  # Should return length of primary_string, not prefix


def test_empty_string_operations():
    s_empty = XString("")
    s_hello = XString("hello")

    assert len(s_empty) == 0

    result1 = s_empty + s_empty
    assert result1.primary_string == ""

    result2 = s_empty + s_hello
    assert result2.primary_string == "hello"

    result3 = s_hello + s_empty
    assert result3.primary_string == "hello"

    result4 = s_empty | s_hello
    assert result4.primary_string == ""
    assert result4.prefix == "hello"

    result5 = s_hello | s_empty
    assert result5.primary_string == "hello"
    assert result5.prefix == ""

    s_empty2 = XString("")
    assert s_empty == s_empty2
    assert s_empty == ""
    assert s_empty != "hello"
    assert s_empty != s_hello
