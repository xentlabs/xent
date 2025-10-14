import pytest

from xent.common.errors import XentGameError, XentInternalError, XentSyntaxError
from xent.common.util import dumps, loads
from xent.common.x_flag import XFlag
from xent.common.x_list import XList
from xent.common.x_string import XString
from xent.runtime.execution import eval_line, play_game


class TestAssignInstruction:
    """Test the assign instruction functionality."""

    @pytest.mark.asyncio
    async def test_assign_comprehensive(self, xrt):
        """Comprehensive test for basic assignment functionality."""
        # Part 1: Test basic string assignment to different register types
        await eval_line("assign(s='hello')", 1, xrt)
        assert isinstance(xrt.local_vars["s"], XString)
        assert str(xrt.local_vars["s"]) == "hello"

        await eval_line("assign(t='world')", 2, xrt)
        assert str(xrt.local_vars["t"]) == "world"

        await eval_line("assign(x='test')", 3, xrt)
        assert str(xrt.local_vars["x"]) == "test"

        # Part 2: Test assigning multiple variables in one statement
        await eval_line("assign(s='hello2', t='world2', x='test2')", 4, xrt)
        assert str(xrt.local_vars["s"]) == "hello2"
        assert str(xrt.local_vars["t"]) == "world2"
        assert str(xrt.local_vars["x"]) == "test2"

        # Part 3: Test assignment to numbered registers
        await eval_line("assign(s1='first', s2='second', s3='third')", 5, xrt)
        assert str(xrt.local_vars["s1"]) == "first"
        assert str(xrt.local_vars["s2"]) == "second"
        assert str(xrt.local_vars["s3"]) == "third"

    @pytest.mark.asyncio
    async def test_assign_static_registers(self, xrt):
        """Test that assignment to static registers is not allowed."""
        # Static register types are: ["a", "b", "c"]
        with pytest.raises(XentSyntaxError):
            await eval_line("assign(a='should_fail')", 1, xrt)

        with pytest.raises(XentSyntaxError):
            await eval_line("assign(b1='should_fail')", 1, xrt)

        with pytest.raises(XentSyntaxError):
            await eval_line("assign(c='should_fail')", 1, xrt)

    @pytest.mark.asyncio
    async def test_assign_function_results(self, xrt):
        """Test assigning results of functions to registers."""
        await eval_line("assign(t='test string')", 1, xrt)
        assert "t" in xrt.local_vars
        assert str(xrt.local_vars["t"]) == "test string"

    @pytest.mark.asyncio
    async def test_assign_string_operations(self, xrt):
        """Test assigning results of string operations."""
        # Setup some strings first
        await eval_line("assign(s1='hello world', s2='world')", 1, xrt)

        # Test concatenation
        await eval_line("assign(s3=s1 + ' test')", 1, xrt)
        assert str(xrt.local_vars["s3"]) == "hello world test"

        # Test // operation (substring before)
        await eval_line("assign(s3=s1 // s2)", 1, xrt)
        assert str(xrt.local_vars["s3"]) == "hello "

        # Test % operation (substring after)
        await eval_line("assign(s3=s1 % s2)", 1, xrt)
        assert str(xrt.local_vars["s3"]) == ""  # Since "world" is at the end

        # Test with a different example
        await eval_line("assign(s1='hello world again', s2='world')", 1, xrt)
        await eval_line("assign(s3=s1 % s2)", 1, xrt)
        assert str(xrt.local_vars["s3"]) == " again"

    @pytest.mark.asyncio
    async def test_assign_empty_string(self, xrt):
        """Test assigning empty strings."""
        await eval_line("assign(s='')", 1, xrt)
        assert str(xrt.local_vars["s"]) == ""

        # Test operations with empty strings
        await eval_line("assign(s1='hello', s2='')", 1, xrt)
        await eval_line("assign(s3=s1 // s2)", 1, xrt)
        assert str(xrt.local_vars["s3"]) == "hello"  # s1 // "" should return s1

        await eval_line("assign(s3=s1 % s2)", 1, xrt)
        assert str(xrt.local_vars["s3"]) == ""  # s1 % "" should return ""

    @pytest.mark.asyncio
    async def test_assign_complex_expressions(self, xrt):
        """Test assigning results of complex expressions."""
        # Test function chaining
        await eval_line("assign(s1='test string', s2=first_n_tokens(s1, 5))", 1, xrt)
        assert "s2" in xrt.local_vars
        assert str(xrt.local_vars["s2"]) == "test string"

        # Test nested operations dont work
        # First, lets clear the state
        await eval_line("assign(s1='', s2='', s3='')", 1, xrt)
        await eval_line("assign(s1='hello', s1='world', s3=(s1 + ' ') + s2)", 1, xrt)
        assert str(xrt.local_vars["s3"]) == " "

    @pytest.mark.asyncio
    async def test_assign_overwrite(self, xrt):
        """Test that assignments overwrite previous values."""
        await eval_line("assign(s='first')", 1, xrt)
        assert str(xrt.local_vars["s"]) == "first"

        await eval_line("assign(s='second')", 1, xrt)
        assert str(xrt.local_vars["s"]) == "second"

    @pytest.mark.asyncio
    async def test_assign_with_positional_args(self, xrt):
        """Test that assign only accepts keyword arguments."""
        with pytest.raises(XentSyntaxError):
            await eval_line("assign('should_fail')", 1, xrt)

        with pytest.raises(XentSyntaxError):
            await eval_line("assign('s', 'value')", 1, xrt)

    @pytest.mark.asyncio
    async def test_assign_invalid_register_names(self, xrt):
        """Test assignment to invalid register names."""
        # Test invalid register type
        with pytest.raises(XentSyntaxError):
            await eval_line("assign(z='invalid')", 1, xrt)

        # Test register number out of bounds (assuming num_registers_per_type is 4)
        with pytest.raises(XentSyntaxError):
            await eval_line("assign(s10='too_high')", 1, xrt)

    @pytest.mark.asyncio
    async def test_assign_special_characters(self, xrt):
        """Test assignment of strings with special characters."""
        await eval_line("assign(s='hello\\nworld')", 1, xrt)
        assert str(xrt.local_vars["s"]) == "hello\nworld"

        await eval_line("assign(s='tab\\there')", 1, xrt)
        assert str(xrt.local_vars["s"]) == "tab\there"

        await eval_line('assign(s="quotes \' and \\"")', 1, xrt)
        assert "quotes" in str(xrt.local_vars["s"])

    @pytest.mark.asyncio
    async def test_assign_in_game_context(self, xrt):
        """Test assign instruction within a full game context."""
        game_code = """
        assign(s1='hello', s2='world')
        assign(s3=s1 + ' ' + s2)
        reveal(s3)
        """

        game_results = await play_game(game_code, xrt, num_rounds=1)
        assert len(game_results) == 1

        # Check that the assignments worked by looking at the reveal
        player_history = xrt.player.event_history
        assert any("hello world" in str(h) for h in player_history)


