# Copyright 2023 Intel Corporation
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

import logging

from pdo.contract import invocation_request


import pdo.client.builder as pbuilder
import pdo.client.builder.command as pcommand
import pdo.client.builder.contract as pcontract
import pdo.client.builder.shell as pshell
import pdo.client.commands.contract as pcontract_cmd

import pdo.exchange.plugins.token_object as token_object

__all__ = [
    "op_initialize",
    "op_get_verifying_key",
    "op_get_contract_metadata",
    "op_get_contract_code_metadata",
    "op_get_asset_type_identifier",
    "op_get_issuer_authority",
    "op_get_authority",
    "op_transfer",
    "op_escrow",
    "op_release",
    "op_claim",
    "cmd_mint_tokens",
    "cmd_transfer_assets",
    "do_download_token",
    "do_download_token_contract",
    "op_my_method",
    "cmd_my_method",
    "load_commands",
]

## -----------------------------------------------------------------
## inherited operations
## -----------------------------------------------------------------
op_get_verifying_key = token_object.op_get_verifying_key
op_get_contract_metadata = token_object.op_get_contract_metadata
op_get_contract_code_metadata = token_object.op_get_contract_code_metadata
op_get_asset_type_identifier = token_object.op_get_asset_type_identifier
op_get_issuer_authority = token_object.op_get_issuer_authority
op_get_authority = token_object.op_get_authority
op_transfer = token_object.op_transfer
op_escrow = token_object.op_escrow
op_release = token_object.op_release
op_claim = token_object.op_claim
op_initialize = token_object.op_initialize

cmd_mint_tokens = token_object.cmd_mint_tokens
cmd_transfer_assets = token_object.cmd_transfer_assets

logger = logging.getLogger(__name__)


class op_my_method(pcontract.contract_op_base):
    name = "op_my_method"
    help = "my method op"

    @classmethod
    def add_arguments(cls, subparser):
        pass

    @classmethod
    def invoke(cls, state, session_params, **kwargs):
        session_params["commit"] = False

        message = invocation_request("my_method")
        result = pcontract_cmd.send_to_contract(state, message, **session_params)
        return result


## -----------------------------------------------------------------
## -----------------------------------------------------------------
class cmd_my_method(pcommand.contract_command_base):
    name = "do_my_method"
    help = "my method"

    @classmethod
    def add_arguments(cls, subparser):
        pass

    @classmethod
    def invoke(cls, state, context, **kwargs):
        save_file = pcontract_cmd.get_contract_from_context(state, context)
        if not save_file:
            raise ValueError("token has not been created")

        session = pbuilder.SessionParameters(save_file=save_file)
        result = pcontract.invoke_contract_op(
            op_my_method, state, context, session, **kwargs
        )

        cls.display(result)

        return result


## -----------------------------------------------------------------
## Create the generic, shell independent version of the aggregate command
## -----------------------------------------------------------------
__operations__ = [
    op_initialize,
    op_get_verifying_key,
    op_get_contract_metadata,
    op_get_contract_code_metadata,
    op_get_asset_type_identifier,
    op_get_issuer_authority,
    op_get_authority,
    op_transfer,
    op_escrow,
    op_release,
    op_claim,
    op_my_method,
]

do_download_token_contract = pcontract.create_shell_command(
    "download_token_contract", __operations__
)

__commands__ = [cmd_mint_tokens, cmd_transfer_assets, cmd_my_method]

do_download_token = pcommand.create_shell_command("download_token", __commands__)


## -----------------------------------------------------------------
## Enable binding of the shell independent version to a pdo-shell command
## -----------------------------------------------------------------
def load_commands(cmdclass):
    pshell.bind_shell_command(cmdclass, "download_token", do_download_token)
    pshell.bind_shell_command(
        cmdclass, "download_token_contract", do_download_token_contract
    )
