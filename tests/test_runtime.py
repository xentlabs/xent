# pyright: reportUnusedExpression=false

import pytest

from xent.benchmark.run_benchmark import extract_token_usage
from xent.common.configuration_types import (
    ExecutableGameMap,
    GameMapConfig,
)
from xent.common.errors import XentConfigurationError, XentInternalError, XentTypeError
from xent.common.token_xent_list import TokenXentList, ValidatedBool
from xent.common.version import get_xent_version, validate_version
from xent.common.x_list import XList
from xent.common.x_string import XString
from xent.common.xent_event import (
    ElicitRequestEvent,
    ElicitResponseEvent,
    FailedEnsureEvent,
    RevealEvent,
    RewardEvent,
    XentEvent,
)
from xent.presentation.executor import (
    SAMPLE_METADATA,
    PresentationFunction,
    get_default_presentation,
)
from xent.presentation.sdk import (
    format_elicit_request,
    format_elicit_response,
    format_failed_ensure,
    format_registers_display,
    format_reveal,
    format_reward,
    get_current_registers,
    get_event_summary,
)
from xent.runtime.execution import eval_line, play_game
from xent.runtime.judge import Judge
from xent.runtime.players.default_players import DefaultXGP, MockXGP
from xent.runtime.runtime import XentRuntime
from xent.runtime.variables import build_globals, build_locals


class TestXString:
    """Tests for XString class functionality."""

    def test_constructor_comprehensive(self):
        """Test XString constructor with various parameters and representations."""
        # Basic constructor
        s1 = XString("test")
        assert s1.primary_string == "test"
        assert s1.prefix == ""
        assert str(s1) == "test"
        assert "XString('test'" in repr(s1)

        # Constructor with XString input
        s2 = XString(s1)
        assert s2.primary_string == s1

        # Constructor with optional parameters
        s3 = XString("test", static=True, public=True, name="test_name")
        assert s3.primary_string == "test"
        assert s3.static is True
        assert s3.public is True
        assert s3.name == "test_name"
        assert s3.prefix == ""

        s4 = XString("hello", static=False, public=True)
        assert s4.primary_string == "hello"
        assert s4.static is False
        assert s4.public is True
        assert s4.name is None

        s5 = XString("default")
        assert s5.primary_string == "default"
        assert s5.static is False
        assert s5.public is False
        assert s5.name is None

        # Invalid type
        with pytest.raises(XentTypeError):
            XString(123)  # type: ignore[arg-type]

    def test_prefix_decorator(self):
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
        with pytest.raises(XentTypeError):
            s1 | 123
        with pytest.raises(XentTypeError):
            123 | s1

    def test_operator_cat(self):
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
        with pytest.raises(XentTypeError):
            s1 + 123
        with pytest.raises(XentTypeError):
            123 + s1

    def test_join_with_xlist(self):
        separator = XString(",") | XString("ignored_prefix")
        item_a = XString("alpha") | XString("p1")
        item_b = XString("beta") | XString("p2")
        item_c = XString("gamma")
        items = XList([item_a, item_b, item_c])

        result = separator.join(items)

        assert isinstance(result, XString)
        assert result.primary_string == "alpha,beta,gamma"
        assert result.prefix == ""
        # Ensure original prefixes remain untouched
        assert separator.prefix == "ignored_prefix"
        assert item_a.prefix == "p1"
        assert item_b.prefix == "p2"
        assert item_c.prefix == ""

    def test_join_rejects_invalid_inputs(self):
        separator = XString(",")
        with pytest.raises(XentTypeError):
            separator.join([XString("alpha")])  # type: ignore[arg-type]

        items = XList([XString("alpha")])
        items.items.append("beta")  # type: ignore[arg-type]
        with pytest.raises(XentTypeError):
            separator.join(items)

    def test_split_with_separator_and_prefix_handling(self):
        source = XString("alpha::beta::gamma") | XString("src_prefix")
        parts = source.split(XString("::"))

        assert isinstance(parts, XList)
        extracted = [part.primary_string for part in parts]
        assert extracted == ["alpha", "beta", "gamma"]
        assert all(part.prefix == "" for part in parts)
        assert source.prefix == "src_prefix"

    def test_split_whitespace(self):
        source = XString("  one   two three   four  ")
        parts_all = source.split()
        assert [part.primary_string for part in parts_all] == [
            "one",
            "two",
            "three",
            "four",
        ]

    def test_operator_cut_front(self):
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
        with pytest.raises(XentTypeError):
            xs // 123
        with pytest.raises(XentTypeError):
            123 // xs

    def test_operator_cut_back(self):
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
            "hello world after" % xs  # type: ignore[str-format]  # noqa: UP031

        # Test with invalid types
        with pytest.raises(XentTypeError):
            xs % 123
        with pytest.raises(XentTypeError):
            123 % xs

    def test_equality_and_inequality(self):
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

    def test_len_method(self):
        s1 = XString("hello")
        assert len(s1) == 5

        s2 = XString("")
        assert len(s2) == 0

        s3 = XString("hello world!")
        assert len(s3) == 12

        s4 = XString("test") | XString("prefix")
        assert len(s4) == 4  # Should return length of primary_string, not prefix

    def test_empty_string(self):
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