class TestRevealInstruction:
    """Test the reveal instruction functionality."""

    @pytest.mark.asyncio
    async def test_reveal_basic(self, xrt):
        """Test reveal with explicit player specification."""
        await eval_line("assign(s='message for black')", 1, xrt)
        await eval_line("reveal(s)", 2, xrt)

        player = xrt.player
        assert len(player.event_history) == 1
        print(player)
        print(player.event_history)
        assert "message for black" in str(player.event_history[0])

    @pytest.mark.asyncio
    async def test_reveal_multiple_values(self, xrt):
        """Test revealing multiple values at once."""
        await eval_line("assign(s1='first', s2='second', s3='third')", 1, xrt)
        await eval_line("reveal(s1, s2, s3)", 2, xrt)

        player = xrt.player
        assert len(player.event_history) == 1
        # All values should be in the reveal
        assert "first" in str(player.event_history[0])
        assert "second" in str(player.event_history[0])
        assert "third" in str(player.event_history[0])

    @pytest.mark.asyncio
    async def test_reveal_empty_string(self, xrt):
        """Test revealing empty strings."""
        await eval_line("assign(s='')", 1, xrt)
        await eval_line("reveal(s)", 2, xrt)

        player = xrt.player
        assert len(player.event_history) == 1
        # The reveal should still happen even with empty string

    @pytest.mark.asyncio
    async def test_reveal_computed_values(self, xrt):
        """Test revealing computed values."""
        await eval_line("assign(s1='hello', s2='world')", 1, xrt)
        await eval_line("reveal(s1 + ' ' + s2)", 2, xrt)

        player = xrt.player
        assert len(player.event_history) == 1
        assert "hello world" in str(player.event_history[0])

    @pytest.mark.asyncio
    async def test_reveal_only_positional_args(self, xrt):
        """Test that reveal only accepts positional arguments."""
        await eval_line("assign(s='test')", 1, xrt)

        # This should fail because reveal doesn't accept keyword arguments
        with pytest.raises(XentSyntaxError):
            await eval_line("reveal(value=s)", 2, xrt)


class TestElicitInstruction:
    """Test the elicit instruction functionality."""

    @pytest.mark.asyncio
    async def test_elicit_player_specification(self, xrt):
        """Test elicit with both default and explicit player specification."""
        # Part 1: Test basic elicit with default player
        await eval_line("elicit(s, 10)", 1, xrt)

        # Check that the variable was set
        assert "s" in xrt.local_vars
        assert str(xrt.local_vars["s"]) == "mocked_move"

        # Check that a previous_elicit beacon was created
        assert "previous_elicit" in xrt.beacons
        assert xrt.beacons["previous_elicit"].line_num == 1

        # Part 2: Test elicit with explicit player specification
        await eval_line("elicit(t, 10)", 2, xrt)

        assert "t" in xrt.local_vars
        assert str(xrt.local_vars["t"]) == "mocked_move"

    @pytest.mark.asyncio
    async def test_elicit_multiple_variables_comprehensive(self, xrt):
        """Test eliciting multiple variables with and without explicit player."""
        # Part 1: Test eliciting multiple variables without explicit player
        await eval_line("elicit(s1, s2, s3, 10)", 1, xrt)

        # All variables should be set
        assert "s1" in xrt.local_vars
        assert "s2" in xrt.local_vars
        assert "s3" in xrt.local_vars

        # Each should have received a move
        assert str(xrt.local_vars["s1"]) == "mocked_move"
        assert str(xrt.local_vars["s2"]) == "mocked_move"
        assert str(xrt.local_vars["s3"]) == "mocked_move"

        # Part 2: Test eliciting multiple variables with explicit player
        await eval_line("elicit(t1, t2, 10)", 2, xrt)

        assert "t1" in xrt.local_vars
        assert "t2" in xrt.local_vars
        assert str(xrt.local_vars["t1"]) == "mocked_move"
        assert str(xrt.local_vars["t2"]) == "mocked_move"

    @pytest.mark.asyncio
    async def test_elicit_token_limit(self, xrt):
        """Test elicit with different token limits."""
        # The token limit is passed as the last argument
        await eval_line("elicit(s1, 5)", 1, xrt)
        await eval_line("elicit(s2, 100)", 2, xrt)

        # Both should work (mock player doesn't respect token limit)
        assert "s1" in xrt.local_vars
        assert "s2" in xrt.local_vars

    @pytest.mark.asyncio
    async def test_elicit_missing_token_limit(self, xrt):
        """Test that elicit requires a token limit."""
        with pytest.raises(XentSyntaxError):
            await eval_line("elicit(s)", 1, xrt)

        with pytest.raises(XentSyntaxError):
            await eval_line("elicit(s)", 1, xrt)

    @pytest.mark.asyncio
    async def test_elicit_only_positional_args(self, xrt):
        """Test that elicit only accepts positional arguments."""
        with pytest.raises(XentSyntaxError):
            await eval_line("elicit(var=s, limit=10)", 1, xrt)


