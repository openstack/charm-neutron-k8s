#!/usr/bin/env python3

# Copyright 2021 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock
import sys

sys.path.append('lib')  # noqa
sys.path.append('src')  # noqa

import charm
import advanced_sunbeam_openstack.test_utils as test_utils


class _NeutronOVNWallabyOperatorCharm(charm.NeutronOVNWallabyOperatorCharm):

    def __init__(self, framework):
        self.seen_events = []
        self.render_calls = []
        super().__init__(framework)

    def _log_event(self, event):
        self.seen_events.append(type(event).__name__)

    def renderer(self, containers, container_configs, template_dir,
                 openstack_release, adapters):
        self.render_calls.append(
            (
                containers,
                container_configs,
                template_dir,
                openstack_release,
                adapters))

    def configure_charm(self, event):
        super().configure_charm(event)
        self._log_event(event)


class TestNeutronOperatorCharm(test_utils.CharmTestCase):

    PATCHES = []

    @mock.patch(
        'charms.observability_libs.v0.kubernetes_service_patch.'
        'KubernetesServicePatch')
    def setUp(self, mock_patch):
        self.container_calls = test_utils.ContainerCalls()
        super().setUp(charm, self.PATCHES)
        self.harness = test_utils.get_harness(
            _NeutronOVNWallabyOperatorCharm,
            container_calls=self.container_calls)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()

    def test_pebble_ready_handler(self):
        self.assertEqual(self.harness.charm.seen_events, [])
        self.harness.container_pebble_ready('neutron-server')
        self.assertEqual(len(self.harness.charm.seen_events), 1)

    def test_all_relations(self):
        self.harness.set_leader()
        test_utils.set_all_pebbles_ready(self.harness)
        test_utils.add_all_relations(self.harness)

        setup_cmds = [
            [
                'sudo', '-u', 'neutron', 'neutron-db-manage', '--config-file',
                '/etc/neutron/neutron.conf', '--config-file',
                '/etc/neutron/plugins/ml2/ml2_conf.ini', 'upgrade', 'head']]
        for cmd in setup_cmds:
            self.assertIn(cmd, self.container_calls.execute['neutron-server'])
        self.assertEqual(
            sorted(list(set(
                self.container_calls.updated_files('neutron-server')))),
            [
                '/etc/neutron/neutron.conf',
                '/etc/neutron/plugins/ml2/cert_host',
                '/etc/neutron/plugins/ml2/key_host',
                '/etc/neutron/plugins/ml2/ml2_conf.ini',
                '/etc/neutron/plugins/ml2/neutron-ovn.crt'])
