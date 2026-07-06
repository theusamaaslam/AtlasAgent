"""Server-rendered /login page.

No React, no JavaScript dependency. Listed providers come from the
registry; clicking a provider sends a GET to
``/auth/login?provider=<name>``.

Visual styling mirrors the Atlas dashboard shell: a soft lavender page,
white command surface, dark navigation rail, rounded controls, and
Usama Aslam attribution. Fonts are served out of the SPA's ``/fonts/``
directory which the dashboard-auth gate already allowlists pre-auth
(see ``_GATE_PUBLIC_PREFIXES`` in ``middleware.py``), so the page renders
without needing the React bundle loaded.

Test-stable class names: the existing test suite extracts the
``class="provider-btn"`` anchor href to walk the OAuth flow. That
class name MUST NOT change without updating
``tests/atlas_cli/test_dashboard_auth_401_reauth.py``.
"""
from __future__ import annotations

import html

from atlas_cli.dashboard_auth import list_session_providers

# Inline minimal CSS. The dashboard's full skin lives in the React
# bundle, which we deliberately do NOT load here — the login page must
# not depend on the SPA build being present or on the injected session
# token.
#
# Single curly braces are placeholders for ``str.format``; CSS curlies
# are doubled (``{{`` / ``}}``).
_LOGIN_HTML_TEMPLATE = """\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/svg+xml" href="/favicon.svg?v=atlas-usama-aslam-20260706">
<link rel="alternate icon" type="image/x-icon" href="/favicon.ico?v=atlas-usama-aslam-20260706">
<title>Sign in - Atlas Agent</title>
<style>
  /* Brand fonts shipped with the dashboard assets. */
  @font-face {{
    font-family: 'Collapse';
    font-style: normal;
    font-weight: 400;
    font-display: swap;
    src: url('/fonts/Collapse-Regular.woff2') format('woff2');
  }}
  @font-face {{
    font-family: 'Collapse';
    font-style: normal;
    font-weight: 700;
    font-display: swap;
    src: url('/fonts/Collapse-Bold.woff2') format('woff2');
  }}
  @font-face {{
    font-family: 'Rules Compressed';
    font-style: normal;
    font-weight: 400;
    font-display: swap;
    src: url('/fonts/RulesCompressed-Regular.woff2') format('woff2');
  }}
  @font-face {{
    font-family: 'Rules Compressed';
    font-style: normal;
    font-weight: 600;
    font-display: swap;
    src: url('/fonts/RulesCompressed-Medium.woff2') format('woff2');
  }}

  :root {{
    --page: #bfc4ed;
    --surface: #f8f8fc;
    --surface-strong: #ffffff;
    --rail: #1f1b2d;
    --rail-soft: #171421;
    --accent: #8f95dc;
    --accent-soft: #e5e7fb;
    --ink: #1f1b2d;
    --muted: #74718a;
    --line: #dfe2f1;
  }}

  *, *::before, *::after {{ box-sizing: border-box; }}

  html, body {{
    margin: 0;
    padding: 0;
    min-height: 100%;
    background: var(--page);
    color: var(--ink);
    font-family: 'Collapse', system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    font-size: 16px;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }}

  body {{
    display: grid;
    place-items: center;
    padding: clamp(1.25rem, 5vw, 3rem);
  }}

  main {{
    width: 100%;
    max-width: 62rem;
    position: relative;
    animation: slide-up 0.6s ease-out both;
  }}

  @keyframes slide-up {{
    from {{ opacity: 0; transform: translateY(6px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
  }}

  @media (prefers-reduced-motion: reduce) {{
    main {{ animation: none; }}
  }}

  .card {{
    display: grid;
    grid-template-columns: minmax(13rem, 15rem) minmax(0, 1fr);
    gap: clamp(1.5rem, 4vw, 3.5rem);
    min-height: 34rem;
    padding: clamp(1rem, 2vw, 1.5rem);
    background: var(--surface);
    border: 1px solid rgba(255, 255, 255, 0.86);
    border-radius: 2rem;
    box-shadow: 0 28px 90px rgba(41, 35, 70, 0.22);
  }}

  .brand-panel {{
    display: flex;
    min-height: 100%;
    flex-direction: column;
    justify-content: space-between;
    gap: 2rem;
    padding: 1.5rem;
    color: #f8f6ff;
    background: linear-gradient(180deg, var(--rail), var(--rail-soft));
    border-radius: 1.55rem;
    box-shadow: 0 22px 48px rgba(31, 27, 45, 0.24);
  }}

  .mark {{
    position: relative;
    width: 5.25rem;
    height: 5.25rem;
    border-radius: 1.35rem;
    background: rgba(255, 255, 255, 0.05);
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.1);
  }}
  .mark span {{
    position: absolute;
    left: 50%;
    top: 50%;
    width: 1.45rem;
    height: 3.1rem;
    border-radius: 999px;
    transform: translate(-50%, -50%);
  }}
  .mark .a {{ background: #8f95dc; transform: translate(-50%, -74%); }}
  .mark .b {{ background: #ffffff; transform: translate(-50%, -24%); }}
  .mark .c {{ background: #bfc4ed; transform: translate(-92%, -50%) rotate(-26deg); }}
  .mark .d {{ background: #f6f7ff; transform: translate(-8%, -50%) rotate(26deg); }}

  .brand-title {{
    margin-top: 1.2rem;
    font-family: 'Rules Compressed', 'Collapse', sans-serif;
    font-size: 1.4rem;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
  }}
  .brand-subtitle {{
    margin-top: 0.45rem;
    color: rgba(248, 246, 255, 0.62);
    font-size: 0.78rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }}
  .brand-foot {{
    color: rgba(248, 246, 255, 0.54);
    font-size: 0.72rem;
    letter-spacing: 0.1em;
    line-height: 1.6;
    text-transform: uppercase;
  }}

  .content {{
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: clamp(1rem, 4vw, 3.5rem) clamp(0.25rem, 3vw, 2rem);
  }}

  h1 {{
    margin: 0 0 0.4rem;
    font-family: 'Collapse', system-ui, sans-serif;
    font-weight: 600;
    font-size: clamp(2.4rem, 6vw, 4.8rem);
    line-height: 0.96;
    letter-spacing: 0;
    color: var(--ink);
  }}

  .subtitle {{
    max-width: 34rem;
    margin: 0 0 2rem;
    color: var(--muted);
    font-size: 1rem;
  }}

  .provider-list {{
    display: grid;
    max-width: 27rem;
    gap: 0.85rem;
  }}

  .provider-btn {{
    display: block;
    width: 100%;
    box-sizing: border-box;
    padding: 1rem 1.25rem;
    text-align: center;
    background: var(--rail);
    color: #ffffff;
    font-family: 'Collapse', sans-serif;
    font-weight: 700;
    font-size: 0.82rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    text-decoration: none;
    border: 1px solid var(--rail);
    border-radius: 999px;
    cursor: pointer;
    box-shadow: 0 12px 28px rgba(31, 27, 45, 0.18);
    transition: background 0.12s ease-out, transform 0.12s ease-out;
  }}
  .provider-btn:hover {{
    background: var(--accent);
    border-color: var(--accent);
    transform: translateY(-1px);
  }}
  .provider-btn:active {{
    transform: translateY(0);
  }}
  .provider-btn:focus-visible {{
    outline: 3px solid color-mix(in srgb, var(--accent) 38%, transparent);
    outline-offset: 3px;
  }}

  .provider-form {{
    display: grid;
    gap: 0.75rem;
    text-align: left;
  }}
  .form-title {{
    font-family: 'Rules Compressed', 'Collapse', sans-serif;
    font-weight: 600;
    font-size: 0.72rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--muted);
  }}
  .field {{
    display: grid;
    gap: 0.3rem;
  }}
  .field-label {{
    font-size: 0.72rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--muted);
  }}
  .field-input {{
    width: 100%;
    box-sizing: border-box;
    padding: 0.85rem 1rem;
    background: var(--surface-strong);
    color: var(--ink);
    border: 1px solid var(--line);
    border-radius: 0.9rem;
    font-family: 'Collapse', sans-serif;
    font-size: 0.95rem;
  }}
  .field-input:focus-visible {{
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 22%, transparent);
  }}
  .form-error {{
    color: #ff6b6b;
    font-size: 0.82rem;
    letter-spacing: 0.02em;
  }}
  .provider-form .provider-btn {{
    margin-top: 0.25rem;
  }}

  footer {{
    margin-top: 1.25rem;
    text-align: center;
    color: color-mix(in srgb, var(--ink) 46%, transparent);
    font-size: 0.75rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    line-height: 1.7;
  }}
  footer .sep {{
    display: inline-block;
    width: 1.5rem;
    height: 1px;
    background: color-mix(in srgb, var(--ink) 20%, transparent);
    vertical-align: middle;
    margin: 0 0.6em 0.2em;
  }}

  ::selection {{
    background: var(--accent);
    color: #ffffff;
  }}

  @media (max-width: 720px) {{
    main {{ max-width: 30rem; }}
    .card {{
      grid-template-columns: 1fr;
      min-height: 0;
      border-radius: 1.5rem;
    }}
    .brand-panel {{
      min-height: 14rem;
      border-radius: 1.1rem;
    }}
    h1 {{ font-size: 2.6rem; }}
  }}
</style>
</head>
<body>
<main>
  <div class="card">
    <aside class="brand-panel" aria-label="Atlas">
      <div>
        <div class="mark" aria-hidden="true">
          <span class="a"></span>
          <span class="b"></span>
          <span class="c"></span>
          <span class="d"></span>
        </div>
        <div class="brand-title">Atlas</div>
        <div class="brand-subtitle">Created by Usama Aslam</div>
      </div>
      <div class="brand-foot">Private dashboard<br>Local agent console</div>
    </aside>
    <section class="content">
      <h1>Sign in</h1>
      <p class="subtitle">Choose a sign-in method to continue to the Atlas dashboard.</p>
      <div class="provider-list">
{provider_buttons}
      </div>
    </section>
  </div>
  <footer>
    <span class="sep"></span>Protected dashboard &middot; Created by Usama Aslam<span class="sep"></span>
  </footer>
</main>
{password_script}
</body>
</html>
"""

