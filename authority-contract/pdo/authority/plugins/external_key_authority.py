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

import pdo.identity.plugins.signature_authority as signature_authority
import pdo.identity.plugins.policy_agent as policy_agent

logger = logging.getLogger(__name__)

__all__ = [
    'op_initialize',
    'op_get_verifying_key',
    'op_get_extended_verifying_key',
    'op_register_signing_context',
    'op_describe_signing_context',
    'op_list_signing_contexts',
    'op_add_vc',
    'op_get_vc_list',
    'op_get_vp',
    'op_sign_credential',
    'op_verify_credential',
    'op_register_trusted_issuer',
    'op_list_trusted_issuers',
    'cmd_register_signing_context',
    'cmd_list_signing_contexts',
    'cmd_get_verifying_key',
    'cmd_verify_credential',
    'cmd_register_trusted_issuer',
    'cmd_list_trusted_issuers',
    'cmd_create_external_key_authority',
    'cmd_sign_credential',
    'do_external_key_authority',
    'do_external_key_authority_contract',
    'load_commands',
]

# -----------------------------------------------------------------
# external_key_authority inherits its identity operations from signature_authority
# and its trusted-issuer operations from policy_agent (used to trust a
# wallet_key_authority). sign_credential is customized (see op_sign_credential):
# it binds an external session key to a wallet from a trusted WalletVerifyingKeyCredential.
# -----------------------------------------------------------------
op_initialize = signature_authority.op_initialize
op_get_verifying_key = signature_authority.op_get_verifying_key
op_get_extended_verifying_key = signature_authority.op_get_extended_verifying_key
op_register_signing_context = signature_authority.op_register_signing_context
op_describe_signing_context = signature_authority.op_describe_signing_context
op_list_signing_contexts = signature_authority.op_list_signing_contexts
op_add_vc = signature_authority.op_add_vc
op_get_vc_list = signature_authority.op_get_vc_list
op_get_vp = signature_authority.op_get_vp
op_verify_credential = signature_authority.op_verify_credential

op_register_trusted_issuer = policy_agent.op_register_trusted_issuer
op_list_trusted_issuers = policy_agent.op_list_trusted_issuers

cmd_register_signing_context = signature_authority.cmd_register_signing_context
cmd_list_signing_contexts = signature_authority.cmd_list_signing_contexts
cmd_get_verifying_key = signature_authority.cmd_get_verifying_key
cmd_verify_credential = signature_authority.cmd_verify_credential
cmd_register_trusted_issuer = policy_agent.cmd_register_trusted_issuer
cmd_list_trusted_issuers = policy_agent.cmd_list_trusted_issuers


# -----------------------------------------------------------------
# -----------------------------------------------------------------
class op_sign_credential(pcontract.contract_op_base) :
    name = "sign_credential"
    help = "bind an external session key to a wallet and issue a publicKeyCredential for it"

    @classmethod
    def add_arguments(cls, subparser) :
        subparser.add_argument(
            '--wallet-verifying-key-credential',
            help='the WalletVerifyingKeyCredential from a trusted wallet_key_authority',
            type=pbuilder.invocation_parameter, required=True)
        subparser.add_argument(
            '--wallet-attestation',
            help='the binding payload signed by the wallet ({payload, signature})',
            type=pbuilder.invocation_parameter, required=True)
        subparser.add_argument(
            '--session-key-attestation',
            help='the same binding payload signed by the session key ({payload, signature})',
            type=pbuilder.invocation_parameter, required=True)

    @classmethod
    def invoke(cls, state, session_params, wallet_verifying_key_credential, wallet_attestation,
               session_key_attestation, **kwargs) :
        session_params['commit'] = False

        message = invocation_request(
            'sign_credential',
            wallet_verifying_key_credential=wallet_verifying_key_credential,
            wallet_attestation=wallet_attestation,
            session_key_attestation=session_key_attestation)
        result = pcontract_cmd.send_to_contract(state, message, **session_params)
        cls.log_invocation(message, result)

        return result


