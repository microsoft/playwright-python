# Copyright (c) Microsoft Corporation.
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

"""Port of tests/library/browsercontext-webauthn.spec.ts."""

import base64
import json
import re
from typing import Any, Awaitable, Callable, Dict

import pytest

from playwright.async_api import BrowserContext, Error, Page, VirtualCredential
from tests.server import Server

ContextFactory = Callable[..., Awaitable[BrowserContext]]

# Registers a passkey through navigator.credentials.create() and returns its id.
CREATE_CREDENTIAL_SCRIPT = """async ({ rpId }) => {
    const challenge = crypto.getRandomValues(new Uint8Array(32));
    const created = await navigator.credentials.create({
      publicKey: {
        challenge,
        rp: { id: rpId, name: 'Test RP' },
        user: { id: new Uint8Array([1, 2, 3, 4]), name: 'u', displayName: 'User' },
        pubKeyCredParams: [{ type: 'public-key', alg: -7 }],
        authenticatorSelection: { residentKey: 'required', userVerification: 'preferred' },
      },
    });
    return created.id;
  }"""

# Signs in with a discoverable credential and returns its id.
GET_DISCOVERABLE_CREDENTIAL_SCRIPT = """async ({ rpId }) => {
    const challenge = crypto.getRandomValues(new Uint8Array(32));
    // No allowCredentials — relies on the re-seeded credential being discoverable.
    const cred = await navigator.credentials.get({
      publicKey: { challenge, rpId, userVerification: 'preferred' },
    });
    return cred.id;
  }"""


async def assert_and_get_sign_count(page: Page, rp_id: str) -> int:
    """Runs an assertion ceremony with a discoverable credential, returns the signature
    counter from the authenticator data."""
    return await page.evaluate(
        """async ({ rpId }) => {
      const challenge = crypto.getRandomValues(new Uint8Array(32));
      const cred = await navigator.credentials.get({
        publicKey: { challenge, rpId, userVerification: 'preferred' },
      });
      const resp = cred.response;
      return new DataView(resp.authenticatorData).getUint32(33);
    }""",
        {"rpId": rp_id},
    )


async def seed_credential(
    context: BrowserContext, credential: VirtualCredential
) -> None:
    """Port of `context.credentials.create(credential.rpId, credential)`."""
    await context.credentials.create(
        credential["rpId"],
        id=credential["id"],
        private_key=credential["privateKey"],
        public_key=credential["publicKey"],
        sign_count=credential["signCount"],
        user_handle=credential["userHandle"],
    )


def from_base64url(value: str) -> bytes:
    """Port of Buffer.from(value, 'base64url')."""
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


async def test_AU_017_should_not_intercept_navigator_credentials_without_install(
    context_factory: ContextFactory, server: Server
) -> None:
    context = await context_factory()
    # Seed a credential, but do not install the interceptor.
    await context.credentials.create(server.HOSTNAME)
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)

    intercepted = await page.evaluate("() => globalThis.__pwWebAuthnInstalled === true")
    assert intercepted is False


async def test_AU_018_should_seed_a_known_credential_and_authenticate(
    context_factory: ContextFactory, server: Server
) -> None:
    # This is the easiest way to create credentials. In practice, this
    # probably comes from environment.
    source = await context_factory()
    known = await source.credentials.create(server.HOSTNAME)

    # A fresh context imports the known credential and signs in with it.
    context = await context_factory()
    await seed_credential(context, known)
    await context.credentials.install()
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)

    result = await page.evaluate(
        """async ({ rpId, credentialId }) => {
      const b64UrlToBytes = (s) => {
        let str = s.replace(/-/g, '+').replace(/_/g, '/');
        while (str.length % 4)
          str += '=';
        const bin = atob(str);
        const u8 = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++)
          u8[i] = bin.charCodeAt(i);
        return u8;
      };
      const challenge = crypto.getRandomValues(new Uint8Array(32));
      const cred = await navigator.credentials.get({
        publicKey: {
          challenge,
          rpId,
          allowCredentials: [{ type: 'public-key', id: b64UrlToBytes(credentialId) }],
          userVerification: 'preferred',
        },
      });
      const resp = cred.response;
      return {
        id: cred.id,
        type: cred.type,
        hasClientData: resp.clientDataJSON.byteLength > 0,
        hasAuthData: resp.authenticatorData.byteLength > 0,
        hasSignature: resp.signature.byteLength > 0,
        authDataFlags: new Uint8Array(resp.authenticatorData)[32],
      };
    }""",
        {"rpId": server.HOSTNAME, "credentialId": known["id"]},
    )

    assert result["id"] == known["id"]
    assert result["type"] == "public-key"
    assert result["hasClientData"] is True
    assert result["hasAuthData"] is True
    assert result["hasSignature"] is True
    # UP (0x01) | UV (0x04) = 0x05
    assert result["authDataFlags"] & 0x05 == 0x05

    # After the credential is deleted, the page can no longer authenticate with it.
    await context.credentials.delete(known["id"])
    assert len(await context.credentials.get()) == 0

    error = await page.evaluate(
        """async ({ rpId, credentialId }) => {
      const b64UrlToBytes = (s) => {
        let str = s.replace(/-/g, '+').replace(/_/g, '/');
        while (str.length % 4)
          str += '=';
        const bin = atob(str);
        const u8 = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++)
          u8[i] = bin.charCodeAt(i);
        return u8;
      };
      const challenge = crypto.getRandomValues(new Uint8Array(32));
      try {
        await navigator.credentials.get({
          publicKey: {
            challenge,
            rpId,
            allowCredentials: [{ type: 'public-key', id: b64UrlToBytes(credentialId) }],
          },
        });
        return 'no-error';
      } catch (e) {
        return e.name;
      }
    }""",
        {"rpId": server.HOSTNAME, "credentialId": known["id"]},
    )
    assert error == "NotAllowedError"