class TestRewardInstruction:
    """Test the reward instruction functionality."""

    @pytest.mark.asyncio
    async def test_reward_values_comprehensive(self, xrt):
        """Comprehensive test for reward with various value types."""
        player = xrt.player

        # Part 1: Test basic positive xent reward
        initial_score = player.get_score()
        await eval_line("reward(xent('hello world'))", 1, xrt)
        score_after_positive = player.get_score()
        assert score_after_positive > initial_score

        # Part 2: Test negative xent reward
        await eval_line("reward(-xent('hello world'))", 2, xrt)
        score_after_negative = player.get_score()
        assert score_after_negative < score_after_positive

        # Part 3: Test reward with explicit player
        assert player.name == "black"
        await eval_line("reward(black, xent('hello world'))", 3, xrt)
        score_after_explicit = player.get_score()
        assert score_after_explicit > score_after_negative

        # Part 4: Test reward with longer xent value
        await eval_line("reward(xent('hello world this is a test'))", 4, xrt)
        final_score = player.get_score()
        assert final_score > score_after_explicit  # Longer string has higher xent

    @pytest.mark.asyncio
    async def test_reward_xent_expression(self, xrt):
        """Test reward with cross-entropy expression."""
        player = xrt.player
        initial_score = player.get_score()

        await eval_line(
            "reward(xent('hello world') - xent('hello world' | 'first thing that prints for a program'))",
            1,
            xrt,
        )

        final_score = player.get_score()
        # The difference should be positive (longer string has higher xent)
        assert final_score > initial_score

    @pytest.mark.asyncio
    async def test_reward_only_positional_args(self, xrt):
        """Test that reward only accepts positional arguments."""
        with pytest.raises(XentSyntaxError):
            await eval_line("reward(player=black, amount=10)", 1, xrt)

    @pytest.mark.asyncio
    async def test_reward_xed_function(self, xrt):
        """Test reward with xed function."""
        await eval_line("assign(s='hello world')", 1, xrt)
        player = xrt.player
        initial_score = player.get_score()

        # xed(s1 | s2) = xent(s1) - xent(s1 | s2)
        await eval_line("reward(xed(s | 'first program prints'))", 2, xrt)

        final_score = player.get_score()
        # xed should be positive (prefix helps predict the suffix)
        assert final_score > initial_score

    @pytest.mark.asyncio
    async def test_reward_in_game_context(self, xrt):
        """Test reward in a complete game context."""
        game_code = """
        assign(s='My favorite breakfast is huevos rancheros')
        reveal(s)
        elicit(s1, 20)
        reward(black, xed(s | s1))
        """
        start_score = xrt.local_vars["black"].get_score()

        game_results = await play_game(game_code, xrt, num_rounds=1)
        assert len(game_results) == 1

        # Player should have received some reward
        assert game_results[0]["score"] != start_score

    @pytest.mark.asyncio
    async def test_reward_history(self, xrt):
        """Test that reward operations are logged in history."""
        await eval_line("reward(xent('hello world'))", 1, xrt)

        assert len(xrt.history) > 0
        assert xrt.history[-1]["type"] == "reward"


