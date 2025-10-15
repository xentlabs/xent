from xent.common.configuration_types import ExecutableGameMap, GameMapRoundResult
from xent.common.errors import XentConfigurationError, XentInternalError
from xent.common.util import get_game_code_lines
from xent.common.xent_event import (
    RoundFinishedEvent,
    RoundStartedEvent,
    XentEvent,
    XentEventType,
)
from xent.runtime.execution import eval_line
from xent.runtime.judge import Judge
from xent.runtime.players import make_npcs, make_player
from xent.runtime.runtime import XentRuntime
from xent.runtime.variables import build_globals, build_locals


# An object which manages a game which is controlled externally.
# Controlled means that the external system decides when to progress the game.
# Prompts, results, etc are returned out of this object.
# This allows external systems to progress game execution without having to use a mailbox
# or other concurrency inversion methods to flip control of game execution.
class ControlledGame:
    def __init__(self, executable_game_map: ExecutableGameMap, judge: Judge):
        if executable_game_map["player"]["player_type"] != "controlled":
            raise XentConfigurationError(
                "Player for ControlledGame must be controlled type"
            )
        self.executable_game_map = executable_game_map
        self.judge = judge
        self.game_code = executable_game_map["game_map"]["code"]
        self.lines = get_game_code_lines(self.game_code)

        judge.set_seed(executable_game_map["metadata"]["seed"], "")
        player = make_player(executable_game_map)
        npcs = make_npcs(executable_game_map)
        locals = build_locals(player, npcs, executable_game_map)
        globals = build_globals(judge)
        self.xrt = XentRuntime(
            player,
            npcs,
            locals,
            globals,
            store_full_interactions=executable_game_map["metadata"].get(
                "store_full_player_interactions", True
            ),
        )

        self.round_num = 0
        self.line_index = 0
        self.round_results: list[GameMapRoundResult] = []

    async def progress(self):
        return await self.progress_until(["elicit_request", "round_finished"])

    async def progress_until(self, until: list[XentEventType]):
        while True:
            events_seen = await self.step()
            for event_seen in events_seen:
                if event_seen["type"] in until:
                    return

    async def step(self) -> list[XentEvent]:
        events_before = self.xrt.history
        await self.maybe_handle_round_start()
        line = self.lines[self.line_index]
        execution_result = await eval_line(line, self.line_index, self.xrt)
        if execution_result is None:
            self.line_index += 1
        else:
            self.line_index = execution_result.line_num
            if self.line_index < 0 or self.line_index >= len(self.lines):
                raise XentInternalError(
                    f"Invalid line number {self.line_index} returned by instruction"
                )

        events_after = await self.maybe_handle_round_finish()
        return events_after[len(events_before) :]

    async def maybe_handle_round_start(self):
        if self.line_index == 0:
            start_event = RoundStartedEvent(
                type="round_started",
                round_index=self.round_num,
                line=self.lines[self.line_index],
                line_num=self.line_index,
                player=self.executable_game_map["player"]["name"],
            )
            await self.xrt.send_event(self.xrt.player, start_event)

    async def maybe_handle_round_finish(self):
        if self.line_index >= len(self.lines):
            finish_event = RoundFinishedEvent(
                type="round_finished",
                round_index=self.round_num,
                line=self.lines[self.line_index],
                line_num=self.line_index,
                player=self.executable_game_map["player"]["name"],
            )
            await self.xrt.send_event(self.xrt.player, finish_event)
            end_events = self.xrt.history
            results = self.xrt.get_results_and_reset()
            self.round_results.append(results)
            return end_events
        else:
            return self.xrt.history