class TestXList:
    """Unit tests for XList behavior."""

    def test_constructor_and_repr(self):
        # Default constructor
        l0 = XList()
        assert isinstance(l0, XList)
        assert len(l0) == 0
        assert l0.static is False
        assert l0.public is False
        assert l0.name is None
        assert "XList(items=[" in repr(l0)

        # Pre-populated with flags
        items = [XString("a"), XString("b")]
        l1 = XList(items=items, static=True, public=True, name="l")
        assert len(l1) == 2
        assert l1.static is True
        assert l1.public is True
        assert l1.name == "l"
        r = repr(l1)
        assert "static=True" in r and "public=True" in r and "name='l'" in r

    def test_equality_and_inequality(self):
        l1 = XList([XString("a"), XString("b")])
        l2 = XList([XString("a"), XString("b")])
        l3 = XList([XString("a"), XString("c")])

        assert l1 == l2
        assert l1 != l3

    def test_iteration_yields_xstrings(self):
        elements = [XString("alpha"), XString("beta")]
        xlist = XList(elements)

        collected = list(xlist)

        assert len(collected) == 2
        assert all(isinstance(item, XString) for item in collected)
        assert [item.primary_string for item in collected] == ["alpha", "beta"]

    def test_add_concatenates_and_type_checks(self):
        left = XList([XString("a")], static=False, public=True, name="l")
        right = XList([XString("b"), XString("c")])

        result = left + right
        assert isinstance(result, XList)
        assert len(result) == 3
        # Left metadata is propagated
        assert result.static is left.static
        assert result.public is left.public
        assert result.name == left.name

        # Originals unchanged
        assert len(left) == 1
        assert len(right) == 2

        # Type check
        with pytest.raises(XentTypeError):
            _ = left + "not_a_list"

    def test_len_and_contains(self):
        l_value = XList([XString("foo")])
        assert len(l_value) == 1
        # Membership with XString and raw string
        assert XString("foo") in l_value
        assert "foo" in l_value
        assert "bar" not in l_value


class TestTokenXentList:
    """Tests for TokenXentList class functionality."""

    def test_basic_arithmetic(self):
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

    def test_no_scalar_operations(self):
        """Test operations between TokenXentList and scalar values."""
        # Create test instance
        list0 = TokenXentList([("a", 1.0), ("b", 2.0), ("c", 3.0)])

        # Test scalar addition
        with pytest.raises(TypeError):
            list0 + 5

        # Test scalar subtraction
        with pytest.raises(TypeError):
            list0 - 2

        # Scalar multiplication is valid
        list0 * 2

        # Test scalar division
        with pytest.raises(TypeError):
            list0 / 2

        # Test right-hand scalar operations
        with pytest.raises(TypeError):
            10 + list0

        with pytest.raises(TypeError):
            10 - list0

        # Right-hand scalar multiplication is valid
        10 * list0

        # Test left-hand scalar division
        with pytest.raises(TypeError):
            list0 / 10

    def test_type_preservation(self):
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
            assert isinstance(op_result, TokenXentList), (
                f"Operation {i} returned {type(op_result)} instead of TokenXentList"
            )

    def test_comparison_comprehensive(self):
        """Test all comparison operations for TokenXentList with both objects and scalars."""
        list1 = TokenXentList([("a", 1.0), ("b", 2.0)])  # total = 3.0
        list2 = TokenXentList([("x", 0.5), ("y", 2.5)])  # total = 3.0
        list3 = TokenXentList([("p", 2.0), ("q", 3.0)])  # total = 5.0

        # Part 1: Test comparisons between TokenXentList objects
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

        # Part 2: Test comparisons with scalar values
        # list1 has total = 3.0
        assert (list1 < 5) is True
        assert (list1 < 2) is False
        assert (list1 <= 3) is True
        assert (list1 > 2) is True
        assert (list1 > 4) is False
        assert (list1 >= 3) is True
        # Note: == and != with scalars return NotImplemented

    def test_validated_bool(self):
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

    def test_incompatible_operations(self):
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

    def test_repr_and_str(self):
        """Test __repr__ and __str__ methods."""
        list1 = TokenXentList([("hello", 1.234567), ("world", 2.987654)])

        # Test __repr__
        repr_str = repr(list1)
        assert "TokenXentList" in repr_str
        assert "scale=1.0" in repr_str
        assert "hello" in repr_str
        assert "world" in repr_str

        # Test __str__ - should match __repr__
        str_rep = str(list1)
        assert str_rep == repr_str

    def test_edge_cases(self):
        """Test edge cases like empty lists and single elements."""
        # Empty list
        empty = TokenXentList([])
        assert empty.total_xent() == 0.0

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

    def test_unary_pos(self):
        """Test unary positive operator."""
        list1 = TokenXentList([("a", 1.0), ("b", 2.0)])

        # Unary positive should return the same object
        result = +list1
        assert result is list1
        assert result.total_xent() == list1.total_xent()

    def test_scale_behavior(self):
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