class TestEnsureInstruction:
    """Test the ensure instruction functionality."""

    @pytest.mark.asyncio
    async def test_ensure_true_condition(self, xrt):
        """Test ensure with a condition that evaluates to True."""
        # This should pass without issue
        await eval_line("elicit(s, 10)", 1, xrt)
        result = await eval_line("ensure(1 == 1)", 2, xrt)
        assert result is None  # Should continue to next line

    @pytest.mark.asyncio
    async def test_ensure_false_condition(self, xrt):
        """Test ensure with a condition that evaluates to False."""
        # First need an elicit to jump back to
        await eval_line("elicit(s, 10)", 1, xrt)

        # This should fail and jump back
        result = await eval_line("ensure(1 == 2)", 2, xrt)
        assert isinstance(result, XFlag)
        assert result.line_num == 1  # Should jump back to the elicit

    @pytest.mark.asyncio
    async def test_ensure_multiple_conditions_comprehensive(self, xrt):
        """Comprehensive test for ensure with multiple conditions and complex expressions."""
        # Part 1: Test multiple conditions that all evaluate to True
        await eval_line("elicit(s, 10)", 1, xrt)
        await eval_line("assign(s='hello')", 2, xrt)
        result = await eval_line("ensure(1 == 1, 2 == 2, len(s) == 5)", 3, xrt)
        assert result is None  # Should continue

        # Part 2: Test multiple conditions where one is False
        await eval_line("assign(x='test')", 4, xrt)
        result = await eval_line("ensure(1 == 1, 2 == 3, len(x) == 4)", 5, xrt)
        assert isinstance(result, XFlag)
        assert result.line_num == 1

        # Part 3: Test complex boolean expressions
        await eval_line("elicit(y, 10)", 6, xrt)
        await eval_line("assign(s1='hello', s2='world', s3='hello world')", 7, xrt)
        # Complex condition that should pass
        result = await eval_line(
            "ensure((s1 + ' ' + s2) == s3, len(s1) < len(s3))", 8, xrt
        )
        assert result is None
        # Complex condition that should fail
        result = await eval_line("ensure(len(s1) > len(s3) or s2 not in s3)", 9, xrt)
        assert isinstance(result, XFlag)

    @pytest.mark.asyncio
    async def test_ensure_with_xent_comparisons(self, xrt):
        """Test ensure with cross-entropy comparisons."""
        await eval_line("elicit(s, 10)", 1, xrt)
        # Test equality of xent values
        result = await eval_line("ensure(xent('hello') == xent('hello'))", 2, xrt)
        assert result is None

        # Test inequality
        result = await eval_line(
            "ensure(xent('hello world') == xent('asdfasdf adsfasdf'))", 3, xrt
        )
        assert isinstance(result, XFlag)

    @pytest.mark.asyncio
    async def test_ensure_with_string_operations(self, xrt):
        """Test ensure with string operation conditions."""
        await eval_line("assign(s='hello world')", 1, xrt)
        await eval_line("elicit(x, 10)", 2, xrt)

        # Test various string conditions
        result = await eval_line("ensure('world' in s, len(s) > 5)", 3, xrt)
        assert result is None

        # Test failed condition
        result = await eval_line("ensure('xyz' in s)", 4, xrt)
        assert isinstance(result, XFlag)
        assert result.line_num == 2

    @pytest.mark.asyncio
    async def test_ensure_only_positional_args(self, xrt):
        """Test that ensure only accepts positional arguments."""
        with pytest.raises(XentSyntaxError):
            await eval_line("ensure(condition=True)", 1, xrt)

    @pytest.mark.asyncio
    async def test_ensure_non_boolean_condition(self, xrt):
        """Test that ensure requires boolean conditions."""
        with pytest.raises(XentSyntaxError):
            await eval_line("ensure('not a boolean')", 1, xrt)

    @pytest.mark.asyncio
    async def test_ensure_max_failures(self, xrt):
        """Test that ensure respects MAX_ENSURE_FAILURES limit."""
        game_code = """
        elicit(s, 10)
        ensure(s == 'impossible_to_guess')
        """

        with pytest.raises(XentGameError):
            await play_game(
                game_code,
                xrt,
                num_rounds=1,
            )

    @pytest.mark.asyncio
    async def test_ensure_with_validated_bool(self, xrt):
        """Test that ensure works with ValidatedBool from xent comparisons."""
        await eval_line(
            "assign(s1='test test test test', s2='test test test test')", 1, xrt
        )
        await eval_line("elicit(x, 10)", 2, xrt)

        # xent comparisons return ValidatedBool
        result = await eval_line("ensure(xent(s1) == xent(s2))", 3, xrt)
        assert result is None

        # Test with combined ValidatedBool conditions
        result = await eval_line(
            "ensure(xent(s1) < xent('a very long string asefsadf asdfasdfasdf asdfasdfadsf'), xent(s2) > 0)",
            4,
            xrt,
        )
        assert result is None


