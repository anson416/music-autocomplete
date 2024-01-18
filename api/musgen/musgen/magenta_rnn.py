# -*- coding: utf-8 -*-
# File: magenta_rnn.py

"""
Copyright 2017 Google LLC.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from pathlib import Path
from types import ModuleType
from typing import Literal

import note_seq
from magenta.models.shared import sequence_generator_bundle
from note_seq.protobuf import generator_pb2
from note_seq.protobuf.music_pb2 import NoteSequence


class MagentaRNN(object):
    def __init__(
        self,
        seq_generator: ModuleType,
        model: str,
        model_dir: str,
    ) -> None:
        generator_map = seq_generator.get_generator_map()
        model_path = Path(model_dir) / f"{model}.mag"
        if not model_path.exists():
            print(f"Downloading {model_path}")
            note_seq.notebook_utils.download_bundle(f"{model}.mag", model_dir)
        self._generator = generator_map[model](
            checkpoint=None,
            bundle=sequence_generator_bundle.read_bundle_file(model_path)
        )
        self._generator.initialize()

    def __call__(
        self,
        input_seq: NoteSequence,
        extend_duration: float,
        temperature: float = 1.0,
    ) -> NoteSequence:
        last_end_time = max(note.end_time for note in input_seq.notes) if input_seq.notes else 0
        generator_options = generator_pb2.GeneratorOptions()
        generator_options.args["temperature"].float_value = temperature
        generator_options.generate_sections.add(start_time=last_end_time, end_time=last_end_time + extend_duration)
        new_seq = self._generator.generate(input_seq, generator_options)
        return new_seq
    
    @classmethod
    def MelodyRNN(
        cls,
        model: Literal["basic_rnn", "mono_rnn", "lookback_rnn", "attention_rnn"] = "basic_rnn",
        model_dir: str = "./models/melody_rnn",
    ) -> "MagentaRNN":
        from magenta.models.melody_rnn import melody_rnn_sequence_generator
        return cls(melody_rnn_sequence_generator, model, model_dir)
    
    @classmethod
    def PerformanceRNN(
        cls,
        model: Literal["performance", "performance_with_dynamics", "performance_with_dynamics_and_modulo_encoding", "density_conditioned_performance_with_dynamics", "pitch_conditioned_performance_with_dynamics", "multiconditioned_performance_with_dynamics"] = "performance",
        model_dir: str = "./models/performance_rnn",
    ) -> "MagentaRNN":
        from magenta.models.performance_rnn import performance_sequence_generator
        return cls(performance_sequence_generator, model, model_dir)