class TestJudge:
    """Tests for Judge class functionality."""

    @pytest.fixture
    def judge(self):
        """Create a test Judge instance."""
        judge = Judge("Qwen/Qwen3-0.6B-Base")
        return judge

    def test_first_n_tokens(self, judge):
        string = XString("This is a test string for the Xent framework.")

        assert judge.first_n_tokens(string, 5) == "This is a test string"
        assert judge.first_n_tokens(str(string), 5) == "This is a test string"
        assert judge.first_n_tokens("", 5) == ""
        assert judge.first_n_tokens("   ", 5) == "   "
        assert judge.first_n_tokens("\n", 5) == "\n"

    @pytest.mark.parametrize(
        "statement, expected_truthfulness",
        [
            # Cases that should be True
            ("Water boils at 30 degrees Celsius at sea level", True),
            ("Grass is green", True),
            # Cases that should be False
            ("The sun is smaller than the earth", False),
            (
                "There are no emoji in the following string: 'hello 🌎'",
                False,
            ),
        ],
    )
    def test_truthfulness(self, judge, statement, expected_truthfulness):
        """Tests the is_true method with various statements."""
        assert judge.is_true(statement) == expected_truthfulness


class TestTokenUsage:
    """Tests for token usage tracking functionality."""

    FAKE_GAME_CONFIG: ExecutableGameMap = {
        "game_map": {
            "name": "Token Usage Test",
            "code": "test_code",
            "map_seed": "test_seed_0",
            "presentation_function": get_default_presentation(),
        },
        "player": {
            "name": "alice",
            "id": "test_alice",
            "player_type": "default",
            "options": {"model": "test", "provider": "test"},
        },
        "metadata": {
            "benchmark_id": "test",
            "xent_version": "0.1.0-dev",
            "judge_model": "gpt2",
            "seed": "test_seed",
            "num_rounds_per_game": 30,
            "npcs": [],
        },
    }

    @pytest.mark.asyncio
    async def test_game_iteration_reset(self):
        """Test that token usage resets between iterations but accumulates in final results."""
        game_config = self.FAKE_GAME_CONFIG.copy()
        player = MockXGP(
            "black",
            "test_black",
            {},
            game_config,
            token_usage_per_move={"input_tokens": 15, "output_tokens": 10},
        )
        locals = build_locals(player, [], game_config)
        judge = Judge("gpt2")
        globals = build_globals(judge)
        xrt = XentRuntime(player, [], locals, globals)

        # First iteration: make some moves
        await eval_line("elicit(s1, 20)", 1, xrt)
        await eval_line("elicit(s2, 20)", 2, xrt)

        # Check token usage after first iteration
        assert xrt.token_usage["input_tokens"] == 30  # 15 * 2
        assert xrt.token_usage["output_tokens"] == 20  # 10 * 2

        # Get results and reset (simulates end of game iteration)
        iteration1_result = xrt.get_results_and_reset()

        # Verify iteration result contains token usage
        assert iteration1_result["token_usage"]["input_tokens"] == 30
        assert iteration1_result["token_usage"]["output_tokens"] == 20

        # Verify runtime token usage was reset
        assert xrt.token_usage["input_tokens"] == 0
        assert xrt.token_usage["output_tokens"] == 0

        # Second iteration: make more moves
        await eval_line("elicit(s3, 20)", 1, xrt)

        # Check token usage in second iteration
        assert xrt.token_usage["input_tokens"] == 15  # 15 * 1
        assert xrt.token_usage["output_tokens"] == 10  # 10 * 1

        # Get second iteration results
        iteration2_result = xrt.get_results_and_reset()
        assert iteration2_result["token_usage"]["input_tokens"] == 15
        assert iteration2_result["token_usage"]["output_tokens"] == 10

        total_usage = extract_token_usage([iteration1_result, iteration2_result])

        # Verify total accumulation across iterations
        assert total_usage["input_tokens"] == 45  # 30 + 15
        assert total_usage["output_tokens"] == 30  # 20 + 10

    @pytest.mark.asyncio
    async def test_zero_token_usage(self):
        """Test handling of zero token usage scenarios."""
        game_config = self.FAKE_GAME_CONFIG.copy()
        player = MockXGP(
            "black",
            "test_black",
            {},
            game_config,
            token_usage_per_move={"input_tokens": 0, "output_tokens": 0},
        )
        locals = build_locals(player, [], game_config)
        judge = Judge("gpt2")
        globals = build_globals(judge)
        xrt = XentRuntime(player, [], locals, globals)

        # Make elicit call with zero token usage
        await eval_line("elicit(s1, 20)", 1, xrt)

        # Verify zero accumulation works correctly
        assert xrt.token_usage["input_tokens"] == 0
        assert xrt.token_usage["output_tokens"] == 0

        # Test reset with zero values
        result = xrt.get_results_and_reset()
        assert result["token_usage"]["input_tokens"] == 0
        assert result["token_usage"]["output_tokens"] == 0


