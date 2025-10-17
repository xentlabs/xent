import ast
import logging
from typing import Any, Literal, TypedDict

from xent.common.configuration_types import GameMapRoundResult
from xent.common.errors import (
    XentConfigurationError,
    XentError,
    XentGameError,
    XentHaltMessage,
    XentInternalError,
    XentSyntaxError,
)
from xent.common.x_flag import XFlag
from xent.common.xent_event import RoundFinishedEvent, RoundStartedEvent
from xent.runtime.runtime import XentRuntime


class StringLiteralToXStringTransformer(ast.NodeTransformer):
    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if isinstance(node.value, str):
            return ast.Call(
                func=ast.Name(id="XString", ctx=ast.Load()),
                args=[ast.Constant(value=node.value)],  # Pass the original string value
                keywords=[],
            )
        return self.generic_visit(node)


class ListLiteralToXListTransformer(ast.NodeTransformer):
    def visit_List(self, node: ast.List) -> ast.AST:
        self.generic_visit(node)

        return ast.copy_location(
            ast.Call(
                func=ast.Name(id="XList", ctx=ast.Load()),
                args=[ast.List(elts=node.elts, ctx=ast.Load())],
                keywords=[],
            ),
            node,
        )

    def visit_ListComp(self, node: ast.ListComp) -> ast.AST:
        self.generic_visit(node)
        return ast.copy_location(
            ast.Call(
                func=ast.Name(id="XList", ctx=ast.Load()),
                args=[node],  # let XList consume the comprehension iterable
                keywords=[],
            ),
            node,
        )


async def play_game(
    code: str,
    xrt: XentRuntime,
    num_rounds: int = 30,
    always_return_results: bool = False,  # Used for interactive play that may break at any moment
) -> list[GameMapRoundResult]:
    lines = [line.strip() for line in code.split("\n")]
    if len(lines) > 64:
        raise XentConfigurationError("Code too long. Max 64 lines.")

    rounds_played = 0
    round_results: list[GameMapRoundResult] = []

    while rounds_played < num_rounds:
        try:
            result = await play_single_game(lines, xrt, rounds_played)
            if result is None:
                return []  # TODO what to do here?
            rounds_played += 1
            round_results.append(result)
        except Exception as e:
            if always_return_results:
                logging.info(
                    "Swallowing exception thrown playing game and returning results"
                )
                return round_results
            else:
                raise e

    logging.info("Game completed successfully")
    return round_results


class Results(TypedDict):
    kind: Literal["results"]
    results: list["GameMapRoundResult"]


class State(TypedDict):
    kind: Literal["state"]
    state: dict[str, Any]


async def run_haltable_game(
    lines: list[str],
    line_index: int,
    xrt: XentRuntime,
    num_rounds: int,
    rounds_played: int,
    round_results: list[GameMapRoundResult],
) -> Results | State:
    while rounds_played < num_rounds:
        try:
            if line_index == 0:
                start_event = RoundStartedEvent(
                    type="round_started",
                    round_index=rounds_played,
                    line=lines[0],
                    line_num=1,
                    player=xrt.player.name,
                )
                await xrt.send_event(xrt.player, start_event)

            while line_index < len(lines):
                line = lines[line_index]
                logging.info(f"Executing line {line_index}: {line}.")
                execution_result = await eval_line(line, line_index, xrt)

                if execution_result is None:
                    line_index += 1
                else:
                    logging.info(
                        f"Line execution triggered jump. New line number: {execution_result.line_num}"
                    )
                    line_index = execution_result.line_num

                    if line_index < 0 or line_index >= len(lines):
                        raise XentInternalError(
                            f"Invalid line number {line_index} returned by instruction"
                        )

            finish_event = RoundFinishedEvent(
                type="round_finished",
                round_index=rounds_played,
                line=lines[-1],
                line_num=len(lines),
                player=xrt.player.name,
            )
            await xrt.send_event(xrt.player, finish_event)

            logging.info("Game round completed successfully")
            result = xrt.get_results_and_reset()
            if result is None:
                return {"kind": "results", "results": []}  # TODO what to do here?
            rounds_played += 1
            round_results.append(result)
            line_index = 0
        except XentHaltMessage:
            serialized_game_state: dict[str, Any] = {
                "lines": lines,
                "line_index": line_index,
                "num_rounds": num_rounds,
                "runtime": xrt.serialize(),
                "rounds_played": rounds_played,
                "round_results": round_results,
            }
            return {"kind": "state", "state": serialized_game_state}

    logging.info("Game completed successfully")
    return {"kind": "results", "results": round_results}


