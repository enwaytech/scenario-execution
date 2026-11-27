# Copyright (C) 2026 Enway GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions
# and limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

""" Test for set_node_parameter_with_restore """
import os
import threading
import unittest

from ament_index_python.packages import get_package_share_directory

import rclpy
from rcl_interfaces.msg import SetParametersResult

from scenario_execution_ros import ROSScenarioExecution
from scenario_execution.model.osc2_parser import OpenScenario2Parser
from scenario_execution.utils.logging import Logger

ORIGINAL_VALUE = [0.0, 0.0]


class TestRosSetNodeParameterWithRestore(unittest.TestCase):
    # pylint: disable=missing-function-docstring,missing-class-docstring

    def setUp(self):
        rclpy.init()
        self.parser = OpenScenario2Parser(Logger('test', False))
        self.scenario_execution_ros = ROSScenarioExecution()
        self.scenario_dir = get_package_share_directory('scenario_execution_ros')

        self.node = rclpy.create_node('test_node')
        self.node.declare_parameter('testArrayParam', ORIGINAL_VALUE)
        self.set_values = []
        self.node.add_on_set_parameters_callback(self.callback)

        self.executor = rclpy.executors.MultiThreadedExecutor()
        self.executor.add_node(self.node)
        self.executor_thread = threading.Thread(target=self.executor.spin, daemon=True)
        self.executor_thread.start()

    def tearDown(self):
        self.node.destroy_node()
        rclpy.try_shutdown()

    def callback(self, params):
        for param in params:
            if param.name == 'testArrayParam':
                if len(param.value) != 2:
                    return SetParametersResult(successful=False, reason='testArrayParam needs 2 values')
                self.set_values.append(list(param.value))
        return SetParametersResult(successful=True)

    def run_scenario(self, scenario_file):
        tree = self.parser.process_file(os.path.join(self.scenario_dir, 'scenarios', 'test', scenario_file), False)
        self.scenario_execution_ros.tree = tree
        self.scenario_execution_ros.run()
        return self.scenario_execution_ros.process_results()

    def test_success_and_restore(self):
        self.assertTrue(self.run_scenario('test_ros_set_node_parameter_with_restore.osc'))
        self.assertEqual(self.set_values, [[1.0, 2.0], ORIGINAL_VALUE])

    def test_rejected_value(self):
        self.assertFalse(self.run_scenario('test_ros_set_node_parameter_with_restore_rejected.osc'))
        # the rejected value is never applied, the restore sets the original value again
        self.assertEqual(self.set_values, [ORIGINAL_VALUE])
