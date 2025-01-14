# Copyright 2019 ZTE corporation. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from tempfile import NamedTemporaryFile
from unittest import TestCase

import tensorflow as tf
import onnx
import pytest

import model_compiler.compilers.tf_model_to_tf_frozen_graph_model as tf_model_compiler
import model_compiler.compilers.tf_frozen_graph_model_to_onnx_model as frozen_graph_compiler
import model_compiler.compilers.onnx_model_file_to_enflame_model as compiler \
    # pylint: disable=no-name-in-module

from model_compiler.compilers.onnx_model_file_to_enflame_model import Config, DataFormat \
    # pylint: disable=no-name-in-module
from model_compiler.models.irs.tf_model import Input, TensorFlowModel
from model_compiler.models.sources.onnx_model_file import ONNXModelFile


def _make_onnx_model():
    with tf.Graph().as_default(), tf.compat.v1.Session().as_default() as session:
        input_x = tf.compat.v1.placeholder(dtype=tf.float32, shape=[3, 4], name='x')
        weight = tf.Variable(initial_value=4.2, dtype=tf.float32)
        output_z = tf.multiply(input_x, weight, name='z')

        session.run(weight.initializer)

    frozen_graph_model = tf_model_compiler.compile_source(
        source=TensorFlowModel(inputs=[Input(tensor=input_x)],
                               outputs=[output_z],
                               session=session)
    )
    return frozen_graph_compiler.compile_source(frozen_graph_model)


@pytest.mark.dtu_test
class ConfigTestCase(TestCase):
    def test_from_json(self):
        self.assertEqual(Config.from_json({'input_formats': ['channels_first']}),
                         Config(input_formats=[DataFormat.CHANNELS_FIRST]))

    def test_from_env(self):
        self.assertEqual(Config.from_env({'INPUT_FORMATS': 'channels_first'}),
                         Config(input_formats=[DataFormat.CHANNELS_FIRST]))


@pytest.mark.dtu_test
class CompileSourceTestCase(TestCase):
    def test_compile_with_variables(self):
        with NamedTemporaryFile(suffix='.onnx') as model_file:
            onnx.save_model(_make_onnx_model().model_proto, model_file.name)

            config = Config.from_json({'input_formats': ['channels_first']})
            compiled = compiler.compile_source(source=ONNXModelFile(model_file.name), config=config)

        self.assertEqual([model_input.name for model_input in compiled.model_inputs], ['x:0'])
        self.assertEqual(compiled.input_formats, [DataFormat.CHANNELS_FIRST])
