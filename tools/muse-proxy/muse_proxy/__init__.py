"""
muse_proxy — the credential-holding egress proxy.

This is tool #2 of the four. It is the only component that ever touches a
credential or makes an outbound request on the agent's behalf. The agent asks the
proxy to do something; the proxy checks the allowlist, attaches the credential,
makes the request, and logs it. The agent never sees a key.

Public surface:
    from muse_proxy import proxy, creds, allowlist

    proxy.request("bluesky", method="POST", path="/xrpc/...", json_body={...})
    creds.put("bluesky", "app-password-value")
    creds.get("bluesky")             # only callable from trusted code
    allowlist.is_allowed("bsky.social")
"""

from . import allowlist, creds, proxy  # noqa: F401

__all__ = ["proxy", "creds", "allowlist"]
__version__ = "1.0.0"
