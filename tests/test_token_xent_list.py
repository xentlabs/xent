# pyright: reportUnusedExpression=false

import pytest

from xega.common.token_xent_list import TokenXentList, ValidatedBool


def test_basic_arithmetic():
    """Test basic arithmetic operations with compatible TokenXentList objects."""
    # Create test instances
    list0 = TokenXentList([("a", 1.0), ("b", 2.0), ("c", 3.0)])
    list1 = TokenXentList([("a", 2.0), ("b", 3.0), ("c", 4.0)])

    # Test addition
    result = list0 + list1
    expected = 15.0  # (1+2) + (2+3) + (3+4) = 3 + 5 + 7 = 15
    assert result.total_xent() == expected

    # Test subtraction
    result = list1 - list0
    expected = 3.0  # (2-1) + (3-2) + (4-3) = 1 + 1 + 1 = 3
    assert result.total_xent() == expected

    # Test multiplication (should raise TypeError)
    with pytest.raises(TypeError):
        result = list0 * list1

    # Test division (should raise TypeError)
    with pytest.raises(TypeError):
        result = list0 / list1

    # Test negation
    result = -list0
    expected = -6.0  # -(1 + 2 + 3) = -6
    assert result.total_xent() == expected


def test_no_scalar_operations():
    """Test operations between TokenXentList and scalar values."""
    # Create test instance
    list0 = TokenXentList([("a", 1.0), ("b", 2.0), ("c", 3.0)])

    # Test scalar addition
    with pytest.raises(TypeError):
        list0 + 5

    # Test scalar subtraction
    with pytest.raises(TypeError):
        list0 - 2

    # Test scalar multiplication
    with pytest.raises(TypeError):
        list0 * 2

    # Test scalar division
    with pytest.raises(TypeError):
        list0 / 2

    # Test right-hand scalar operations
    with pytest.raises(TypeError):
        10 + list0

    with pytest.raises(TypeError):
        10 - list0

    # Test right-hand scalar multiplication
    with pytest.raises(TypeError):
        10 * list0

    # Test left-hand scalar division
    with pytest.raises(TypeError):
        list0 / 10


def test_type_preservation():
    """Test that all operations preserve the TokenXentList type."""
    # Create test instances
    list0 = TokenXentList([("a", 1.0), ("b", 2.0), ("c", 3.0)])
    list1 = TokenXentList([("a", 2.0), ("b", 3.0), ("c", 4.0)])

    # Operations that should return TokenXentList
    operations = [
        list0 + list1,
        list0 - list1,
        -list0,
        +list0,
    ]

    for i, op_result in enumerate(operations):
        assert isinstance(
            op_result, TokenXentList
        ), f"Operation {i} returned {type(op_result)} instead of TokenXentList"


def test_comparison_operations():
    """Test comparison operations between TokenXentList objects."""
    list1 = TokenXentList([("a", 1.0), ("b", 2.0)])  # total = 3.0
    list2 = TokenXentList([("x", 0.5), ("y", 2.5)])  # total = 3.0
    list3 = TokenXentList([("p", 2.0), ("q", 3.0)])  # total = 5.0

    # Test equality
    result = list1 == list2
    assert isinstance(result, ValidatedBool)
    assert bool(result) is True

    result = list1 == list3
    assert isinstance(result, ValidatedBool)
    assert bool(result) is False

    # Test inequality
    result = list1 != list3
    assert isinstance(result, ValidatedBool)
    assert bool(result) is True

    # Test less than
    result = list1 < list3
    assert isinstance(result, ValidatedBool)
    assert bool(result) is True

    result = list3 < list1
    assert isinstance(result, ValidatedBool)
    assert bool(result) is False

    # Test less than or equal
    result = list1 <= list2
    assert isinstance(result, ValidatedBool)
    assert bool(result) is True

    result = list1 <= list3
    assert isinstance(result, ValidatedBool)
    assert bool(result) is True

    # Test greater than
    result = list3 > list1
    assert isinstance(result, ValidatedBool)
    assert bool(result) is True

    # Test greater than or equal
    result = list3 >= list1
    assert isinstance(result, ValidatedBool)
    assert bool(result) is True

    result = list1 >= list2
    assert isinstance(result, ValidatedBool)
    assert bool(result) is True


def test_comparison_with_scalars():
    """Test comparison operations between TokenXentList and scalar values."""
    list1 = TokenXentList([("a", 1.0), ("b", 2.0)])  # total = 3.0

    # Test comparisons with scalars
    assert (list1 < 5) is True
    assert (list1 < 2) is False
    assert (list1 <= 3) is True
    assert (list1 > 2) is True
    assert (list1 > 4) is False
    assert (list1 >= 3) is True

    # Note: == and != with scalars return NotImplemented


