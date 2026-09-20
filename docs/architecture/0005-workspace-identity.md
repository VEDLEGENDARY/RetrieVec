# Workspace identity and sessions

Authlib 1.8.0 implements Authorization Code, S256 PKCE and OIDC verification.
State, nonce and PKCE verifier live in PostgreSQL, behind a random browser cookie.
Issuer is pinned by configuration; Authlib validates signature, audience, expiry
and nonce. Callback URL is fixed, never inferred from a Host header. The identity
key is issuer plus subject, never an email. Login rotates the session identifier;
logout deletes it. No application identity bypass exists.

Cookies are HttpOnly, SameSite=Lax, Secure by default, with an eight-hour absolute
session expiry. `RETRIEVEC_LOCAL_HTTP=1` permits HTTP only on explicit localhost
URLs. Mutations require the exact Origin and session CSRF token. No credentialed
CORS is enabled. Provider tokens are not retained after identity verification.
Logout ends the application session; it does not end the identity provider SSO
session. Sign-in requests account selection for the two-user workflow.

Run `python scripts/configure_identity.py`, then
`docker compose -f compose.identity.yaml up -d`. Passwords are random and written
only to ignored artifacts. Keycloak development mode is local-only, not a
deployment configuration. Existing users survive container restart.

To link an old CLI principal, an operator inserts an exact verified issuer and
subject into `identities` referencing that principal before first app login.
Do not automatically assign imported collections to newly signed-in users.

References: [Authlib OIDC implementation](https://github.com/authlib/authlib/blob/main/authlib/integrations/base_client/async_openid.py),
[Keycloak container setup](https://www.keycloak.org/server/containers).