_EMPTY_HTML = """\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/svg+xml" href="/favicon.svg?v=atlas-usama-aslam-20260706">
<link rel="alternate icon" type="image/x-icon" href="/favicon.ico?v=atlas-usama-aslam-20260706">
<title>Sign-in unavailable - Atlas Agent</title>
<style>
  @font-face {
    font-family: 'Collapse';
    font-style: normal;
    font-weight: 400;
    font-display: swap;
    src: url('/fonts/Collapse-Regular.woff2') format('woff2');
  }
  @font-face {
    font-family: 'Rules Compressed';
    font-style: normal;
    font-weight: 600;
    font-display: swap;
    src: url('/fonts/RulesCompressed-Medium.woff2') format('woff2');
  }
  :root {
    --page: #bfc4ed;
    --surface: #f8f8fc;
    --rail: #1f1b2d;
    --accent: #8f95dc;
    --ink: #1f1b2d;
    --muted: #74718a;
    --line: #dfe2f1;
  }
  *, *::before, *::after { box-sizing: border-box; }
  html, body {
    margin: 0; padding: 0; min-height: 100%;
    background: var(--page);
    color: var(--ink);
    font-family: 'Collapse', system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    font-size: 16px; line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }
  body {
    display: grid; place-items: center;
    padding: clamp(1.5rem, 6vh, 6rem) 1.25rem;
  }
  main {
    width: 100%; max-width: 34rem;
    padding: 2.5rem 2.25rem;
    background: var(--surface);
    border: 1px solid rgba(255, 255, 255, 0.86);
    border-radius: 1.75rem;
    box-shadow: 0 28px 90px rgba(41, 35, 70, 0.22);
  }
  h1 {
    margin: 0 0 1rem;
    font-family: 'Rules Compressed', 'Collapse', sans-serif;
    font-weight: 600; font-size: 1.5rem;
    letter-spacing: 0.05em; text-transform: uppercase;
    color: var(--rail);
  }
  p { margin: 0 0 1rem; color: var(--muted); }
  code {
    background: var(--rail);
    color: #ffffff;
    padding: 0.12em 0.4em;
    border-radius: 0.35rem;
    font-family: 'Courier New', monospace;
    font-size: 0.9em;
  }
</style>
</head>
<body>
<main>
<p style="margin:0 0 0.75rem;color:var(--accent);font-size:0.78rem;letter-spacing:0.12em;text-transform:uppercase;">Created by Usama Aslam</p>
<h1>Sign-in unavailable</h1>
<p>This dashboard is bound to a non-loopback host but no authentication
providers are installed.</p>
<p>Configure a dashboard authentication provider, or restart with
<code>--insecure</code> to bypass the auth gate (not recommended on
untrusted networks).</p>
</main>
</body>
</html>
"""