class TestBeaconReplayInstructions:
    """Test beacon, replay, and main flag functionality."""

    @pytest.mark.asyncio
    async def test_beacon_creation_comprehensive(self, xrt):
        """Comprehensive test for beacon creation with both flag_1 and flag_2."""
        # Part 1: Test basic beacon creation with flag_1
        await eval_line("beacon(flag_1)", 5, xrt)

        # Should create a beacon
        assert "flag_1" in xrt.beacons
        flag = xrt.beacons["flag_1"]
        assert isinstance(flag, XFlag)
        assert flag.name == "flag_1"
        assert flag.line_num == 5

        # Part 2: Test beacon with flag_2
        await eval_line("beacon(flag_2)", 10, xrt)

        assert "flag_2" in xrt.beacons
        flag = xrt.beacons["flag_2"]
        assert flag.name == "flag_2"
        assert flag.line_num == 10

    @pytest.mark.asyncio
    async def test_beacon_overwrite(self, xrt):
        """Test that setting beacon twice overwrites the first one."""
        await eval_line("beacon(flag_1)", 5, xrt)
        assert xrt.beacons["flag_1"].line_num == 5

        await eval_line("beacon(flag_1)", 10, xrt)
        assert xrt.beacons["flag_1"].line_num == 10

    @pytest.mark.asyncio
    async def test_beacon_only_one_arg(self, xrt):
        """Test that beacon only accepts a single argument."""
        with pytest.raises(XentSyntaxError):
            await eval_line("beacon(flag_1, flag_2)", 1, xrt)

    @pytest.mark.asyncio
    async def test_beacon_only_positional_arg(self, xrt):
        """Test that beacon only accepts positional arguments."""
        with pytest.raises(XentSyntaxError):
            await eval_line("beacon(flag=flag_1)", 1, xrt)

    @pytest.mark.asyncio
    async def test_beacon_invalid_flag(self, xrt):
        """Test beacon with invalid flag name."""
        # Only flag_1 and flag_2 are valid
        with pytest.raises(XentGameError):
            await eval_line("beacon(flag_3)", 1, xrt)

        with pytest.raises(XentGameError):
            await eval_line("beacon(invalid_flag)", 1, xrt)

    @pytest.mark.asyncio
    async def test_replay_basic(self, xrt):
        """Test basic replay functionality."""
        # Set a beacon first
        await eval_line("beacon(flag_1)", 2, xrt)

        # Replay should jump to the beacon
        result = await eval_line("replay(flag_1, 1)", 5, xrt)
        assert isinstance(result, XFlag)
        assert result.line_num == 2

    @pytest.mark.asyncio
    async def test_replay_counter(self, xrt):
        """Test replay counter functionality."""
        game_code = """
        beacon(flag_1)
        reward(xent('hello world'))
        replay(flag_1, 3)
        """

        results = await play_game(game_code, xrt, num_rounds=1)
        assert len(results) == 1
        reward_count = 0
        for event in results[0]["history"]:
            if event["type"] == "reward":
                reward_count += 1

        assert reward_count == 8

    @pytest.mark.asyncio
    async def test_replay_without_beacon(self, xrt):
        """Test replay without setting beacon first."""
        with pytest.raises(XentInternalError):
            await eval_line("replay(flag_1, 1)", 1, xrt)

    @pytest.mark.asyncio
    async def test_replay_zero_count(self, xrt):
        """Test replay with zero count."""
        await eval_line("beacon(flag_1)", 1, xrt)

        # Zero count should not jump
        result = await eval_line("replay(flag_1, 0)", 2, xrt)
        assert result is None  # Should continue to next line

    @pytest.mark.asyncio
    async def test_replay_tracks_per_line(self, xrt):
        """Test that replay counters are tracked per line."""
        game_code = """
        beacon(flag_1)
        reveal('loop')
        replay(flag_1, 2)
        beacon(flag_2)
        reveal('inner')
        replay(flag_1, 1)
        """

        await play_game(game_code, xrt, num_rounds=1)

        # Check history to see execution pattern
        player = xrt.player
        loop_count = sum(1 for h in player.event_history if "loop" in str(h))
        inner_count = sum(1 for h in player.event_history if "inner" in str(h))

        assert loop_count > 0
        assert inner_count > 0

    @pytest.mark.asyncio
    async def test_replay_with_two_flags(self, xrt):
        """Test using both flag_1 and flag_2."""
        game_code = """
        beacon(flag_1)
        reward(xent('hello world'))
        beacon(flag_2)
        reward(-xent('hello world'))
        replay(flag_2, 1)
        replay(flag_1, 1)
        """

        results = await play_game(game_code, xrt, num_rounds=1)

        # Confirms the inner loop is executed more than the outer loop
        assert results[0]["score"] < 0

    @pytest.mark.asyncio
    async def test_multi_round(self, xrt):
        """Test that multi round configuration creates an implicit replay at the end."""
        game_code = """
        assign(s='hello')
        reveal(s)
        reward(xent('hello world'))
        """.strip()

        game_results = await play_game(game_code, xrt, num_rounds=2)

        # Should have multiple game results from multiple rounds
        assert len(game_results) > 1

        # Each iteration should give the same reward
        for result in game_results:
            assert result["score"] > 0


