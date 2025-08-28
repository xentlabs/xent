import ast
import logging
from typing import Any

from xega.common.configuration_types import XegaGameIterationResult
from xega.common.errors import (
    XegaConfigurationError,
    XegaError,
    XegaGameError,
    XegaInternalError,
    XegaSyntaxError,
)
from xega.common.x_flag import XFlag
from xega.runtime.runtime import XegaRuntime


class StringLiteralToXStringTransformer(ast.NodeTransformer):
    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if isinstance(node.value, str):
            return ast.Call(
                func=ast.Name(id="XString", ctx=ast.Load()),
                args=[ast.Constant(value=node.value)],  # Pass the original string value
                keywords=[],
            )
        return self.generic_visit(node)


async def play_game(
    code: str,
    xrt: XegaRuntime,
    num_rounds=30,
) -> list[XegaGameIterationResult]:
    lines = [line.strip() for line in code.split("\n")]
    if len(lines) > 64:
        raise XegaConfigurationError("Code too long. Max 64 lines.")

    rounds_played = 0
    game_results: list[XegaGameIterationResult] = []

    while rounds_played < num_rounds:
        result = await play_single_game(lines, xrt)
        if result is None:
            return []  # TODO what to do here?
        rounds_played += 1
        if result is not None:
            game_results.append(result)

    logging.info("Game completed successfully")
    return game_results


# TODO need to clean up error handling / none return here
async def play_single_game(
    lines: list[str], xrt: XegaRuntime
) -> XegaGameIterationResult | None:
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
                raise XegaInternalError(
                    f"Invalid line number {line_index} returned by instruction"
                )

    logging.info("Game round completed successfully")
    results = xrt.get_results_and_reset()
    return results


async def eval_line(line: str, line_num: int, xrt: XegaRuntime) -> XFlag | None:
    # Inline comments are handled by ast, but if the line starts with # or is empty, we ignore it
    if (line.strip() == "") or line.strip().startswith("#"):
        return None
    try:
        tree = ast.parse(line, mode="eval")
    except SyntaxError as e:
        logging.exception(f"Syntax error in expression: {e}")
        raise XegaSyntaxError(
            f"Syntax error in expression: {line} (line {line_num})"
        ) from None

    if not isinstance(tree, ast.Expression):
        raise XegaSyntaxError(
            f"Invalid expression: {line} (line {line_num}): Not an Expression"
        )

    instruction_name, call_node = get_validated_call_info(
        tree, xrt.instruction_names(), line, line_num
    )

    args = call_node.args
    kwargs = call_node.keywords

    try:
        (resolved_args, resolved_kwargs) = gather_params(
            args, kwargs, xrt, line, line_num
        )
    except XegaError as e:
        logging.exception(f"Error gathering parameters: {e}")
        raise e
    except Exception as e:
        logging.exception(f"Unexpected error resolving parameters: {e}")
        raise XegaGameError(
            f"Unexpected error resolving parameters: {line} (line {line_num}): {e}"
        ) from e

    try:
        result = await xrt.execute(
            instruction_name, resolved_args, resolved_kwargs, line, line_num
        )
    except XegaError as e:
        logging.exception(f"Error executing instruction: {e}")
        raise e
    except Exception as e:
        logging.exception(f"Unexpected error executing instruction: {e}")
        raise XegaGameError(
            f"Unexpected error executing instruction: {line} (line {line_num}): {e}"
        ) from e

    return result


def get_validated_call_info(
    tree: ast.Expression, instruction_names: set[str], line: str, line_num: int
) -> tuple[str, ast.Call]:
    if not isinstance(tree.body, ast.Call):
        raise XegaSyntaxError(
            f"The expression does not start with an instruction (not ast.Call). Line: {line}, Line number: {line_num}"
        )
    if not isinstance(tree.body.func, ast.Name):
        raise XegaSyntaxError(
            f"The instruction call does not use a simple name (not ast.Name). Line: {line}, Line number: {line_num}"
        )

    call_node = tree.body
    func_node = tree.body.func

    instruction_name: str = func_node.id
    if instruction_name not in instruction_names:
        raise XegaSyntaxError(
            f'Instruction "{instruction_name}" not found. Line: {line}, Line number: {line_num}'
        )

    return instruction_name, call_node


# Returns a tuple of (resolved_args, resolved_kwargs)
def gather_params(
    args: list[ast.expr],
    kwargs: list[ast.keyword],
    xrt: XegaRuntime,
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
            raise XegaSyntaxError(
                f"Keyword argument key {variable_name} is not a string. Line: {line}, Line number: {line_num}"
            )

        value = kwarg.value
        resolved_value = resolve_arg(value, xrt, line, line_num)
        resolved_kwargs[variable_name] = resolved_value

    return (resolved_args, resolved_kwargs)


def resolve_arg(arg_node: ast.expr, xrt: XegaRuntime, line: str, line_num: int) -> Any:
    try:
        transformer = StringLiteralToXStringTransformer()
        transformed_arg_node = transformer.visit(arg_node)
        ast.fix_missing_locations(transformed_arg_node)

        expression = ast.Expression(body=transformed_arg_node)
        code = compile(expression, filename="<ast>", mode="eval")
        resolved_arg = eval(code, xrt.globals, xrt.local_vars)
        return resolved_arg
    except Exception as e:
        logging.exception(f"Error resolving argument: {e}")
        # TODO: depending on the error, we might want to raise a XegaSyntaxError instead
        raise XegaGameError(
            f"Error resolving argument: {line} (line {line_num}): {e}"
        ) from e