class TestVersioning:
    """Tests for version tracking functionality"""

    def test_get_xent_version(self):
        """Test that get_xent_version returns a valid version string"""
        version = get_xent_version()
        assert isinstance(version, str)
        assert len(version) > 0
        # Should be semantic version or dev version
        assert "." in version or "dev" in version

    def test_validate_version_matching(self):
        """Test version validation with matching versions"""
        current = get_xent_version()
        is_valid, message = validate_version(current, current)
        assert is_valid is True
        assert "match" in message.lower()

    def test_validate_version_mismatch(self):
        """Test version validation with mismatching versions"""
        is_valid, message = validate_version("1.0.0", "2.0.0")
        assert is_valid is False
        assert "mismatch" in message.lower()
        assert "1.0.0" in message
        assert "2.0.0" in message

    def test_validate_version_missing(self):
        """Test version validation with missing version (old config)"""
        current = get_xent_version()
        is_valid, message = validate_version(None, current)
        assert is_valid is True  # Should not fail for backward compatibility
        assert "no version" in message.lower() or "warning" in message.lower()


class TestSDKFunctions:
    def test_format_elicit_request(self):
        event: ElicitRequestEvent = {
            "type": "elicit_request",
            "line": "elicit(var, 10)",
            "line_num": 5,
            "player": "alice",
            "var_name": "move",
            "max_len": 10,
            "registers": {},
        }
        result = format_elicit_request(event)
        assert result == "Request: move (max 10 tokens)"

    def test_format_elicit_response(self):
        event: ElicitResponseEvent = {
            "type": "elicit_response",
            "line": "elicit(var, 10)",
            "line_num": 5,
            "player": "alice",
            "response": "my move",
            "token_usage": {"input_tokens": 10, "output_tokens": 5},
        }
        result = format_elicit_response(event)
        assert result == "Response: my move"

    def test_format_reveal(self):
        values = {"var1": XString("value1"), "var2": XString("value2")}
        event: RevealEvent = {
            "type": "reveal",
            "line": "reveal(var1, var2)",
            "line_num": 3,
            "player": "alice",
            "values": values,
        }
        result = format_reveal(event)
        expected = 'Revealed: var1: "value1", var2: "value2"'
        assert result == expected

    def test_format_reward(self):
        reward_value = TokenXentList([("token1", 1.5), ("token2", 0.5)])
        event: RewardEvent = {
            "type": "reward",
            "line": "reward(player, score)",
            "line_num": 8,
            "player": "alice",
            "value": reward_value,
        }
        result, score = format_reward(event)  # format_reward now returns tuple
        assert "Total:" in result
        assert "Per-token:" in result
        assert score == 20  # rounded total

    def test_format_failed_ensure(self):
        event: FailedEnsureEvent = {
            "type": "failed_ensure",
            "line": "ensure(condition)",
            "line_num": 10,
            "player": "alice",
            "ensure_results": [True, False, True],
            "beacon": "previous_elicit",
        }
        result = format_failed_ensure(event)
        expected = "Failed ensure: Argument 0: True, Argument 1: False, Argument 2: True. Moving to beacon: previous_elicit"
        assert result == expected

    def test_get_event_summary(self):
        events: list[XentEvent] = [
            {
                "type": "elicit_request",
                "line": "",
                "line_num": 1,
                "player": "alice",
                "var_name": "move",
                "max_len": 10,
                "registers": {},
            },
            {
                "type": "elicit_response",
                "line": "",
                "line_num": 1,
                "player": "alice",
                "response": "test",
                "token_usage": {"input_tokens": 1, "output_tokens": 1},
            },
            {
                "type": "elicit_request",
                "line": "",
                "line_num": 2,
                "player": "alice",
                "var_name": "move2",
                "max_len": 5,
                "registers": {},
            },
        ]
        result = get_event_summary(events)
        assert "Game history:" in result
        assert "2 elicit_request" in result
        assert "1 elicit_response" in result

    def test_get_current_registers(self):
        state = {
            "var1": XString("value1"),
            "var2": "string_value",
            "var3": 42,
            "var4": True,
            "var5": {"not": "extractable"},
        }

        registers = get_current_registers(state)
        assert registers["var1"] == "value1"
        assert registers["var2"] == "string_value"
        assert registers["var3"] == "42"
        assert registers["var4"] == "True"
        assert "var5" not in registers

    def test_format_registers_display(self):
        registers = {"var1": "value1", "var2": "value2"}
        result = format_registers_display(registers)
        assert "Current registers:" in result
        assert "var1: value1" in result
        assert "var2: value2" in result

        empty_result = format_registers_display({})
        assert empty_result == "No registers available"