async def test_AU_019_should_capture_a_page_created_credential_and_reuse_it_in_another_context(
    context_factory: ContextFactory, server: Server
) -> None:
    # Setup context: the app registers a passkey via navigator.credentials.create().
    setup_context = await context_factory()
    await setup_context.credentials.install()
    setup_page = await setup_context.new_page()
    await setup_page.goto(server.EMPTY_PAGE)

    created_id = await setup_page.evaluate(
        CREATE_CREDENTIAL_SCRIPT, {"rpId": server.HOSTNAME}
    )

    [captured] = await setup_context.credentials.get(rp_id=server.HOSTNAME)
    assert captured["id"] == created_id
    assert re.match(r"^[A-Za-z0-9_-]+$", captured["privateKey"])
    assert re.match(r"^[A-Za-z0-9_-]+$", captured["publicKey"])

    # Reuse the captured passkey in a fresh context and sign in with it.
    context = await context_factory()
    await seed_credential(context, captured)
    await context.credentials.install()
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)

    got_id = await page.evaluate(
        GET_DISCOVERABLE_CREDENTIAL_SCRIPT, {"rpId": server.HOSTNAME}
    )

    assert got_id == created_id


async def test_AU_020_should_reuse_a_page_created_credential_via_the_storage_state_option(
    context_factory: ContextFactory, server: Server
) -> None:
    # Setup context: the app registers a passkey via navigator.credentials.create().
    setup_context = await context_factory()
    await setup_context.credentials.install()
    setup_page = await setup_context.new_page()
    await setup_page.goto(server.EMPTY_PAGE)

    created_id = await setup_page.evaluate(
        CREATE_CREDENTIAL_SCRIPT, {"rpId": server.HOSTNAME}
    )

    # Capture the passkey as part of the storage state.
    storage_state = await setup_context.storage_state(credentials=True)

    # A context created from the storage state has the authenticator installed and signs in with
    # the captured passkey — without calling install() again.
    context = await context_factory(storage_state=storage_state)
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)

    got_id = await page.evaluate(
        GET_DISCOVERABLE_CREDENTIAL_SCRIPT, {"rpId": server.HOSTNAME}
    )

    assert got_id == created_id


async def test_AU_021_should_seed_and_report_sign_count(
    context_factory: ContextFactory, server: Server
) -> None:
    context = await context_factory()
    fresh = await context.credentials.create("fresh.example.com")
    assert fresh["signCount"] == 0

    seeded = await context.credentials.create(server.HOSTNAME, sign_count=41)
    assert seeded["signCount"] == 41
    await context.credentials.install()
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)

    # Each assertion increments the counter and reports the new value to the page.
    assert await assert_and_get_sign_count(page, server.HOSTNAME) == 42
    assert await assert_and_get_sign_count(page, server.HOSTNAME) == 43
    assert await context.credentials.get(id=seeded["id"]) == [
        {**seeded, "signCount": 43}
    ]
    assert await context.credentials.get(id=fresh["id"]) == [fresh]

    # A captured credential continues from the same counter in another context.
    [captured] = await context.credentials.get(id=seeded["id"])
    context2 = await context_factory()
    await seed_credential(context2, captured)
    await context2.credentials.install()
    page2 = await context2.new_page()
    await page2.goto(server.EMPTY_PAGE)
    assert await assert_and_get_sign_count(page2, server.HOSTNAME) == 44


