"""Messaging channels: dispatch T-Ex team runs from chat apps.

Built-in adapters register themselves on import (see registry.register_adapter).
This module must stay import-light — adapters only touch the network when used.
"""

from texllm.channels.base import (  # noqa: F401
    ChannelAdapter,
    ChannelVerifyError,
    InboundMessage,
    WebhookRequest,
    WebhookResponse,
    parse_senders,
)

# Built-in adapters self-register on import (registry.register_adapter).
from texllm.channels import bluebubbles  # noqa: E402,F401
from texllm.channels import custom  # noqa: E402,F401
from texllm.channels import google_chat  # noqa: E402,F401
from texllm.channels import telegram  # noqa: E402,F401
from texllm.channels import whatsapp  # noqa: E402,F401