class TestPresentationFunction:
    def test_simple_presentation_function(self):
        code = """
from xent.presentation.sdk import ChatBuilder

def present_turn(state, since_events, metadata, full_history=None, ctx=None):
    b = ChatBuilder()
    b.user("Simple presentation")
    return b.render()
"""
        func = PresentationFunction(code)
        messages, _ = func({}, [], SAMPLE_METADATA)
        result = "\n".join(m["content"] for m in messages)
        assert result == "Simple presentation"

    def test_presentation_with_sdk_functions(self):
        code = """
from xent.presentation.sdk import format_elicit_request, format_reveal, ChatBuilder

def present_turn(state, since_events, metadata, full_history=None, ctx=None):
    if not since_events:
        return [dict(role="user", content="No events yet")]

    lines = []
    for event in since_events:
        if event['type'] == 'elicit_request':
            lines.append(format_elicit_request(event))
        elif event['type'] == 'reveal':
            lines.append(format_reveal(event))

    sep = chr(10)
    return [dict(role="user", content=sep.join(lines))]
"""
        func = PresentationFunction(code)

        events: list[XentEvent] = [
            {
                "type": "elicit_request",
                "line": "test",
                "line_num": 1,
                "player": "alice",
                "var_name": "move",
                "max_len": 10,
                "registers": {},
            }
        ]

        messages, _ = func({}, events, SAMPLE_METADATA)
        result = "\n".join(m["content"] for m in messages)
        assert "Request: move (max 10 tokens)" in result

    def test_presentation_function_validation(self):
        valid_code = """
def present_turn(state, since_events, metadata, full_history=None, ctx=None):
    return [dict(role="user", content="Valid function")]
"""
        func = PresentationFunction(valid_code)
        assert func.validate()

    def test_invalid_syntax(self):
        with pytest.raises(XentInternalError):
            PresentationFunction(
                "def present_turn(state since_events, metadata): pass"
            )  # Missing comma

    def test_missing_present_function(self):
        with pytest.raises(XentConfigurationError):
            PresentationFunction("def other_function(): pass")

    def test_non_callable_present(self):
        with pytest.raises(XentInternalError):
            PresentationFunction("present_turn = 'not a function'")

    def test_sdk_utilities_with_imports(self):
        """Test that SDK utilities work correctly when imported"""
        code = """
from xent.presentation.sdk import split_rounds, extract_rewards, get_scores_by_round, ChatBuilder
from xent.common.token_xent_list import TokenXentList

def present_turn(state, since_events, metadata, full_history=None, ctx=None):
    history = full_history if full_history is not None else since_events
    rounds = split_rounds(history)
    all_rewards = extract_rewards(history)
    scores = get_scores_by_round(history)
    return [dict(role="user", content=f"Rounds: {len(rounds)}, Rewards: {len(all_rewards)}, Scores: {len(scores)}")]
"""
        func = PresentationFunction(code)

        # Create test history with multiple rounds
        history: list[XentEvent] = [
            {"type": "round_started", "round_index": 0},  # type: ignore
            {"type": "elicit_response", "response": "test1"},  # type: ignore
            {"type": "reward", "value": TokenXentList([("token1", 1.0)])},  # type: ignore
            {"type": "round_finished", "round_index": 0},  # type: ignore
            {"type": "round_started", "round_index": 1},  # type: ignore
            {"type": "elicit_response", "response": "test2"},  # type: ignore
            {"type": "reward", "value": TokenXentList([("token2", 2.0)])},  # type: ignore
            {"type": "round_finished", "round_index": 2},  # type: ignore
        ]

        messages, _ = func({}, [], SAMPLE_METADATA, full_history=history)
        result = "\n".join(m["content"] for m in messages)
        assert "Rounds: 2" in result
        assert "Rewards: 2" in result
        assert "Scores: 2" in result

    def test_presentation_builder(self):
        """Test PresentationBuilder functionality"""
        code = """
from xent.presentation.sdk import PresentationBuilder, ChatBuilder

def present_turn(state, since_events, metadata, full_history=None, ctx=None):
    builder = PresentationBuilder()
    builder.add_header("Test Header")
    builder.add_line("Test Line")
    builder.start_section("testSection")
    builder.add_line("Inside Section")
    builder.end_section()
    builder.start_section("withAttr", key="value")
    builder.add_line("With Attributes")
    content = builder.render()
    return [dict(role="user", content=content)]
"""
        func = PresentationFunction(code)
        messages, _ = func({}, [], SAMPLE_METADATA)
        result = "\n".join(m["content"] for m in messages)

        assert "Test Header" in result
        assert "Test Line" in result
        assert "<testSection>" in result
        assert "Inside Section" in result
        assert "</testSection>" in result
        assert '<withAttr key="value">' in result
        assert "With Attributes" in result
        assert "</withAttr>" in result

    def test_format_functions(self):
        """Test SDK formatting functions"""
        code = """
from xent.presentation.sdk import format_token_xent_list, format_reward
from xent.common.token_xent_list import TokenXentList

def present_turn(state, since_events, metadata, full_history=None, ctx=None):
    # Test format_token_xent_list
    txl = TokenXentList([("hello", 1.5), ("world", 2.0)])
    formatted = format_token_xent_list(txl)

    # Test format_reward (returns tuple)
    reward_event = {"value": txl}
    reward_text, reward_score = format_reward(reward_event)

    return [dict(role="user", content=f"Formatted: {formatted}\\nReward: {reward_text}\\nScore: {reward_score}")]
"""
        func = PresentationFunction(code)
        messages, _ = func({}, [], SAMPLE_METADATA)
        result = "\n".join(m["content"] for m in messages)

        assert "hello|15 world|20" in result  # rounded values
        assert "Total:" in result
        assert "Per-token:" in result
        assert "Score: 35" in result  # rounded by round_xent


