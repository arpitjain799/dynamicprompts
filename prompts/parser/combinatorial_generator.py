from __future__ import annotations
from collections.abc import Iterable

from .parse import (
    ActionBuilder,
    Parser,
)

from .commands import (
    Command,
    SequenceCommand,
    WildcardCommand,
    LiteralCommand,
    VariantCommand,
)


class CombinatorialSequenceCommand(SequenceCommand):
    def prompts(self, tokens: list[Command] | None = None) -> Iterable[str]:
        if tokens is None:
            tokens = self.tokens

        if len(tokens) == 0:
            yield ""
        else:
            token = tokens[0]
            for prompt in token.prompts():
                for next_prompts in self.prompts(tokens[1:]):
                    yield (prompt + " " + next_prompts).strip()


class CombinatorialWildcardCommand(WildcardCommand):
    def __init__(self, wildcard_manager, token):
        super().__init__(wildcard_manager, token)
        self._wildcard_manager = wildcard_manager
        if type(token) == list:
            import pdb; pdb.set_trace()
        self._wildcard = token

    def prompts(self):
        generator = CombinatorialGenerator(self._wildcard_manager)
        values = self._wildcard_manager.get_all_values(self._wildcard)
        for val in values:
            for prompt in generator.generate_prompts(val):
                yield prompt

    def __repr__(self):
        return f"{self.__class__.__name__}({self._wildcard!r})"


class CombinatorialVariantCommand(VariantCommand):
    def _resolve_combinations(self, combo) -> Iterable[str]:
        if len(combo) == 0:
            yield ""
        else:
            c, rest = combo[0], combo[1:]
            for p in c.prompts():
                for r in self._resolve_combinations(rest):
                    if r == "":
                        yield p
                    else:
                        yield self.sep.join([p, r])

    def _combo_to_prompt(self, combo: list[Command]) -> Iterable[list[str]]:
        if len(combo) == 0:
            yield []
        else:
            c_1, c_rest = combo[0], combo[1:]

            for p in c_1.prompts():
                for rest_prompt in self._combo_to_prompt(c_rest):
                    if rest_prompt != "":
                        yield [p] + rest_prompt
                    else:
                        yield [p]

    def prompts(self) -> Iterable[str]:
        if len(self._values) == 0:
            return []

        for bound in range(self.min_bound, self.max_bound + 1):
            for combo in self._combinations(bound):
                for prompt_arr in self._combo_to_prompt(combo):
                    has_duplicates = len(prompt_arr) != len(set(prompt_arr))
                    if has_duplicates:
                        continue
                    yield self.sep.join(prompt_arr)

    def __repr__(self):
        z = zip(self._weights, self._values)
        return f"{self.__class__.__name__}({list(z)!r})"


class CombinatorialActionBuilder(ActionBuilder):
    def get_literal_class(self):
        return LiteralCommand

    def get_variant_class(self):
        return CombinatorialVariantCommand

    def get_wildcard_class(self):
        return CombinatorialWildcardCommand

    def get_sequence_class(self):
        return CombinatorialSequenceCommand


class CombinatorialGenerator:
    def __init__(self, wildcard_manager):
        self._wildcard_manager = wildcard_manager

    def get_action_builder(self) -> ActionBuilder:
        return CombinatorialActionBuilder(self._wildcard_manager)

    def configure_parser(self) -> Parser:
        builder = self.get_action_builder()
        parser = Parser(builder)

        return parser

    def generate_prompts(self, prompt: str, num_prompts: int|None=None):
        if len(prompt) == 0:
            return []

        parser = self.configure_parser()
        sequence = parser.parse(prompt)
        prompts = sequence.prompts()

        if num_prompts is None:
            return [p for idx, p in enumerate(prompts)]
        else:
            return [p for idx, p in enumerate(prompts) if idx < num_prompts]