# -----------------------------------------------------------------
# -----------------------------------------------------------------
class cmd_create_external_key_authority(pcommand.contract_command_base) :
    name = "create"
    help = "create an external key authority"

    @classmethod
    def add_arguments(cls, subparser) :
        subparser.add_argument('-c', '--contract-class', help='Name of the contract class', type=str)
        subparser.add_argument('-e', '--eservice-group', help='Name of the enclave service group to use', type=str)
        subparser.add_argument('-f', '--save-file', help='File where contract data is stored', type=str)
        subparser.add_argument('-p', '--pservice-group', help='Name of the provisioning service group to use', type=str)
        subparser.add_argument('-r', '--sservice-group', help='Name of the storage service group to use', type=str)
        subparser.add_argument('--source', help='File that contains contract source code', type=str)
        subparser.add_argument('--extra', help='Extra data associated with the contract file', nargs=2, action='append')

        subparser.add_argument(
            '-d', '--description',
            help='Description of the external key authority',
            type=str, required=True)

    @classmethod
    def invoke(cls, state, context, description, **kwargs) :
        save_file = pcontract_cmd.get_contract_from_context(state, context)
        if save_file :
            return save_file

        save_file = pcontract_cmd.create_contract_from_context(state, context, 'external_key_authority', **kwargs)
        context['save_file'] = save_file

        session = pbuilder.SessionParameters(save_file=save_file)
        pcontract.invoke_contract_op(
            op_initialize,
            state, context, session,
            description,
            **kwargs)

        cls.display('created external key authority in {}'.format(save_file))
        return save_file


# -----------------------------------------------------------------
# -----------------------------------------------------------------
class cmd_sign_credential(pcommand.contract_command_base) :
    name = "sign_credential"
    help = "bind an external session key to a wallet and issue a publicKeyCredential for the session key"

    @classmethod
    def add_arguments(cls, subparser) :
        subparser.add_argument(
            '--wallet-verifying-key-credential',
            help='file with the WalletVerifyingKeyCredential from a trusted wallet_key_authority',
            type=str, required=True)
        subparser.add_argument(
            '--wallet-attestation',
            help='file with the binding payload signed by the wallet ({payload, signature})',
            type=str, required=True)
        subparser.add_argument(
            '--session-key-attestation',
            help='file with the same payload signed by the session key ({payload, signature})',
            type=str, required=True)
        subparser.add_argument(
            '--credential',
            help='file where the issued verifiable credential will be written',
            type=str, required=True)

    @classmethod
    def invoke(cls, state, context, wallet_verifying_key_credential, wallet_attestation,
               session_key_attestation, credential, **kwargs) :
        save_file = pcontract_cmd.get_contract_from_context(state, context)
        if not save_file :
            raise ValueError('external key authority contract must be created and initialized')

        with open(wallet_verifying_key_credential, "r") as fp :
            wskc = json.load(fp)
        with open(wallet_attestation, "r") as fp :
            wallet_attestation_data = json.load(fp)
        with open(session_key_attestation, "r") as fp :
            session_key_attestation_data = json.load(fp)

        session = pbuilder.SessionParameters(save_file=save_file)
        vc = pcontract.invoke_contract_op(
            op_sign_credential,
            state, context, session,
            wallet_verifying_key_credential=wskc,
            wallet_attestation=wallet_attestation_data,
            session_key_attestation=session_key_attestation_data,
            **kwargs)

        with open(credential, "w") as fp :
            fp.write(vc)

        cls.display('saved publicKeyCredential to {}'.format(credential))
        return True


# -----------------------------------------------------------------
# Create the generic, shell independent version of the aggregate command
# -----------------------------------------------------------------
__operations__ = [
    op_initialize,
    op_get_verifying_key,
    op_get_extended_verifying_key,
    op_register_signing_context,
    op_describe_signing_context,
    op_list_signing_contexts,
    op_add_vc,
    op_get_vc_list,
    op_get_vp,
    op_sign_credential,
    op_verify_credential,
    op_register_trusted_issuer,
    op_list_trusted_issuers,
]

do_external_key_authority_contract = pcontract.create_shell_command('external_key_authority_contract', __operations__)

__commands__ = [
    cmd_get_verifying_key,
    cmd_register_signing_context,
    cmd_list_signing_contexts,
    cmd_verify_credential,
    cmd_register_trusted_issuer,
    cmd_list_trusted_issuers,
    cmd_create_external_key_authority,
    cmd_sign_credential,
]

do_external_key_authority = pcommand.create_shell_command('external_key_authority', __commands__)


# -----------------------------------------------------------------
# Enable binding of the shell independent version to a pdo-shell command
# -----------------------------------------------------------------
def load_commands(cmdclass) :
    pshell.bind_shell_command(cmdclass, 'external_key_authority', do_external_key_authority)
    pshell.bind_shell_command(cmdclass, 'external_key_authority_contract', do_external_key_authority_contract)