@pytest.fixture
def game_config():
    """Create a game config with a custom presentation function"""
    presentation_code = """
def present_turn(state, since_events, metadata, full_history=None, ctx=None):
    history = full_history if full_history is not None else since_events
    lines = []
    for event in history:
        if event['type'] == 'elicit_request':
            lines.append(f"CUSTOM: {event['var_name']} requested (max {event['max_len']})")
        elif event['type'] == 'reveal':
            var_names = list(event['values'].keys())
            lines.append(f"CUSTOM: Revealed {', '.join(var_names)}")
        else:
            lines.append(f"CUSTOM: {event['type']}")
    sep = chr(10)
    return [dict(role='user', content=sep.join(lines))]
"""

    expanded_game: GameMapConfig = {
        "name": "test_game",
        "code": 'assign(x="test")\nreveal(x)\nelicit(y, 10)',
        "map_seed": "test_seed",
        "presentation_function": presentation_code,
    }

    config: ExecutableGameMap = {
        "game_map": expanded_game,
        "player": {
            "name": "black",
            "id": "mock_id",
            "player_type": "mock",
            "options": {},
        },
        "metadata": {
            "benchmark_id": "test",
            "xent_version": "0.1.0-dev",
            "judge_model": "test",
            "num_rounds_per_game": 1,
            "seed": "test",
            "npcs": [],
        },
    }

    return config


