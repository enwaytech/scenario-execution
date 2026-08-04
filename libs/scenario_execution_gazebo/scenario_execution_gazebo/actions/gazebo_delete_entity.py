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


import subprocess  # nosec B404
from enum import Enum
from typing import Optional

import py_trees
from scenario_execution.actions.run_process import RunProcess


class DeleteActionState(Enum):
    """States for executing a delete-entity in gazebo."""

    IDLE = 1
    WAITING_FOR_RESPONSE = 2
    DONE = 3
    FAILURE = 4


class GazeboDeleteEntity(RunProcess):
    """Class to delete an entity in gazebo."""

    def __init__(self) -> None:
        super().__init__()
        self.entity_name: Optional[str] = None
        self.current_state = DeleteActionState.IDLE
        self._entity_exists = True

    def execute(self, entity_name: str, world_name: str):  # pylint: disable=arguments-differ
        super().execute(wait_for_shutdown=True)
        self.entity_name = entity_name
        self.world_name = world_name
        self._entity_exists = self._check_entity_exists(entity_name)

        if self._entity_exists:
            self.set_command(["gz", "service", "-s", f"/world/{self.world_name}/remove",
                              "--reqtype", "gz.msgs.Entity",
                              "--reptype", "gz.msgs.Boolean",
                              "--timeout", "1000", "--req", f'name: "{self.entity_name}" type: MODEL'])

    def _check_entity_exists(self, entity_name: str) -> bool:
        """Return True if the entity is present in the Gazebo world."""
        try:
            result = subprocess.run(  # nosec B603
                ["gz", "model", "-m", entity_name],
                capture_output=True,
                timeout=10,
            )
            return "no model named" not in result.stdout.decode().lower()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return True  # assume exists so deletion is still attempted

    def update(self) -> py_trees.common.Status:
        if not self._entity_exists:
            self.feedback_message = (  # pylint: disable= attribute-defined-outside-init
                f"Entity '{self.entity_name}' does not exist, skipping deletion"
            )
            return py_trees.common.Status.SUCCESS
        return super().update()

    def on_executed(self) -> None:
        """Hook when process gets executed."""
        self.feedback_message = (
            f"Waiting for entity '{self.entity_name}' to be deleted"  # pylint: disable= attribute-defined-outside-init
        )
        self.current_state = DeleteActionState.WAITING_FOR_RESPONSE

    def on_process_finished(self, ret: int) -> py_trees.common.Status:
        """Check result of process."""
        if self.current_state == DeleteActionState.WAITING_FOR_RESPONSE:
            if ret == 0:
                while True:
                    try:
                        line = self.output.popleft()
                        line = line.lower()
                        if "error" in line or "timed out" in line:
                            self.logger.warning(line)
                            # pylint: disable-next= attribute-defined-outside-init
                            self.feedback_message = f"Found error output while executing '{self.get_command()}': {line}"
                            self.current_state = DeleteActionState.FAILURE
                            return py_trees.common.Status.FAILURE
                    except IndexError:
                        break
                self.feedback_message = f"Successfully deleted entity '{self.entity_name}'"
                self.current_state = DeleteActionState.DONE
                return py_trees.common.Status.SUCCESS
            else:
                self.feedback_message = f"Deleting '{self.entity_name}' failed with {ret}"
                self.current_state = DeleteActionState.FAILURE
                return py_trees.common.Status.FAILURE
        else:
            return py_trees.common.Status.INVALID