# TODO need to clean up error handling / none return here
async def play_single_game(
    lines: list[str],
    xrt: XentRuntime,
    rounds_played: int,
) -> GameMapRoundResult | None:
    start_event = RoundStartedEvent(
        type="round_started",
        round_index=rounds_played,
        line=lines[0],
        line_num=1,
        player=xrt.player.name,
    )
    await xrt.send_event(xrt.player, start_event)

    line_index = 0

    while line_index < len(lines):
        line = lines[line_index]
        logging.info(f"Executing line {line_index}: {line}.")
        execution_result = await eval_line(line, line_index, xrt)

        if execution_result is None:
            line_index += 1
        else:
            logging.info(
                f"Line execution triggered jump. New line number: {execution_result.line_num}"
            )
            line_index = execution_result.line_num

            if line_index < 0 or line_index >= len(lines):
                raise XentInternalError(
                    f"Invalid line number {line_index} returned by instruction"
                )

    finish_event = RoundFinishedEvent(
        type="round_finished",
        round_index=rounds_played,
        line=lines[-1],
        line_num=len(lines),
        player=xrt.player.name,
    )
    await xrt.send_event(xrt.player, finish_event)

    logging.info("Game round completed successfully")
    results = xrt.get_results_and_reset()
    return results


async def eval_line(line: str, line_num: int, xrt: XentRuntime) -> XFlag | None:
    # Inline comments are handled by ast, but if the line starts with # or is empty, we ignore it
    if (line.strip() == "") or line.strip().startswith("#"):
        return None
    try:
        tree = ast.parse(line, mode="eval")
    except SyntaxError as e:
        logging.exception(f"Syntax error in expression: {e}")
        raise XentSyntaxError(
            f"Syntax error in expression: {line} (line {line_num})"
        ) from None

    instruction_name, call_node = get_validated_call_info(
        tree, xrt.instruction_names(), line, line_num
    )

    args = call_node.args
    kwargs = call_node.keywords

    try:
        (resolved_args, resolved_kwargs) = gather_params(
            args, kwargs, xrt, line, line_num
        )
    except XentError as e:
        logging.exception(f"Error gathering parameters: {e}")
        raise e
    except Exception as e:
        logging.exception(f"Unexpected error resolving parameters: {e}")
        raise XentGameError(
            f"Unexpected error resolving parameters: {line} (line {line_num}): {e}"
        ) from e

    try:
        result = await xrt.execute(
            instruction_name, resolved_args, resolved_kwargs, line, line_num
        )
    except XentError as e:
        logging.exception(f"Error executing instruction: {e}")
        raise e
    except XentHaltMessage as e:
        raise e
    except Exception as e:
        logging.exception(f"Unexpected error executing instruction: {e}")
        raise XentGameError(
            f"Unexpected error executing instruction: {line} (line {line_num}): {e}"
        ) from e

    return result


def get_validated_call_info(
    tree: ast.Expression, instruction_names: set[str], line: str, line_num: int
) -> tuple[str, ast.Call]:
    if not isinstance(tree.body, ast.Call):
        raise XentSyntaxError(
            f"The expression does not start with an instruction (not ast.Call). Line: {line}, Line number: {line_num}"
        )
    if not isinstance(tree.body.func, ast.Name):
        raise XentSyntaxError(
            f"The instruction call does not use a simple name (not ast.Name). Line: {line}, Line number: {line_num}"
        )

    call_node = tree.body
    func_node = tree.body.func

    instruction_name: str = func_node.id
    if instruction_name not in instruction_names:
        raise XentSyntaxError(
            f'Instruction "{instruction_name}" not found. Line: {line}, Line number: {line_num}'
        )

    return instruction_name, call_node


# Returns a tuple of (resolved_args, resolved_kwargs)
def gather_params(
    args: list[ast.expr],
    kwargs: list[ast.keyword],
    xrt: XentRuntime,
    line: str,
    line_num: int,
) -> tuple[list[Any], dict[str, Any]]:
    resolved_args = []
    for arg in args:
        resolved_args.append(resolve_arg(arg, xrt, line, line_num))

    resolved_kwargs = {}
    for kwarg in kwargs:
        variable_name = kwarg.arg
        if not isinstance(variable_name, str):
            raise XentSyntaxError(
                f"Keyword argument key {variable_name} is not a string. Line: {line}, Line number: {line_num}"
            )

        value = kwarg.value
        resolved_value = resolve_arg(value, xrt, line, line_num)
        resolved_kwargs[variable_name] = resolved_value

    return (resolved_args, resolved_kwargs)


def resolve_arg(arg_node: ast.expr, xrt: XentRuntime, line: str, line_num: int) -> Any:
    try:
        arg_node = StringLiteralToXStringTransformer().visit(arg_node)
        arg_node = ListLiteralToXListTransformer().visit(arg_node)

        ast.fix_missing_locations(arg_node)
        code = compile(ast.Expression(body=arg_node), filename="<ast>", mode="eval")
        resolved_arg = eval(code, xrt.globals, xrt.local_vars)
        return resolved_arg
    except Exception as e:
        logging.exception(f"Error resolving argument: {e}")
        # TODO: depending on the error, we might want to raise a XentSyntaxError instead
        raise XentGameError(
            f"Error resolving argument: {line} (line {line_num}): {e}"
        ) from e
