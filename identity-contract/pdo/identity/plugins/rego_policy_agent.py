# Copyright 2026 Intel Corporation
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

import json
import logging

from pdo.contract import invocation_request

import pdo.client.builder as pbuilder
import pdo.client.builder.command as pcommand
import pdo.client.builder.contract as pcontract
import pdo.client.builder.shell as pshell
import pdo.client.commands.contract as pcontract_cmd

__all__ = [
    'op_set_rego_policy',
    'op_get_rego_policy',
    'op_evaluate',
    'cmd_create_rego_policy_agent',
    'cmd_set_rego_policy',
    'cmd_get_rego_policy',
    'cmd_evaluate',
    'do_rego_policy_agent',
    'do_rego_policy_agent_contract',
    'load_commands',
]

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------
class op_set_rego_policy(pcontract.contract_op_base):

    name = "set_rego_policy"
    help = "store a Rego policy in the contract"

    @classmethod
    def add_arguments(cls, subparser):
        subparser.add_argument(
            '-p', '--policy',
            help='Rego policy text',
            type=str,
            required=True)

    @classmethod
    def invoke(cls, state, session_params, policy, **kwargs):
        session_params['commit'] = True
        message = invocation_request('set_rego_policy', policy=policy)
        result = pcontract_cmd.send_to_contract(state, message, **session_params)
        cls.log_invocation(message, result)
        return result


# -----------------------------------------------------------------
class op_get_rego_policy(pcontract.contract_op_base):

    name = "get_rego_policy"
    help = "fetch the stored Rego policy"

    @classmethod
    def add_arguments(cls, subparser):
        pass

    @classmethod
    def invoke(cls, state, session_params, **kwargs):
        session_params['commit'] = False
        message = invocation_request('get_rego_policy')
        result = pcontract_cmd.send_to_contract(state, message, **session_params)
        cls.log_invocation(message, result)
        return result


# -----------------------------------------------------------------
class op_evaluate(pcontract.contract_op_base):

    name = "evaluate"
    help = "evaluate the stored Rego policy against input"

    @classmethod
    def add_arguments(cls, subparser):
        subparser.add_argument(
            '-i', '--input',
            help='Input value (JSON)',
            type=pbuilder.invocation_parameter,
            required=True)
        subparser.add_argument(
            '-r', '--rule',
            help='Rego rule path (e.g. data.policy.allow)',
            type=str,
            required=True)

    @classmethod
    def invoke(cls, state, session_params, input, rule, **kwargs):
        session_params['commit'] = False
        # the contract expects `input` as a JSON document encoded in a string
        if not isinstance(input, str):
            input = json.dumps(input)
        message = invocation_request('evaluate', input=input, rule=rule)
        result = pcontract_cmd.send_to_contract(state, message, **session_params)
        cls.log_invocation(message, result)
        return result


# -----------------------------------------------------------------
class cmd_create_rego_policy_agent(pcommand.contract_command_base):
    name = "create"
    help = "create and initialize a Rego policy agent contract"

    @classmethod
    def add_arguments(cls, subparser):
        subparser.add_argument('-c', '--contract-class', type=str)
        subparser.add_argument('-e', '--eservice-group', type=str)
        subparser.add_argument('-f', '--save-file', type=str)
        subparser.add_argument('-p', '--pservice-group', type=str)
        subparser.add_argument('-r', '--sservice-group', type=str)
        subparser.add_argument('--source', type=str)
        subparser.add_argument('--extra', nargs=2, action='append')

    @classmethod
    def invoke(cls, state, context, **kwargs):
        save_file = pcontract_cmd.get_contract_from_context(state, context)
        if save_file:
            return save_file

        save_file = pcontract_cmd.create_contract_from_context(
            state, context, 'rego_policy_agent', **kwargs)
        context['save_file'] = save_file

        cls.display('created rego_policy_agent in {}'.format(save_file))
        return save_file


# -----------------------------------------------------------------
class cmd_set_rego_policy(pcommand.contract_command_base):
    name = "set_policy"
    help = "load a Rego policy file into the contract"

    @classmethod
    def add_arguments(cls, subparser):
        subparser.add_argument(
            '--file',
            help='Rego policy file',
            type=str,
            required=True)

    @classmethod
    def invoke(cls, state, context, file, **kwargs):
        save_file = pcontract_cmd.get_contract_from_context(state, context)
        if not save_file:
            raise ValueError('rego_policy_agent contract must be created and initialized')

        with open(file, 'r') as fp:
            policy_text = fp.read()

        session = pbuilder.SessionParameters(save_file=save_file)
        pcontract.invoke_contract_op(
            op_set_rego_policy, state, context, session, policy=policy_text, **kwargs)
        cls.display('policy loaded from {}'.format(file))
        return True


# -----------------------------------------------------------------
class cmd_get_rego_policy(pcommand.contract_command_base):
    name = "get_policy"
    help = "fetch the stored Rego policy"

    @classmethod
    def add_arguments(cls, subparser):
        pass

    @classmethod
    def invoke(cls, state, context, **kwargs):
        save_file = pcontract_cmd.get_contract_from_context(state, context)
        if not save_file:
            raise ValueError('rego_policy_agent contract must be created and initialized')

        session = pbuilder.SessionParameters(save_file=save_file)
        result = pcontract.invoke_contract_op(
            op_get_rego_policy, state, context, session, **kwargs)
        cls.display(result)
        return result


# -----------------------------------------------------------------
class cmd_evaluate(pcommand.contract_command_base):
    name = "evaluate"
    help = "evaluate the stored policy against an input"

    @classmethod
    def add_arguments(cls, subparser):
        subparser.add_argument(
            '--input',
            help='Input file containing JSON',
            type=str,
            required=True)
        subparser.add_argument(
            '--rule',
            help='Rego rule path',
            type=str,
            required=True)

    @classmethod
    def invoke(cls, state, context, input, rule, **kwargs):
        save_file = pcontract_cmd.get_contract_from_context(state, context)
        if not save_file:
            raise ValueError('rego_policy_agent contract must be created and initialized')

        with open(input, 'r') as fp:
            input_value = json.load(fp)

        session = pbuilder.SessionParameters(save_file=save_file)
        result = pcontract.invoke_contract_op(
            op_evaluate, state, context, session,
            input=input_value, rule=rule, **kwargs)
        cls.display(result)
        return result


# -----------------------------------------------------------------
__operations__ = [
    op_set_rego_policy,
    op_get_rego_policy,
    op_evaluate,
]

do_rego_policy_agent_contract = pcontract.create_shell_command(
    'rego_policy_agent_contract', __operations__)

__commands__ = [
    cmd_create_rego_policy_agent,
    cmd_set_rego_policy,
    cmd_get_rego_policy,
    cmd_evaluate,
]

do_rego_policy_agent = pcommand.create_shell_command('rego_policy_agent', __commands__)


def load_commands(cmdclass):
    pshell.bind_shell_command(cmdclass, 'rego_policy_agent', do_rego_policy_agent)
    pshell.bind_shell_command(cmdclass, 'rego_policy_agent_contract', do_rego_policy_agent_contract)
