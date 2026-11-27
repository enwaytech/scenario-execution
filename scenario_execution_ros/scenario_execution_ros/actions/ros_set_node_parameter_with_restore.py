# Copyright (C) 2026 Enway GmbH
#
# -----------MENTION OF PREDECESSOR LICENSE--------------
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

from typing import Any, Optional, Tuple, override

import py_trees
from rcl_interfaces.msg import Parameter, ParameterType, ParameterValue
from rcl_interfaces.srv import GetParameters, SetParameters
import rclpy
from rclpy.client import Client
from rclpy.executors import SingleThreadedExecutor
from rclpy.parameter import get_parameter_value
from rclpy.task import Future
from rosidl_runtime_py import message_to_ordereddict

from .ros_service_call import RosServiceCall
from .ros_set_node_parameter import RosSetNodeParameter

RESTORE_TIMEOUT_S = 2.0


class RosSetNodeParameterWithRestore(RosSetNodeParameter):
    """
    Set a node parameter and restore its original value on scenario shutdown (success, failure, timeout or Ctrl-C).

    Unlike set_node_parameter, the value is parsed as by `ros2 param set`, so numeric arrays are supported.
    """

    def __init__(self, node_name: str, parameter_name: str) -> None:
        super().__init__(node_name=node_name, parameter_name=parameter_name)
        # Allow scenario parameters as values, no response variable is stored
        self.resolve_variable_reference_arguments_in_execute = True
        self._get_client: Optional[Client] = None
        self._get_future: Optional[Future] = None
        self._original_value: Optional[ParameterValue] = None
        self._restore_requested = False

    @override
    def setup(self, **kwargs: Any) -> None:
        super().setup(**kwargs)
        get_service_name = self.service_name.removesuffix('/set_parameters') + '/get_parameters'
        self._get_client = self.node.create_client(GetParameters, get_service_name, callback_group=self.cb_group)

    @override
    def execute(self, parameter_value: str) -> None:  # pylint: disable=arguments-differ,arguments-renamed
        value = get_parameter_value(parameter_value)
        data = {'parameters': [{'name': self.parameter_name, 'value': message_to_ordereddict(value)}]}
        RosServiceCall.execute(self, data=data)

    @override
    def update(self) -> py_trees.common.Status:
        # Get the original value before setting the new one
        if self._original_value is None:
            if self._get_future is None and self._get_client is not None:
                self.feedback_message = f'Getting the original value of {self.parameter_name}'
                self._get_future = self._get_client.call_async(GetParameters.Request(names=[self.parameter_name]))
            if self._get_future is None or not self._get_future.done():
                return py_trees.common.Status.RUNNING
            response = self._get_future.result()
            values = response.values if response is not None else []
            if not values or values[0].type == ParameterType.PARAMETER_NOT_SET:
                self.feedback_message = f'Parameter {self.parameter_name} is not declared'
                return py_trees.common.Status.FAILURE
            self._original_value = values[0]

        return super().update()

    @override
    def check_response(self, msg: SetParameters.Response) -> Tuple[bool, str]:
        result = msg.results[0]
        return (result.successful, result.reason)

    @override
    def shutdown(self) -> None:
        if self._original_value is None or self._restore_requested:
            return
        self._restore_requested = True

        # The scenario node is destroyed right after the behaviors shut down, so restore with a temporary node and
        # wait for the reply here
        node = rclpy.create_node('scenario_execution_parameter_restore')
        try:
            client = node.create_client(SetParameters, self.service_name)
            if not client.wait_for_service(timeout_sec=RESTORE_TIMEOUT_S):
                self.logger.warning(f'Cannot restore {self.parameter_name}: {self.service_name} is not available')
                return
            request = SetParameters.Request(
                parameters=[Parameter(name=self.parameter_name, value=self._original_value)]
            )
            future = client.call_async(request)
            executor = SingleThreadedExecutor(context=node.context)
            executor.add_node(node)
            executor.spin_until_future_complete(future, timeout_sec=RESTORE_TIMEOUT_S)
            executor.shutdown()
            if not future.done():
                self.logger.warning(f'Restoring {self.parameter_name} timed out')
            elif not future.result().results[0].successful:
                self.logger.warning(f'Restoring {self.parameter_name} failed: {future.result().results[0].reason}')
            else:
                self.logger.info(f'Restored {self.parameter_name}')
        finally:
            node.destroy_node()