# Inline script that wires every password provider form to POST JSON to
# ``/auth/password-login`` and navigate on success. Emitted ONLY when at
# least one ``supports_password`` provider is listed (OAuth-only login
# pages stay script-free, preserving the no-JS contract for that case).
#
# Plain string (NOT run through ``str.format``), so braces are literal —
# do not double them. A single delegated submit handler covers all forms;
# the provider name is read from the form's ``data-provider`` attribute.
_PASSWORD_FORM_SCRIPT = """\
<script>
(function () {
  function handle(form) {
    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var err = form.querySelector('.form-error');
      var btn = form.querySelector('button[type=submit]');
      if (err) { err.hidden = true; err.textContent = ''; }
      if (btn) { btn.disabled = true; }
      var body = {
        provider: form.getAttribute('data-provider') || '',
        username: (form.querySelector('input[name=username]') || {}).value || '',
        password: (form.querySelector('input[name=password]') || {}).value || '',
        next: (form.querySelector('input[name=next]') || {}).value || ''
      };
      fetch('/auth/password-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        credentials: 'same-origin'
      }).then(function (resp) {
        if (resp.ok) {
          return resp.json().then(function (data) {
            window.location.assign((data && data.next) || '/');
          });
        }
        var msg = resp.status === 429
          ? 'Too many attempts. Please wait and try again.'
          : (resp.status === 401 ? 'Invalid username or password.'
                                 : 'Sign-in failed. Please try again.');
        if (err) { err.textContent = msg; err.hidden = false; }
        if (btn) { btn.disabled = false; }
      }).catch(function () {
        if (err) { err.textContent = 'Network error. Please try again.'; err.hidden = false; }
        if (btn) { btn.disabled = false; }
      });
    });
  }
  var forms = document.querySelectorAll('form.provider-form');
  for (var i = 0; i < forms.length; i++) { handle(forms[i]); }
})();
</script>
"""


