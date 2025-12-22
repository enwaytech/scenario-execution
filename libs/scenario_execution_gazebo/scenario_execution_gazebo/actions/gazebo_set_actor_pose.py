# Copyright (c) 2026 Enway GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

from .gazebo_set_entity_pose import GazeboSetEntityPose


class GazeboSetActorPose(GazeboSetEntityPose):
    """Class to set the pose of an actor in gazebo."""

    def __init__(self, associated_actor: dict) -> None:
        super().__init__()

    def execute(self, associated_actor: dict, pose: dict, world_name: str) -> None:  # pylint: disable=arguments-differ
        super().execute(entity_name=associated_actor["name"], pose=pose, world_name=world_name)
