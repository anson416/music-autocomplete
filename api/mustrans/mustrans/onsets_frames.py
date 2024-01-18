# -*- coding: utf-8 -*-
# File: onsets_frames.py

"""
Copyright 2020 Google LLC.

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

import urllib.request
from pathlib import Path
from typing import Literal
from zipfile import ZipFile

import six
import tensorflow.compat.v1 as tf
from magenta.models.onsets_frames_transcription import (audio_label_data_utils,
                                                        configs, data,
                                                        infer_util, train_util)
from note_seq.protobuf import music_pb2

tf.disable_v2_behavior()


class OnsetsFrames(object):
    def __init__(
        self,
        model: Literal["maestro", "egmd"] = "maestro",
        model_dir: str = "./models/onsets_frames",
    ) -> None:
        model_dir = Path(model_dir)
        unzip_dir = model_dir / model

        if model == "maestro":
            OnsetsFrames._download_and_unzip(
                "https://storage.googleapis.com/magentadata/models/onsets_frames_transcription/maestro_checkpoint.zip",
                model_dir,
                unzip_dir,
                redownload=False,
            )
            self._checkpoint_dir = unzip_dir / "train"
            self._config = configs.CONFIG_MAP["onsets_frames"]
        elif model == "egmd":
            OnsetsFrames._download_and_unzip(
                "https://storage.googleapis.com/magentadata/models/onsets_frames_transcription/e-gmd_checkpoint.zip",
                model_dir,
                unzip_dir,
                redownload=False,
            )
            self._checkpoint_dir = unzip_dir
            self._config = configs.CONFIG_MAP["drums"]
        else:
            raise ValueError(f"Unknown model \"{model}\"")
        
        self._hparams = self._config.hparams
        self._hparams.batch_size = 1
        self._hparams.truncated_length_secs = 0
        
    @staticmethod
    def _download_and_unzip(
        url: str,
        download_dir: Path,
        unzip_dir: Path,
        redownload: bool = True,
    ) -> None:
        if unzip_dir.exists() and not redownload:
            return
        
        download_dir.mkdir(parents=True, exist_ok=True)
        unzip_dir.mkdir(parents=True, exist_ok=True)

        print(f"Downloading {unzip_dir}")
        zip_path = download_dir / Path(url).name
        urllib.request.urlretrieve(url, zip_path)
        with ZipFile(zip_path, "r") as zObject:
            zObject.extractall(unzip_dir)
        zip_path.unlink()

    @staticmethod
    def _create_example(
        wav_path: str,
        sample_rate: int,
        load_audio_with_librosa: bool = False,
    ) -> str:
        wav_data = tf.gfile.Open(wav_path, "rb").read()
        example_list = list(audio_label_data_utils.process_record(
            wav_data=wav_data,
            sample_rate=sample_rate,
            ns=music_pb2.NoteSequence(),
            example_id=six.ensure_text(wav_path, "utf-8"),
            min_length=0,
            max_length=-1,
            allow_empty_notesequence=True,
            load_audio_with_librosa=load_audio_with_librosa,
        ))
        assert len(example_list) == 1
        return example_list[0].SerializeToString()
    
    def __call__(
        self,
        wav_path: str,
    ):
        with tf.Graph().as_default():
            examples = tf.placeholder(tf.string, [None])
            dataset = data.provide_batch(
                examples=examples,
                preprocess_examples=True,
                params=self._hparams,
                is_training=False,
                shuffle_examples=False,
                skip_n_initial_records=0,
            )
            estimator = train_util.create_estimator(self._config.model_fn, self._checkpoint_dir, self._hparams)
            iterator = tf.data.make_initializable_iterator(dataset)
            next_record = iterator.get_next()

            with tf.Session() as sess:
                sess.run([
                    tf.initializers.global_variables(),
                    tf.initializers.local_variables(),
                ])
                sess.run(
                    iterator.initializer,
                    {examples: [OnsetsFrames._create_example(wav_path, self._hparams.sample_rate, False)]},
                )

                def transcription_data(params):
                    del params
                    return tf.data.Dataset.from_tensors(sess.run(next_record))
                
                input_fn = infer_util.labels_to_features_wrapper(transcription_data)
                prediction_list = list(estimator.predict(
                    input_fn,
                    checkpoint_path=self._checkpoint_dir,
                    yield_single_examples=False,
                ))
                assert len(prediction_list) == 1

                sequence_prediction = music_pb2.NoteSequence.FromString(prediction_list[0]["sequence_predictions"][0])
                return sequence_prediction
