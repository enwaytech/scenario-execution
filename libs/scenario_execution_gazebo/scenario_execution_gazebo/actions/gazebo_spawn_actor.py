# Copyright (C) 2024 Intel Corporation
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

from .gazebo_spawn_entity import GazeboSpawnEntity


class GazeboSpawnActor(GazeboSpawnEntity):
    """Class to spawn an actor into simulation."""

    def __init__(self, associated_actor: dict, xacro_arguments: list, model: str):
        super().__init__(xacro_arguments, model)
        self.associated_actor = associated_actor

    def setup(self, **kwargs):
        super().setup(**kwargs)

    # pylint: disable-next=arguments-differ
    def execute(self, associated_actor: dict, spawn_pose: list, world_name: str) -> None:
        self.associated_actor = associated_actor
        super().execute(entity_name=self.associated_actor["name"], spawn_pose=spawn_pose, world_name=world_name)