class TestDSLFunctions:
    """Test DSL functions including string operations and entropy functions."""

    @pytest.mark.asyncio
    async def test_string_concatenation(self, xrt):
        """Test string concatenation with + operator."""
        await eval_line("assign(s1='hello', s2='world')", 1, xrt)
        await eval_line("assign(s3=s1 + ' ' + s2)", 2, xrt)

        assert str(xrt.local_vars["s3"]) == "hello world"

    @pytest.mark.asyncio
    async def test_string_before_operator(self, xrt):
        """Test // operator (substring before delimiter)."""
        await eval_line("assign(s='hello world again')", 1, xrt)

        # Test basic case
        await eval_line("assign(s1=s // 'world')", 2, xrt)
        assert str(xrt.local_vars["s1"]) == "hello "

        # Test when delimiter is at start
        await eval_line("assign(s1=s // 'hello')", 3, xrt)
        assert str(xrt.local_vars["s1"]) == ""

        # Test when delimiter is not found
        await eval_line("assign(s1=s // 'xyz')", 4, xrt)
        assert str(xrt.local_vars["s1"]) == "hello world again"

        # Test with empty delimiter
        await eval_line("assign(s1=s // '')", 5, xrt)
        assert str(xrt.local_vars["s1"]) == "hello world again"

    @pytest.mark.asyncio
    async def test_string_after_operator(self, xrt):
        """Test % operator (substring after delimiter)."""
        await eval_line("assign(s='hello world again')", 1, xrt)

        # Test basic case
        await eval_line("assign(s1=s % 'world')", 2, xrt)
        assert str(xrt.local_vars["s1"]) == " again"

        # Test when delimiter is at end
        await eval_line("assign(s1=s % 'again')", 3, xrt)
        assert str(xrt.local_vars["s1"]) == ""

        # Test when delimiter is not found
        await eval_line("assign(s1=s % 'xyz')", 4, xrt)
        assert str(xrt.local_vars["s1"]) == ""

        # Test with empty delimiter
        await eval_line("assign(s1=s % '')", 5, xrt)
        assert str(xrt.local_vars["s1"]) == ""

    @pytest.mark.asyncio
    async def test_only_uses_chars(self, xrt):
        await eval_line("elicit(s1, 10)", 1, xrt)

        result = await eval_line("ensure(only_uses_chars('abck', 'back'))", 2, xrt)
        assert result is None

        result = await eval_line("ensure(only_uses_chars('abc', 'back'))", 2, xrt)
        assert result is not None

        result = await eval_line("ensure(only_uses_chars('.,;:!? ', '!., '))", 2, xrt)
        assert result is None

        result = await eval_line("ensure(only_uses_chars('.,;:!?', '!., '))", 2, xrt)
        assert result is not None

        result = await eval_line("ensure(only_uses_chars('😀😃😄', '😀'))", 2, xrt)
        assert result is None

        result = await eval_line("ensure(only_uses_chars('🌟✨💫', '🌙'))", 2, xrt)
        assert result is not None

        result = await eval_line("ensure(only_uses_chars('👍🏽👍🏻', '👍🏽'))", 2, xrt)
        assert result is None

        # The skin tone thumbs up emoji decomposes into tone + thumbs up, so this is valid
        result = await eval_line("ensure(only_uses_chars('👍🏽👍🏻', '👍'))", 2, xrt)
        assert result is None

        result = await eval_line("ensure(only_uses_chars('👍', '👍🏽👍🏻'))", 2, xrt)
        assert result is not None

        result = await eval_line("ensure(only_uses_chars('🇺🇸🇬🇧', '🇺🇸'))", 2, xrt)
        assert result is None

        result = await eval_line("ensure(only_uses_chars('🇺🇸', '🇺🇸🇬🇧'))", 2, xrt)
        assert result is not None

        result = await eval_line(
            "ensure(only_uses_chars('你好世界', '你好世界'))", 2, xrt
        )
        assert result is None

        result = await eval_line("ensure(only_uses_chars('你好世界', '再见'))", 2, xrt)
        assert result is not None

    @pytest.mark.parametrize(
        "s1,s2,expected",
        [
            ("the cat and the dog", "the dog and a bird", "cat"),
            ("I eat pizza", "I like dogs", "eat pizza"),
            ("Hello, world!", "world!", "Hello, !"),
            ("foo_bar foo", "foo", "_bar"),
            ("foo-bar foo", "foo", "-bar"),
            ("The the THE", "the", ""),
            ("yes, yes; yes.", "yes", ", ; ."),
            ("(hello) world", "hello", "() world"),
            ("version1 version", "version", "version1"),
            ("café dog", "café", "dog"),
            ("no common", "words on here", "no common"),
            ("🍫💙 🍫🥳", "🍫 🍫💙", "🍫🥳"),
        ],
    )
    @pytest.mark.asyncio
    async def test_remove_common_words_function(self, xrt, s1, s2, expected):
        await eval_line(f"assign(s1='{s1}', s2='{s2}')", 1, xrt)
        await eval_line("assign(s3=remove_common_words(s1, s2))", 2, xrt)

        assert str(xrt.local_vars["s3"]) == expected

    @pytest.mark.asyncio
    async def test_only_uses_words_basic(self, xrt):
        # Do elicit to make sure it has a last elicit player set for failed ensures
        await eval_line("elicit(s, 10)", 1, xrt)
        result = await eval_line(
            "ensure(only_uses_words('red blue', 'red blue'))", 1, xrt
        )
        assert result is None

        result = await eval_line(
            "ensure(only_uses_words('red blue', 'red green'))", 2, xrt
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_only_uses_words_and_remove_common_words_xlist(self, xrt):
        # Do elicit to make sure it has a last elicit player set for failed ensures
        await eval_line("elicit(s, 10)", 1, xrt)
        await eval_line("assign(l=['red', 'green'])", 1, xrt)

        result = await eval_line("ensure(only_uses_words(l, 'red green'))", 2, xrt)
        assert result is None

        result = await eval_line("ensure(only_uses_words(l, 'red blue'))", 3, xrt)
        assert result is not None

        await eval_line("assign(s1=remove_common_words('blue red green', l))", 4, xrt)
        assert str(xrt.local_vars["s1"]) == "blue"

    @pytest.mark.asyncio
    async def test_xent_comprehensive(self, xrt):
        """Comprehensive test for xent() function with and without prefix."""
        # Part 1: Test basic xent() function
        score_before = xrt.local_vars["black"].score
        await eval_line("reward(black, xent('hello world'))", 1, xrt)
        first_score = xrt.local_vars["black"].score - score_before
        await eval_line(
            "reward(black, xent('hello world hello world hello world'))", 2, xrt
        )
        second_score = xrt.local_vars["black"].score - score_before - first_score
        assert second_score > first_score  # Longer string has higher xent

        # Part 2: Test xent() with prefix (| operator)
        score_with_prefix_before = xrt.local_vars["black"].score
        await eval_line("reward(black, xent('hello world'))", 3, xrt)
        score_no_prefix = xrt.local_vars["black"].score - score_with_prefix_before
        await eval_line(
            "reward(black, xent('hello world' | 'first program print text'))", 4, xrt
        )
        score_with_prefix = (
            xrt.local_vars["black"].score - score_with_prefix_before - score_no_prefix
        )
        assert score_with_prefix < score_no_prefix  # Prefix reduces xent

    @pytest.mark.asyncio
    async def test_nex_function(self, xrt):
        """Test basic nex() function."""
        score_before = xrt.local_vars["black"].score
        await eval_line("reward(black, nex('hello world'))", 1, xrt)
        first_score = xrt.local_vars["black"].score - score_before
        await eval_line(
            "reward(black, nex('hello world hello world hello world'))", 2, xrt
        )
        second_score = xrt.local_vars["black"].score - score_before - first_score

        assert second_score < first_score

    @pytest.mark.asyncio
    async def test_xed_function(self, xrt):
        """Test xed() function."""
        score_before = xrt.local_vars["black"].score
        await eval_line(
            "reward(black, xed('hello world' | 'first program print text'))", 1, xrt
        )
        score_after = xrt.local_vars["black"].score - score_before
        # Test that xed() gives a positive score
        assert score_after > score_before

    @pytest.mark.asyncio
    async def test_function_in_conditionals(self, xrt):
        """Test using functions in ensure conditions."""
        await eval_line("assign(s='hello world')", 1, xrt)
        await eval_line("elicit(s1, 10)", 2, xrt)

        # Test length condition
        result = await eval_line("ensure(len(s) > 5)", 3, xrt)
        assert result is None  # Should pass

        # Test xent comparison
        result = await eval_line("ensure(xent(s) > xent('hi'))", 4, xrt)
        assert result is None  # Should pass


class TestErrorCases:
    """Test error handling and invalid usage scenarios."""

    @pytest.mark.asyncio
    async def test_unknown_instruction(self, xrt):
        """Test that unknown instructions raise exceptions."""
        with pytest.raises(XentSyntaxError):
            await eval_line("unknown_instruction(x='test')", 1, xrt)

        with pytest.raises(XentSyntaxError):
            await eval_line("this_does_not_exist()", 1, xrt)

    @pytest.mark.asyncio
    async def test_malformed_syntax(self, xrt):
        """Test various malformed syntax errors."""
        # Missing closing parenthesis
        with pytest.raises(XentSyntaxError):
            await eval_line("assign(s='test'", 1, xrt)

        # Missing quotes
        with pytest.raises(XentGameError):
            await eval_line("assign(s=test)", 1, xrt)

        # Invalid Python syntax
        with pytest.raises(XentSyntaxError):
            await eval_line("assign s='test'", 1, xrt)

    @pytest.mark.asyncio
    async def test_empty_instruction(self, xrt):
        """Test empty instruction lines."""
        # Empty string should be OK (no-op)
        result = await eval_line("", 1, xrt)
        assert result is None

        # Just whitespace should also be OK
        result = await eval_line("   ", 1, xrt)
        assert result is None

        # Comment lines should be OK
        result = await eval_line("# This is a comment", 1, xrt)
        assert result is None

    @pytest.mark.asyncio
    async def test_instruction_argument_errors_comprehensive(self, xrt):
        """Comprehensive test for wrong types, missing args, and too many args."""
        # Part 1: Test wrong argument types
        # assign with positional args
        with pytest.raises(XentSyntaxError):
            await eval_line("assign('s', 'value')", 1, xrt)

        # reveal with keyword args
        with pytest.raises(XentSyntaxError):
            await eval_line("reveal(value='test')", 1, xrt)

        # ensure with keyword args
        with pytest.raises(XentSyntaxError):
            await eval_line("ensure(condition=True)", 1, xrt)

        # Part 2: Test missing required arguments
        # elicit without token limit
        with pytest.raises(XentSyntaxError):
            await eval_line("elicit(s)", 1, xrt)

        # beacon without flag
        with pytest.raises(XentSyntaxError):
            await eval_line("beacon()", 1, xrt)

        # replay without arguments
        with pytest.raises(XentSyntaxError):
            await eval_line("replay()", 1, xrt)

        # Part 3: Test too many arguments
        # beacon with multiple flags
        with pytest.raises(XentSyntaxError):
            await eval_line("beacon(flag_1, flag_2)", 1, xrt)

    @pytest.mark.asyncio
    async def test_register_errors_comprehensive(self, xrt):
        """Comprehensive test for invalid register names and undefined access."""
        # Part 1: Test invalid register names
        # Invalid register type
        with pytest.raises(XentSyntaxError):
            await eval_line("assign(z='invalid')", 1, xrt)

        # Register number too high
        with pytest.raises(XentSyntaxError):
            await eval_line("assign(s99='too_high')", 1, xrt)

        # Invalid format
        with pytest.raises(XentSyntaxError):
            await eval_line("assign(1s='invalid')", 1, xrt)

        # Part 2: Test undefined register access
        # Accessing undefined register in expression
        with pytest.raises(XentGameError):
            await eval_line("assign(s=undefined_var)", 1, xrt)

        # Using undefined register in reveal
        with pytest.raises(XentGameError):
            await eval_line("reveal(undefined_var)", 1, xrt)

    @pytest.mark.asyncio
    async def test_undefined_functions(self, xrt):
        """Test calling undefined functions."""
        with pytest.raises(XentGameError):
            await eval_line("assign(s=undefined_function())", 1, xrt)

        with pytest.raises(XentGameError):
            await eval_line("assign(s=random_func('arg'))", 1, xrt)

    @pytest.mark.asyncio
    async def test_wrong_function_args(self, xrt):
        """Test functions with wrong number of arguments."""
        # xent with no args
        with pytest.raises(XentGameError):
            await eval_line("assign(s=xent())", 1, xrt)

        # get_story with args (should take none)
        with pytest.raises(XentGameError):
            await eval_line("assign(s=get_story('arg'))", 1, xrt)

        # first_n_tokens with wrong number of args
        with pytest.raises(XentGameError):
            await eval_line("assign(s=first_n_tokens('string'))", 1, xrt)


class TestCombinedOperations:
    """Test interactions between different DSL instructions."""

    @pytest.mark.asyncio
    async def test_reveal_elicit_interaction(self, xrt):
        """Test interaction between reveal and elicit."""
        game_code = """
        assign(s='Please enter a word')
        reveal(s)
        elicit(s1, 10)
        reveal(s1)
        """

        await play_game(game_code, xrt, num_rounds=1)

        player = xrt.player
        # Should have received two reveals + elicit + elicit response
        assert len(player.event_history) == 6
        assert "Please enter a word" in str(player.event_history[1])
        assert "mocked_move" in str(player.event_history[4])

    @pytest.mark.asyncio
    async def test_elicit_registers(self, xrt):
        """Test basic elicit operation with default player."""
        await eval_line("assign(s1='test1')", 1, xrt)
        await eval_line("assign(s2='test2')", 1, xrt)
        await eval_line("assign(s3='test3')", 1, xrt)
        await eval_line("assign(t1='test4')", 1, xrt)
        await eval_line("assign(t2='test5')", 1, xrt)
        await eval_line("assign(t3='test6')", 1, xrt)
        await eval_line("elicit(s, 10)", 1, xrt)

        player = xrt.player
        assert player.event_history[-1]["type"] == "elicit_response"
        assert player.event_history[-2]["type"] == "elicit_request"
        event = player.event_history[-2]
        registers = event["registers"]
        # 4 slots per register across 9 registers (a,b,c,l,s,t,x,y,p)
        assert len(registers) == 36
        # Confirm newly added list register appears in snapshot
        assert "l" in registers and isinstance(registers["l"], XList)
        assert registers["s1"] == "test1"
        assert registers["s2"] == "test2"
        assert registers["s3"] == "test3"
        assert registers["t1"] == "test4"
        assert registers["t2"] == "test5"
        assert registers["t3"] == "test6"


class TestListDSL:
    @pytest.mark.asyncio
    async def test_list_registers_initialized_types_and_flags(self, xrt):
        # 'l' is a mutable list register; 'a' is a static list register
        assert isinstance(xrt.local_vars["l"], XList)
        assert isinstance(xrt.local_vars["a"], XString)
        assert isinstance(xrt.local_vars["s"], XString)

        a_value = xrt.local_vars["a"]
        l_value = xrt.local_vars["l"]
        assert a_value.static is True and a_value.public is True
        assert l_value.static is False

    @pytest.mark.asyncio
    async def test_assign_list_concatenation_noop(self, xrt):
        # Default lists are empty; concatenation should work and keep l empty
        await eval_line("assign(l=l + l1)", 1, xrt)
        assert isinstance(xrt.local_vars["l"], XList)
        assert len(xrt.local_vars["l"]) == 0

    @pytest.mark.asyncio
    async def test_assign_list_with_string_raises_type_error(self, xrt):
        # Now assigning XString to XList target should raise an error
        with pytest.raises(XentSyntaxError):
            await eval_line("assign(l='hello')", 1, xrt)

    @pytest.mark.asyncio
    async def test_assign_to_static_list_register_disallowed(self, xrt):
        with pytest.raises(XentSyntaxError):
            await eval_line("assign(a=l)", 1, xrt)

    @pytest.mark.asyncio
    async def test_elicit_rejects_list_register_target(self, xrt):
        with pytest.raises(XentSyntaxError):
            await eval_line("elicit(l, 5)", 1, xrt)

    @pytest.mark.asyncio
    async def test_elicit_request_includes_list_for_omniscient_player(self, xrt):
        await eval_line("elicit(s, 5)", 1, xrt)
        event = next(
            e for e in xrt.player.event_history if e["type"] == "elicit_request"
        )
        regs = event["registers"]
        assert "l" in regs and isinstance(regs["l"], XList)

    @pytest.mark.asyncio
    async def test_elicit_request_excludes_non_public_list_for_non_omniscient_player(
        self, xrt
    ):
        # alice is non-omniscient; snapshot should exclude non-public 'l'
        await eval_line("elicit(alice, s, 5)", 1, xrt)
        alice_player = xrt.local_vars["alice"]
        event = next(
            e for e in alice_player.event_history if e["type"] == "elicit_request"
        )
        regs = event["registers"]
        assert "l" not in regs
        # Public registers include 'a', 'b', 'p'
        assert "a" in regs and isinstance(regs["a"], XString)
        assert "b" in regs
        assert "p" in regs

    @pytest.mark.asyncio
    async def test_reveal_allows_list_values(self, xrt):
        await eval_line("reveal(l)", 1, xrt)
        event = next(e for e in xrt.player.event_history if e["type"] == "reveal")
        assert "l" in event["values"] and isinstance(event["values"]["l"], XList)

    @pytest.mark.asyncio
    async def test_reveal_mixed_values(self, xrt):
        await eval_line("assign(s='hi')", 1, xrt)
        await eval_line("assign(l=['hello', 'world'])", 1, xrt)
        await eval_line("reveal(s, l)", 2, xrt)
        event = next(e for e in xrt.player.event_history if e["type"] == "reveal")
        assert isinstance(event["values"]["s"], XString)
        assert isinstance(event["values"]["l"], XList)

    @pytest.mark.asyncio
    async def test_ensure_len_on_list_register(self, xrt):
        await eval_line("elicit(s, 5)", 1, xrt)
        result = await eval_line("ensure(len(l) == 0)", 2, xrt)
        assert result is None

    def test_reset_clears_list_registers(self, xrt):
        # Manually populate list, then ensure reset clears it
        xrt.local_vars["l"].items = [XString("foo")]
        assert len(xrt.local_vars["l"]) == 1
        _ = xrt.get_results_and_reset()
        assert isinstance(xrt.local_vars["l"], XList)
        assert len(xrt.local_vars["l"]) == 0

    @pytest.mark.asyncio
    async def test_event_serialization_handles_xlist(self, xrt):
        await eval_line("elicit(s, 5)", 1, xrt)
        event = next(
            e for e in xrt.player.event_history if e["type"] == "elicit_request"
        )
        payload = dumps({"type": "xent_event", "event": event})
        # Should serialize list registers as JSON arrays of strings
        parsed = loads(payload)
        assert isinstance(parsed["event"]["registers"]["l"], list)
        # Each item should be a string after encoding
        for item in parsed["event"]["registers"]["l"]:
            assert isinstance(item, str)