def test_validated_bool():
    """Test ValidatedBool class functionality."""
    vb_true = ValidatedBool(True)
    vb_false = ValidatedBool(False)

    # Test bool conversion
    assert bool(vb_true) is True
    assert bool(vb_false) is False

    # Test AND operations
    result = vb_true & vb_true
    assert isinstance(result, ValidatedBool)
    assert bool(result) is True

    result = vb_true & vb_false
    assert isinstance(result, ValidatedBool)
    assert bool(result) is False

    # Test OR operations
    result = vb_true | vb_false
    assert isinstance(result, ValidatedBool)
    assert bool(result) is True

    result = vb_false | vb_false
    assert isinstance(result, ValidatedBool)
    assert bool(result) is False

    # Test NOT operation
    result = ~vb_true
    assert isinstance(result, ValidatedBool)
    assert bool(result) is False

    result = ~vb_false
    assert isinstance(result, ValidatedBool)
    assert bool(result) is True

    # Test with regular bool
    assert (vb_true & True) is True
    assert (vb_false | True) is True

    # Test repr
    assert repr(vb_true) == "ValidatedBool(value=True)"
    assert repr(vb_false) == "ValidatedBool(value=False)"


def test_incompatible_operations():
    """Test operations between incompatible TokenXentList objects."""
    list1 = TokenXentList([("a", 1.0), ("b", 2.0)])
    list2 = TokenXentList([("x", 3.0), ("y", 4.0)])  # different tokens
    list3 = TokenXentList([("a", 1.0)])  # different length

    # Addition of incompatible lists fails
    with pytest.raises(TypeError):
        list1 + list2

    # Subtraction of incompatible lists
    with pytest.raises(TypeError):
        list1 - list2

    # Test with different lengths
    with pytest.raises(TypeError):
        list1 + list3


def test_special_multiplication_rules():
    """Test that multiplication only works with -1 and 1."""
    list1 = TokenXentList([("a", 2.0), ("b", 3.0)])

    # Test allowed multiplications
    result = list1 * 1
    assert result.total_xent() == list1.total_xent()

    result = list1 * -1
    assert result.total_xent() == -list1.total_xent()

    result = 1 * list1
    assert result.total_xent() == list1.total_xent()

    result = -1 * list1
    assert result.total_xent() == -list1.total_xent()

    # Test disallowed multiplications
    with pytest.raises(TypeError):
        list1 * 2

    with pytest.raises(TypeError):
        list1 * 0.5

    with pytest.raises(TypeError):
        2 * list1

    with pytest.raises(TypeError):
        list1 * 1.1  # Close to 1 but not exactly


def test_repr_and_str():
    """Test __repr__ and __str__ methods."""
    list1 = TokenXentList([("hello", 1.234567), ("world", 2.987654)])

    # Test __str__ - should round to integer values
    str_rep = str(list1)
    assert str_rep == "hello|1 world|3"

    # Test __repr__
    repr_str = repr(list1)
    assert "TokenXentList" in repr_str
    assert "scale=1.0" in repr_str
    assert "hello" in repr_str
    assert "world" in repr_str


def test_edge_cases():
    """Test edge cases like empty lists and single elements."""
    # Empty list
    empty = TokenXentList([])
    assert empty.total_xent() == 0.0
    assert str(empty) == ""

    # Single element
    single = TokenXentList([("only", 5.0)])
    assert single.total_xent() == 5.0

    # Operations on empty lists
    with pytest.raises(TypeError):
        empty + 10

    result = empty + empty
    assert result.total_xent() == 0.0

    # Test _apply_scale with empty list
    scaled_empty = TokenXentList([], scale=2.0)
    assert scaled_empty.total_xent() == 0.0


def test_unary_pos():
    """Test unary positive operator."""
    list1 = TokenXentList([("a", 1.0), ("b", 2.0)])

    # Unary positive should return the same object
    result = +list1
    assert result is list1
    assert result.total_xent() == list1.total_xent()


def test_scale_behavior():
    """Test behavior of scale parameter."""
    # Create with scale
    list1 = TokenXentList([("a", 1.0), ("b", 2.0)], scale=-1.0)
    assert list1.total_xent() == -1.0 * (1.0 + 2.0)

    # Test that operations preserve scale correctly
    list2 = TokenXentList([("a", 0.5), ("b", 1.5)])

    # Adding compatible lists applies scale
    result = list1 + list2
    normalized1 = list1._apply_scale()
    normalized2 = list2._apply_scale()
    expected = normalized1.total_xent() + normalized2.total_xent()
    assert abs(result.total_xent() - expected) < 0.01