class TestPresentationIntegration:
    """Test presentation layer integration with the game system"""

    def test_player_loads_custom_presentation_function(self, game_config):
        """Test that players load custom presentation functions"""
        options: dict[str, str | int | float | bool] = {
            "provider": "ollama",
            "model": "test",
        }
        player = DefaultXGP("black", "test_id", options, game_config)

        assert player.presentation_function is not None
        assert callable(player.presentation_function)

    def test_custom_presentation_function_usage(self, game_config):
        """Test that custom presentation function is used when making moves"""
        options: dict[str, str | int | float | bool] = {
            "provider": "ollama",
            "model": "test",
        }
        player = DefaultXGP("black", "test_id", options, game_config)

        # Simulate some events

        reveal_event: RevealEvent = {
            "type": "reveal",
            "line": "reveal(x)",
            "line_num": 1,
            "player": "black",
            "values": {"x": XString("test_value")},
        }

        elicit_event: ElicitRequestEvent = {
            "type": "elicit_request",
            "line": "elicit(y, 10)",
            "line_num": 2,
            "player": "black",
            "var_name": "y",
            "max_len": 10,
            "registers": {},
        }

        player.event_history = [reveal_event, elicit_event]

        # Test the presentation function directly
        messages, _ = player.presentation_function(
            {},
            player.event_history,
            SAMPLE_METADATA,
            full_history=player.event_history,
            ctx={},
        )
        result = "\n".join(m["content"] for m in messages)

        assert "CUSTOM: Revealed x" in result
        assert "CUSTOM: y requested (max 10)" in result
        assert result.startswith("CUSTOM:")

    def test_presentation_function_throws_error(self, game_config):
        # Create a game config with a broken presentation function
        broken_code = """
def present_turn(state, since_events, metadata, full_history=None, ctx=None):
    raise ValueError("Intentional error")
"""
        game_config["game_map"]["presentation_function"] = broken_code

        options: dict[str, str | int | float | bool] = {
            "provider": "ollama",
            "model": "test",
        }
        player = DefaultXGP("black", "test_id", options, game_config)

        assert player.presentation_function is not None

        elicit_event: ElicitRequestEvent = {
            "type": "elicit_request",
            "line": "elicit(y, 10)",
            "line_num": 1,
            "player": "black",
            "var_name": "y",
            "max_len": 10,
            "registers": {},
        }

        player.event_history = [elicit_event]

        with pytest.raises(XentConfigurationError):
            player.presentation_function({}, player.event_history, SAMPLE_METADATA)

    def test_default_presentation_function(self):
        """Test that the default presentation function produces expected output"""

        default_code = get_default_presentation()
        func = PresentationFunction(default_code)

        # Test with sample events
        reveal_event: RevealEvent = {
            "type": "reveal",
            "line": "reveal(x)",
            "line_num": 1,
            "player": "black",
            "values": {"x": XString("test_value")},
        }

        elicit_event: ElicitRequestEvent = {
            "type": "elicit_request",
            "line": "elicit(y, 10)",
            "line_num": 2,
            "player": "black",
            "var_name": "y",
            "max_len": 10,
            "registers": {},
        }

        history: list[XentEvent] = [reveal_event, elicit_event]
        messages, _ = func({}, history, SAMPLE_METADATA)
        result = "\n".join(m["content"] for m in messages)

        # Should match the format produced by SDK functions
        expected_lines = [
            'Revealed: x: "test_value"',
            "Request: y (max 10 tokens)",
        ]

        for expected_line in expected_lines:
            assert expected_line in result

    @pytest.mark.asyncio
    async def test_full_integration_with_mock_player(self):
        """Test the full integration path with MockXGP player using presentation"""

        # Create a presentation function that includes register state info
        presentation_code = """
def present_turn(state, since_events, metadata, full_history=None, ctx=None):
    history = full_history if full_history is not None else since_events
    lines = []
    if state:
        register_values = []
        for name, value in state.items():
            try:
                register_values.append(f"{name}={str(value)[:20]}")
            except:
                pass
        if register_values:
            lines.append(f"REGISTERS: {', '.join(register_values)}")
    for event in history:
        if event['type'] == 'reveal':
            lines.append("CUSTOM_REVEAL: Values shown")
        elif event['type'] == 'elicit_request':
            lines.append(f"CUSTOM_ELICIT: Need {event['var_name']}")
        elif event['type'] == 'reward':
            lines.append("CUSTOM_REWARD: Score updated")
    if not lines:
        lines.append("CUSTOM_START: Game beginning")
    sep = chr(10)
    return [dict(role='user', content=sep.join(lines))]
"""

        # Create game configuration
        expanded_game: GameMapConfig = {
            "name": "test_integration",
            "code": """assign(x="initial_value")
reveal(x)
elicit(z, 10)""",
            "map_seed": "test_seed",
            "presentation_function": presentation_code,
        }

        config: ExecutableGameMap = {
            "game_map": expanded_game,
            "player": {
                "name": "black",
                "id": "mock_id",
                "player_type": "mock",
                "options": {},
            },
            "metadata": {
                "benchmark_id": "test",
                "xent_version": "0.1.0-dev",
                "judge_model": "test",
                "num_rounds_per_game": 1,
                "seed": "test",
                "npcs": [],
            },
        }

        # Create MockXGP player with the game config
        mock_player = MockXGP("black", "mock_id", None, config)

        # Simulate reveal event
        reveal_event: RevealEvent = {
            "type": "reveal",
            "line": "reveal(x)",
            "line_num": 2,
            "player": "black",
            "values": {"x": XString("initial_value")},
        }
        await mock_player.post(reveal_event)

        # Simulate elicit request event
        elicit_event: ElicitRequestEvent = {
            "type": "elicit_request",
            "line": "elicit(z, 10)",
            "line_num": 3,
            "player": "black",
            "var_name": "z",
            "max_len": 10,
            "registers": {},
        }
        await mock_player.post(elicit_event)

        # Create register states with actual values to verify they're passed
        register_states = {
            "x": XString("initial_value"),
            "y": XString("another_value"),
            "empty": XString(""),
        }

        # Call make_move - this is the crucial integration point
        move_result = await mock_player.make_move("z", register_states)
        move, _tokens = (move_result.response, move_result.token_usage)

        # Verify the move was made
        assert move == "mocked_move"

        # Verify presentation function was used in make_move by inspecting conversation
        joined = "\n".join(
            m["content"] for m in mock_player.conversation if m["role"] == "user"
        )
        assert "CUSTOM_" in joined
        assert "CUSTOM_REVEAL" in joined
        assert "CUSTOM_ELICIT" in joined

        # Verify registers were passed (non-empty state)
        assert "REGISTERS:" in joined, "Register state not passed to presentation"
        assert "x=" in joined, "Register x not in presentation output"
        assert "y=" in joined, "Register y not in presentation output"

        # Verify default formatting is NOT present
        assert "02-<reveal>" not in joined, "Default formatting should not be present"
        assert "03-<elicit>" not in joined, "Default formatting should not be present"

    @pytest.mark.asyncio
    async def test_presentation_throws_with_mock_player(self):
        """Test that MockXGP falls back to default formatting when presentation fails"""

        # Create a broken presentation function
        broken_presentation = """
def present_turn(state, since_events, metadata, full_history=None, ctx=None):
    return 1 / 0
"""

        expanded_game: GameMapConfig = {
            "name": "test_fallback",
            "code": """reveal("test")
elicit(x, 5)""",
            "map_seed": "test_seed",
            "presentation_function": broken_presentation,
        }

        config: ExecutableGameMap = {
            "metadata": {
                "benchmark_id": "test",
                "xent_version": "0.1.0-dev",
                "judge_model": "test",
                "num_rounds_per_game": 1,
                "seed": "test",
                "store_full_player_interactions": False,
                "npcs": [],
            },
            "game_map": expanded_game,
            "player": {
                "name": "black",
                "id": "mock_id",
                "player_type": "mock",
                "options": {},
            },
        }

        mock_player = MockXGP("black", "mock_id", None, config)

        elicit_event: ElicitRequestEvent = {
            "type": "elicit_request",
            "line": "elicit(x, 5)",
            "line_num": 2,
            "player": "black",
            "var_name": "x",
            "max_len": 5,
            "registers": {},
        }

        await mock_player.post(elicit_event)

        register_states = {"test": XString("test_value")}
        with pytest.raises(XentConfigurationError):
            await mock_player.make_move("x", register_states)

    def test_real_game_presentation_with_sdk(self):
        """Test that a real game presentation works with SDK imports"""
        # Simplified version of Condense presentation using SDK (turn-based)
        condense_presentation = """
from xent.presentation.sdk import (
    PresentationBuilder,
    extract_rewards,
    get_scores_by_round,
    split_rounds,
)

def present_turn(state, since_events, metadata, full_history=None, ctx=None):
    history = full_history if full_history is not None else since_events
    builder = PresentationBuilder()
    builder.add_header("Condense Game Test")
    builder.add_game_state(story=state.get("s", "test story"))
    scores_by_round = get_scores_by_round(history)
    if scores_by_round:
        builder.start_section("history")
        for score_data in scores_by_round:
            builder.add_line(f"Round {score_data['round']}: {score_data['total']:.3f}")
        builder.end_section()
    else:
        builder.add_line("No history yet")
    return [dict(role='user', content=builder.render())]
"""

        func = PresentationFunction(condense_presentation)

        # Test with realistic game state and history
        from xent.common.token_xent_list import TokenXentList

        state = {"s": XString("Once upon a time")}
        history: list[XentEvent] = [
            {"type": "elicit_response", "response": "magical"},  # type: ignore
            {"type": "reward", "value": TokenXentList([("test", 1.5)])},  # type: ignore
        ]

        messages, _ = func(state, history, SAMPLE_METADATA)
        result = "\n".join(m["content"] for m in messages)
        assert "Condense Game Test" in result
        assert "Once upon a time" in result
        assert "Round 0: 1.5" in result

    def test_sdk_data_extraction_with_game_history(self):
        """Test SDK utilities with realistic multi-round game history"""
        test_presentation = """
from xent.presentation.sdk import split_rounds, get_scores_by_round, extract_rewards

def present_turn(state, since_events, metadata, full_history=None, ctx=None):
    history = full_history if full_history is not None else since_events
    rounds = split_rounds(history)
    scores = get_scores_by_round(history)
    all_rewards = extract_rewards(history)
    lines = [f"Total rounds: {len(rounds)}"]
    lines.append(f"Total rewards: {len(all_rewards)}")
    lines.append(f"Scores calculated: {len(scores)}")
    if scores:
        total_scores = [s['total'] for s in scores]
        lines.append(f"Best score: {max(total_scores):.3f}")
        lines.append(f"Worst score: {min(total_scores):.3f}")
    sep = chr(10)
    return [dict(role='user', content=sep.join(lines))]
"""

        func = PresentationFunction(test_presentation)

        # Create realistic multi-round history

        history: list[XentEvent] = [
            # Round 1
            {"type": "round_started", "round_index": 0},  # type: ignore
            {"type": "elicit_response", "response": "attempt1"},  # type: ignore
            {"type": "reward", "value": TokenXentList([("token1", 2.0)])},  # type: ignore
            {"type": "round_finished", "round_index": 0},  # type: ignore
            # Round 2
            {"type": "round_started", "round_index": 0},  # type: ignore
            {"type": "elicit_response", "response": "attempt2"},  # type: ignore
            {"type": "reward", "value": TokenXentList([("token2", 3.5)])},  # type: ignore
            {"type": "round_finished", "round_index": 0},  # type: ignore
            # Round 3
            {"type": "round_started", "round_index": 0},  # type: ignore
            {"type": "elicit_response", "response": "attempt3"},  # type: ignore
            {"type": "reward", "value": TokenXentList([("token3", 1.2)])},  # type: ignore
            {"type": "round_finished", "round_index": 0},  # type: ignore
        ]

        messages, _ = func({}, [], SAMPLE_METADATA, full_history=history)
        result = "\n".join(m["content"] for m in messages)

        assert "Total rounds: 3" in result
        assert "Total rewards: 3" in result
        assert "Scores calculated: 3" in result
        assert "Best score: 3.5" in result
        assert "Worst score: 1.2" in result


class TestRoundBoundaryEvents:
    @pytest.mark.asyncio
    async def test_round_start_and_finish_events(self, xrt):
        game_code = """
        assign(s='hello')
        reveal(s)
        reward(xent('hello world'))
        """.strip()

        results = await play_game(game_code, xrt, num_rounds=1)
        assert len(results) == 1
        history = results[0]["history"]

        types = [e["type"] for e in history]

        # Exactly one start and one finish
        assert types.count("round_started") == 1
        assert types.count("round_finished") == 1

        start_event = history[0]
        finish_event = history[-1]

        # Round index present and equal
        assert finish_event["type"] == "round_finished"
        assert start_event["type"] == "round_started"
        assert start_event["round_index"] == finish_event["round_index"] == 0

        # Check that line nums are correct
        assert start_event["line_num"] == 1, "Start event should be line number 1"
        assert finish_event["line_num"] == 3, "Finish event should be line number 3"

        # Check that players are strings
        for event in history:
            assert isinstance(event["player"], str)