def render_login_html(*, next_path: str = "") -> str:
    """Return the full HTML for ``GET /login``.

    ``next_path`` — when set, the post-login landing path the user
    originally requested. Threaded into each provider button's ``href``
    as a ``next=`` query parameter so the OAuth round trip carries it
    end-to-end. The caller (``routes.login_page``) is responsible for
    validating ``next_path`` against the same-origin rules before we
    emit it; we still HTML-escape it as defence in depth.
    """
    providers = list_session_providers()
    if not providers:
        return _EMPTY_HTML

    if next_path:
        # URL-encode then HTML-escape. The URL-encode step matches the
        # gate's ``_safe_next_target`` output shape (also URL-encoded),
        # so a value that round-tripped from /login?next=... back into
        # the button href is byte-identical.
        from urllib.parse import quote
        next_qs = f"&next={html.escape(quote(next_path, safe=''), quote=True)}"
    else:
        next_qs = ""

    buttons = []
    needs_password_script = False
    for p in providers:
        if getattr(p, "supports_password", False):
            needs_password_script = True
            buttons.append(_render_password_form(p, next_path))
        else:
            buttons.append(
                f'      <a class="provider-btn" '
                f'href="/auth/login?provider={html.escape(p.name, quote=True)}{next_qs}">'
                f'Sign in with {html.escape(p.display_name)}</a>'
            )
    script = _PASSWORD_FORM_SCRIPT if needs_password_script else ""
    return _LOGIN_HTML_TEMPLATE.format(
        provider_buttons="\n".join(buttons),
        password_script=script,
    )


def _render_password_form(provider, next_path: str) -> str:
    """Render a username/password form for a ``supports_password`` provider.

    The form is wired by :data:`_PASSWORD_FORM_SCRIPT` (a single delegated
    submit handler) to POST JSON to ``/auth/password-login`` and navigate
    on success. ``next_path`` is carried in a hidden field; it has already
    been validated same-origin by the caller and is HTML-escaped here as
    defence in depth. The provider ``name`` is emitted in a ``data-``
    attribute (not a hidden input) so the script reads it without trusting
    form-field ordering.
    """
    pname = html.escape(provider.name, quote=True)
    plabel = html.escape(provider.display_name)
    safe_next = html.escape(next_path, quote=True) if next_path else ""
    return (
        f'      <form class="provider-form" data-provider="{pname}" '
        f'autocomplete="on">\n'
        f'        <div class="form-title">Sign in with {plabel}</div>\n'
        f'        <input type="hidden" name="next" value="{safe_next}">\n'
        f'        <label class="field">\n'
        f'          <span class="field-label">Username</span>\n'
        f'          <input class="field-input" type="text" name="username" '
        f'autocomplete="username" autocapitalize="none" '
        f'autocorrect="off" spellcheck="false" required>\n'
        f'        </label>\n'
        f'        <label class="field">\n'
        f'          <span class="field-label">Password</span>\n'
        f'          <input class="field-input" type="password" name="password" '
        f'autocomplete="current-password" required>\n'
        f'        </label>\n'
        f'        <div class="form-error" role="alert" hidden></div>\n'
        f'        <button class="provider-btn" type="submit">Sign in</button>\n'
        f'      </form>'
    )