async def test_AU_022_should_reject_invalid_sign_count(
    context_factory: ContextFactory,
) -> None:
    context = await context_factory()
    with pytest.raises(Error) as exc_info:
        await context.credentials.create("example.com", sign_count=-1)
    assert (
        "signCount must be between 0 and 4294967295, got -1" in exc_info.value.message
    )
    assert await context.credentials.get() == []


async def test_AU_023_should_preserve_sign_count_via_the_storage_state_option(
    context_factory: ContextFactory, server: Server
) -> None:
    setup_context = await context_factory()
    await setup_context.credentials.create(server.HOSTNAME)
    await setup_context.credentials.install()
    setup_page = await setup_context.new_page()
    await setup_page.goto(server.EMPTY_PAGE)
    assert await assert_and_get_sign_count(setup_page, server.HOSTNAME) == 1

    storage_state = await setup_context.storage_state(credentials=True)
    [captured] = await setup_context.credentials.get()
    assert captured["signCount"] == 1
    assert storage_state == {"cookies": [], "origins": [], "credentials": [captured]}

    context = await context_factory(storage_state=storage_state)
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    assert await assert_and_get_sign_count(page, server.HOSTNAME) == 2

    # Storage state saved by older versions has no signCount, the counter starts from zero.
    legacy_credential: Dict[str, Any] = {**captured}
    del legacy_credential["signCount"]
    legacy_storage_state: Any = {**storage_state, "credentials": [legacy_credential]}
    legacy_context = await context_factory(storage_state=legacy_storage_state)
    legacy_page = await legacy_context.new_page()
    await legacy_page.goto(server.EMPTY_PAGE)
    assert await assert_and_get_sign_count(legacy_page, server.HOSTNAME) == 1


async def test_AU_024_should_serialize_credentials_with_to_json(
    context_factory: ContextFactory, server: Server
) -> None:
    context = await context_factory()
    await context.credentials.install()
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)

    result = await page.evaluate(
        """async ({ rpId }) => {
      const toB64Url = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\\+/g, '-').replace(/\\//g, '_').replace(/=+$/, '');
      const created = await navigator.credentials.create({
        publicKey: {
          challenge: crypto.getRandomValues(new Uint8Array(32)),
          rp: { id: rpId, name: 'Test RP' },
          user: { id: new Uint8Array([1, 2, 3, 4]), name: 'u', displayName: 'User' },
          pubKeyCredParams: [{ type: 'public-key', alg: -7 }],
          authenticatorSelection: { residentKey: 'required' },
        },
      });
      const attestation = created.response;
      const got = await navigator.credentials.get({
        publicKey: { challenge: crypto.getRandomValues(new Uint8Array(32)), rpId },
      });
      const assertion = got.response;
      return {
        registration: JSON.parse(JSON.stringify(created)),
        authentication: JSON.parse(JSON.stringify(got)),
        expected: {
          id: created.id,
          attestation: {
            clientDataJSON: toB64Url(attestation.clientDataJSON),
            authenticatorData: toB64Url(attestation.getAuthenticatorData()),
            publicKey: toB64Url(attestation.getPublicKey()),
            attestationObject: toB64Url(attestation.attestationObject),
          },
          assertion: {
            clientDataJSON: toB64Url(assertion.clientDataJSON),
            authenticatorData: toB64Url(assertion.authenticatorData),
            signature: toB64Url(assertion.signature),
            userHandle: toB64Url(assertion.userHandle),
          },
        },
      };
    }""",
        {"rpId": server.HOSTNAME},
    )
    registration = result["registration"]
    authentication = result["authentication"]
    expected = result["expected"]

    assert registration == {
        "id": expected["id"],
        "rawId": expected["id"],
        "response": {
            **expected["attestation"],
            "transports": ["internal"],
            "publicKeyAlgorithm": -7,
        },
        "authenticatorAttachment": "platform",
        "clientExtensionResults": {},
        "type": "public-key",
    }
    assert authentication == {
        "id": expected["id"],
        "rawId": expected["id"],
        "response": expected["assertion"],
        "authenticatorAttachment": "platform",
        "clientExtensionResults": {},
        "type": "public-key",
    }

    [credential] = await context.credentials.get()
    assert registration["response"]["publicKey"] == credential["publicKey"]
    assert authentication["response"]["userHandle"] == credential["userHandle"]
    assert (
        json.loads(from_base64url(registration["response"]["clientDataJSON"]))["type"]
        == "webauthn.create"
    )
    assert (
        json.loads(from_base64url(authentication["response"]["clientDataJSON"]))["type"]
        == "webauthn.get"
    )

    # Registration authenticator data is embedded in the attestation object and carries attested credential data (AT flag).
    auth_data = from_base64url(registration["response"]["authenticatorData"])
    assert auth_data in from_base64url(registration["response"]["attestationObject"])
    assert auth_data[32] & 0x40 == 0x40
