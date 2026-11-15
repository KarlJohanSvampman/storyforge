"""Provider-independent narrative compilation boundary.

The initial implementation deliberately performs deterministic source assembly. A
real AI provider can later implement the same protocol without changing the API
or persistence contracts.
"""
from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class CompilerSource:
    title: str
    text: str
    source_kind: str


@dataclass(frozen=True)
class CompilerOutput:
    content: str
    provider_name: str
    model_name: str
    prompt_version: str


class NarrativeCompiler(Protocol):
    provider_name: str
    model_name: str
    prompt_version: str

    def compile(self, *, title: str, sources: Sequence[CompilerSource]) -> CompilerOutput:
        """Return a draft proposal. Implementations must not approve or publish it."""


class DeterministicNarrativeCompiler:
    """Mock provider that assembles source material without rewriting it."""

    provider_name = "mock"
    model_name = "source-preserving-assembler-v1"
    prompt_version = "assembly-template-v1"

    def compile(self, *, title: str, sources: Sequence[CompilerSource]) -> CompilerOutput:
        sections = [
            f"# {title}",
            "",
            "> Compilation proposal. This version preserves selected source text; it has not been approved.",
            "",
        ]
        for index, source in enumerate(sources, start=1):
            label = "Accepted suggestion" if source.source_kind == "accepted_suggestion" else "Contribution"
            sections.extend([
                f"## {index}. {source.title}",
                f"*Source type: {label}*",
                "",
                source.text.strip(),
                "",
            ])
        return CompilerOutput(
            content="\n".join(sections).rstrip() + "\n",
            provider_name=self.provider_name,
            model_name=self.model_name,
            prompt_version=self.prompt_version,
        )


def get_narrative_compiler() -> NarrativeCompiler:
    """Application composition root; replace this factory to configure a real provider."""
    return DeterministicNarrativeCompiler()
