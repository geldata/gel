#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2016-present MagicStack Inc. and the EdgeDB authors.
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
#

from __future__ import annotations
from typing import cast, Optional

import html
import email.message

from edb.server.protocol.auth_ext import config as auth_config

from . import components as render


def render_signin_page(
    *,
    base_path: str,
    providers: frozenset[auth_config.ProviderConfig],
    error_message: Optional[str] = None,
    email: Optional[str] = None,
    challenge: str,
    selected_tab: Optional[str] = None,
    # config
    redirect_to: str,
    redirect_to_on_signup: Optional[str] = None,
    app_name: Optional[str] = None,
    logo_url: Optional[str] = None,
    dark_logo_url: Optional[str] = None,
    brand_color: Optional[str] = None,
) -> bytes:
    password_provider = None
    webauthn_provider = None
    magic_link_provider = None
    oauth_providers = []
    for p in providers:
        if p.name == 'builtin::local_emailpassword':
            password_provider = cast(auth_config.EmailPasswordProviderConfig, p)
        elif p.name == 'builtin::local_webauthn':
            webauthn_provider = cast(auth_config.WebAuthnProviderConfig, p)
        elif p.name == 'builtin::local_magic_link':
            magic_link_provider = cast(auth_config.MagicLinkProviderConfig, p)
        elif p.name.startswith('builtin::oauth_') or hasattr(p, "issuer_url"):
            oauth_providers.append(cast(auth_config.OAuthProviderConfig, p))

    base_email_factor_form = render.render_base_email_form(
        challenge=challenge, email=email
    )

    password_input = (
        render.render_password_input(challenge) if password_provider else ''
    )

    email_factor_form = render_email_factor_form(
        base_email_factor_form=base_email_factor_form,
        password_input=password_input,
        selected_tab=selected_tab,
        single_form_fields=f'''
            {
            render.hidden_input(
                name='redirect_to',
                value=(
                    redirect_to
                    if webauthn_provider
                    else (base_path + '/ui/magic-link-sent')
                ),
                secondary_value=redirect_to,
            )
        }
            {
            render.hidden_input(
                name='redirect_on_failure',
                value=f'{base_path}/ui/signin',
                secondary_value=f'{base_path}/ui/signin?selected_tab=password',
            )
        }
            {
            render.hidden_input(
                name='provider',
                value=magic_link_provider.name if magic_link_provider else '',
                secondary_value=(
                    password_provider.name if password_provider else ''
                ),
            )
        }
            {
            render.hidden_input(name='callback_url', value=redirect_to)
            if magic_link_provider
            else ''
        }
        ''',
        password_form=(
            render.render_password_form(
                base_email_form=base_email_factor_form,
                password_input=password_input,
                redirect_to=redirect_to,
                base_path=base_path,
                provider_name=password_provider.name,
            )
            if password_provider
            else None
        ),
        webauthn_form=(
            render.render_webauthn_form(
                base_email_form=base_email_factor_form,
                redirect_to=redirect_to,
                base_path=base_path,
                provider_name=webauthn_provider.name,
            )
            if webauthn_provider
            else None
        ),
        magic_link_form=(
            render.render_magic_link_form(
                base_email_form=base_email_factor_form,
                redirect_to=redirect_to,
                base_path=base_path,
                provider_name=magic_link_provider.name,
                verification_method=magic_link_provider.verification_method,
            )
            if magic_link_provider
            else None
        ),
        magic_link_verification_method=(
            magic_link_provider.verification_method
            if magic_link_provider
            else 'Link'
        ),
    )

    if email_factor_form:
        email_factor_form += render.bottom_note(
            "Don't have an account?", link='Sign up', href='signup'
        )

    oauth_buttons = render.oauth_buttons(
        oauth_providers=oauth_providers,
        label_prefix=('Sign in with' if email_factor_form else 'Continue with'),
        challenge=challenge,
        redirect_to=redirect_to,
        redirect_to_on_signup=redirect_to_on_signup,
        collapsed=email_factor_form is not None and len(oauth_providers) >= 3,
    )

    return render.base_page(
        title=f'Sign in{f" to {app_name}" if app_name else ""}',
        logo_url=logo_url,
        dark_logo_url=dark_logo_url,
        brand_color=brand_color,
        cleanup_search_params=['error', 'email', 'selected_tab'],
        content=f'''
          {render.title('Sign in', app_name=app_name)}
          {render.error_message(error_message)}
          {oauth_buttons}
          {
            render.divider
            if email_factor_form and len(oauth_providers) > 0
            else ''
        }
          {email_factor_form or ''}
          {render.script('webauthn-authenticate') if webauthn_provider else ''}
        ''',
    )


def render_email_factor_form(
    *,
    base_email_factor_form: Optional[str] = None,
    password_input: str = '',
    selected_tab: Optional[str] = None,
    single_form_fields: str = '',
    password_form: Optional[str],
    webauthn_form: Optional[str],
    magic_link_form: Optional[str],
    magic_link_verification_method: str = "Link",
) -> Optional[str]:
    if (
        password_form is None
        and webauthn_form is None
        and magic_link_form is None
    ):
        return None

    match (password_form, webauthn_form, magic_link_form):
        case (_, None, None):
            return password_form
        case (None, _, None):
            return webauthn_form
        case (None, None, _):
            return magic_link_form

    magic_link_tab_label = render.get_magic_link_tab_label(
        magic_link_verification_method
    )
    magic_link_button_text = render.get_magic_link_button_text(
        magic_link_verification_method
    )

    if base_email_factor_form is None or (
        webauthn_form is not None and magic_link_form is not None
    ):
        tabs = [
            (
                ('Passkey', webauthn_form, selected_tab == 'webauthn')
                if webauthn_form
                else None
            ),
            (
                ('Password', password_form, selected_tab == 'password')
                if password_form
                else None
            ),
            (
                (
                    magic_link_tab_label,
                    magic_link_form,
                    selected_tab == 'magic_link',
                )
                if magic_link_form
                else None
            ),
        ]

        selected_tabs = [t[2] for t in tabs if t is not None]
        selected_index = (
            selected_tabs.index(True) if True in selected_tabs else 0
        )

        return render.tabs_buttons(
            [t[0] for t in tabs if t is not None], selected_index
        ) + render.tabs_content(
            [t[1] for t in tabs if t is not None], selected_index
        )

    slider_content = [
        f'''
            {
            render.button("Sign In", id="webauthn-signin")
            if webauthn_form
            else render.button(magic_link_button_text, id="magic-link-signin")
        }
            {
            render.button(
                "Sign in with password",
                id="show-password-form",
                secondary=True,
                type="button",
            )
        }
        ''',
        f'''
            {password_input}
            <div class="button-group">
                {
            render.button(
                None, id="hide-password-form", secondary=True, type="button"
            )
        }
                {render.button("Sign in with password", id="password-signin")}
            </div>
        ''',
    ]

    return f"""
    <form id="email-factor" method="post" {
        'action="../magic-link/email"' if magic_link_form else ''
    } data-secondary-action="../authenticate" novalidate>
        {single_form_fields}
        {base_email_factor_form}
        {
        render.tabs_content(
            slider_content,
            selected_tab=(1 if selected_tab == 'password' else 0),
        )
    }
    </form>
    """


def render_signup_page(
    *,
    base_path: str,
    providers: frozenset[auth_config.ProviderConfig],
    error_message: Optional[str] = None,
    email: Optional[str] = None,
    challenge: str,
    selected_tab: Optional[str] = None,
    # config
    redirect_to: str,
    redirect_to_on_signup: Optional[str] = None,
    app_name: Optional[str] = None,
    logo_url: Optional[str] = None,
    dark_logo_url: Optional[str] = None,
    brand_color: Optional[str] = None,
) -> bytes:
    password_provider = None
    webauthn_provider = None
    magic_link_provider = None
    oauth_providers = []
    for p in providers:
        if p.name == 'builtin::local_emailpassword':
            password_provider = cast(auth_config.EmailPasswordProviderConfig, p)
        elif p.name == 'builtin::local_webauthn':
            webauthn_provider = cast(auth_config.WebAuthnProviderConfig, p)
        elif p.name == 'builtin::local_magic_link':
            magic_link_provider = cast(auth_config.MagicLinkProviderConfig, p)
        elif p.name.startswith('builtin::oauth_') or hasattr(p, "issuer_url"):
            oauth_providers.append(cast(auth_config.OAuthProviderConfig, p))

    base_email_factor_form = render.render_base_email_form(
        challenge=challenge, email=email
    )

    email_factor_form = render_email_factor_form(
        selected_tab=selected_tab,
        password_form=(
            render.render_password_signup_form(
                base_email_form=base_email_factor_form,
                redirect_to=render.get_email_password_signup_redirect_url(
                    password_provider.verification_method,
                    base_path,
                    redirect_to_on_signup or redirect_to,
                ),
                base_path=base_path,
                provider_name=password_provider.name,
            )
            if password_provider
            else None
        ),
        webauthn_form=(
            render.render_webauthn_signup_form(
                base_email_form=base_email_factor_form,
                redirect_to=render.get_webauthn_signup_redirect_url(
                    webauthn_provider.verification_method,
                    base_path,
                    redirect_to_on_signup or redirect_to,
                ),
                base_path=base_path,
                provider_name=webauthn_provider.name,
            )
            if webauthn_provider
            else None
        ),
        magic_link_form=(
            render.render_magic_link_signup_form(
                base_email_form=base_email_factor_form,
                redirect_to=redirect_to_on_signup or redirect_to,
                base_path=base_path,
                provider_name=magic_link_provider.name,
                verification_method=magic_link_provider.verification_method,
            )
            if magic_link_provider
            else None
        ),
        magic_link_verification_method=(
            magic_link_provider.verification_method
            if magic_link_provider
            else 'Link'
        ),
    )

    if email_factor_form:
        email_factor_form += render.bottom_note(
            'Already have an account?', link='Sign in', href='signin'
        )

    oauth_buttons = render.oauth_buttons(
        oauth_providers=oauth_providers,
        label_prefix=('Sign up with' if email_factor_form else 'Continue with'),
        challenge=challenge,
        redirect_to=redirect_to,
        redirect_to_on_signup=redirect_to_on_signup,
        collapsed=email_factor_form is not None and len(oauth_providers) >= 3,
    )

    return render.base_page(
        title=f'Sign up{f" to {app_name}" if app_name else ""}',
        logo_url=logo_url,
        dark_logo_url=dark_logo_url,
        brand_color=brand_color,
        cleanup_search_params=['error', 'email', 'selected_tab'],
        content=f'''
            {render.title('Sign up', app_name=app_name)}
            {render.error_message(error_message)}
            {oauth_buttons}
            {
            render.divider
            if email_factor_form and len(oauth_providers) > 0
            else ''
        }
            {email_factor_form or ''}
            {render.script('webauthn-register') if webauthn_provider else ''}
        ''',
    )


def render_forgot_password_page(
    *,
    base_path: str,
    provider_name: str,
    challenge: str,
    error_message: Optional[str] = None,
    email: Optional[str] = None,
    email_sent: Optional[str] = None,
    # config
    app_name: Optional[str] = None,
    logo_url: Optional[str] = None,
    dark_logo_url: Optional[str] = None,
    brand_color: Optional[str] = None,
) -> bytes:
    if email_sent is not None:
        content = render.success_message(
            f'Password reset email has been sent to <b>{email_sent}</b>'
        )
    else:
        content = f'''
        {render.error_message(error_message)}

        <form method="POST" action="../send-reset-email">
          <input type="hidden" name="provider" value="{provider_name}" />
          <input type="hidden" name="challenge" value="{challenge}" />
          <input type="hidden" name="redirect_on_failure" value="{
            base_path
        }/ui/forgot-password?challenge={challenge}" />
          <input type="hidden" name="redirect_to" value="{
            base_path
        }/ui/forgot-password?challenge={challenge}" />
          <input type="hidden" name="reset_url" value="{
            base_path
        }/ui/reset-password" />

          <label for="email">Email</label>
          <input id="email" name="email" type="email" value="{email or ''}" />

          {render.button('Send Reset Email')}
        </form>
        '''

    return render.base_page(
        title=f'Reset password{f" for {app_name}" if app_name else ""}',
        logo_url=logo_url,
        dark_logo_url=dark_logo_url,
        brand_color=brand_color,
        cleanup_search_params=['error', 'email', 'email_sent'],
        content=f'''
            {render.title('Reset password', join='for', app_name=app_name)}
            {content}
            {render.bottom_note("Back to", link="Sign In", href="signin")}
        ''',
    )


def render_reset_password_page(
    *,
    base_path: str,
    provider_name: str,
    is_valid: bool,
    redirect_to: str,
    challenge: Optional[str] = None,
    reset_token: Optional[str] = None,
    error_message: Optional[str] = None,
    is_code_flow: bool = False,
    email: Optional[str] = None,
    # config
    app_name: Optional[str] = None,
    logo_url: Optional[str] = None,
    dark_logo_url: Optional[str] = None,
    brand_color: Optional[str] = None,
) -> bytes:
    if not is_valid and challenge is None:
        content = render.error_message(
            f'''Reset token is invalid, challenge string is missing. Please
            return to the app, and attempt to log in again.''',
            False,
        )
    elif not is_valid and challenge is not None:
        content = render.error_message(
            f'''Reset token is invalid, it may have expired.
            <a href="forgot-password?challenge={challenge}">
              Try sending another reset email
            </a>''',
            False,
        )
    elif is_code_flow and email:
        content = f'''
            {render.error_message(error_message)}
            <p>We've sent a 6-digit reset code to <strong>{
            html.escape(email)
        }</strong></p>
            {
            render.code_input_form(
                action="../reset-password",
                email=email,
                provider=provider_name,
                redirect_to=redirect_to,
                redirect_on_failure=f"{base_path}/ui/reset-password?code=true&email={html.escape(email)}",
                label="Enter reset code",
                button_text="Reset Password",
                additional_fields='''
                    <label for="password">New Password</label>
                    <input
                        id="password"
                        name="password"
                        type="password"
                        required
                    />
                ''',
                challenge=challenge,
            )
        }
        '''
    else:
        content = f'''
        {render.error_message(error_message)}

        <form method="POST" action="../reset-password">
          <input type="hidden" name="provider" value="{provider_name}" />
          <input type="hidden" name="reset_token" value="{reset_token}" />
          <input type="hidden" name="redirect_on_failure" value="{
            base_path
        }/ui/reset-password" />
          <input type="hidden" name="redirect_to" value="{redirect_to}" />

          <label for="password">New Password</label>
          <input id="password" name="password" type="password" />

          {render.button('Reset Password')}
        </form>'''

    return render.base_page(
        title=f'Reset password{f" for {app_name}" if app_name else ""}',
        logo_url=logo_url,
        dark_logo_url=dark_logo_url,
        brand_color=brand_color,
        cleanup_search_params=['error'],
        content=f'''
            {render.title('Reset password', join='for', app_name=app_name)}
            {content}
        ''',
    )


def render_email_verification_page(
    *,
    is_valid: bool,
    error_messages: list[str],
    verification_token: Optional[str] = None,
    # config
    app_name: Optional[str] = None,
    logo_url: Optional[str] = None,
    dark_logo_url: Optional[str] = None,
    brand_color: Optional[str] = None,
) -> bytes:
    resend_url = None
    if verification_token:
        verification_token = html.escape(verification_token)
        resend_url = (
            f"resend-verification?verification_token={verification_token}"
        )
    if not is_valid:
        messages = ''.join(
            [render.error_message(error) for error in error_messages]
        )
        content = f'''
            {messages}
            {
            (
                f'<a href="{resend_url}">Try sending another verification'
                'email</a>'
            )
            if resend_url
            else ''
        }
            '''
    else:
        content = '''
        Email has been successfully verified. You may now
        <a href="signin">sign in</a>
        '''

    return render.base_page(
        title=f'Verify email{f" for {app_name}" if app_name else ""}',
        logo_url=logo_url,
        dark_logo_url=dark_logo_url,
        brand_color=brand_color,
        cleanup_search_params=['error'],
        content=f'''
            {render.title('Verify email', join='for', app_name=app_name)}
            {content}
        ''',
    )


def render_email_verification_expired_page(
    verification_token: str,
    # config
    app_name: Optional[str] = None,
    logo_url: Optional[str] = None,
    dark_logo_url: Optional[str] = None,
    brand_color: Optional[str] = None,
) -> bytes:
    verification_token = html.escape(verification_token)
    content = render.error_message(
        f'''
        Your verification token has expired.
        <a href="resend-verification?verification_token={verification_token}">
            Click here to resend the verification email
        </a>
        ''',
        False,
    )

    return render.base_page(
        title=f'Verification expired{f" for {app_name}" if app_name else ""}',
        logo_url=logo_url,
        dark_logo_url=dark_logo_url,
        brand_color=brand_color,
        cleanup_search_params=['error'],
        content=f'''
            {
            render.title('Verification expired', join='for', app_name=app_name)
        }
            {content}
        ''',
    )


def render_verify_page(
    *,
    base_path: str,
    email: Optional[str] = None,
    provider: Optional[str] = None,
    is_code_flow: bool = False,
    error_message: Optional[str] = None,
    challenge: Optional[str] = None,
    # config
    redirect_to: str,
    app_name: Optional[str] = None,
    logo_url: Optional[str] = None,
    dark_logo_url: Optional[str] = None,
    brand_color: Optional[str] = None,
) -> bytes:
    """Renders verification page that handles both link and code flows."""

    if is_code_flow and email and provider:
        content = f'''
            {render.error_message(error_message)}
            <p>We've sent a 6-digit verification code to <strong>{
            html.escape(email)
        }</strong></p>
            {
            render.code_input_form(
                action="../verify",
                email=email,
                provider=provider,
                redirect_to=redirect_to,
                redirect_on_failure=f"{base_path}/ui/verify?code=true&email={html.escape(email)}&provider={provider}",
                label="Enter verification code",
                button_text="Verify Email",
                challenge=challenge,
            )
        }
        '''
    else:
        content = render.success_message(
            "A verification link has been sent to your email. Please check "
            "your email and click the link to verify your account."
        )

    return render.base_page(
        title=f'Verify email{f" for {app_name}" if app_name else ""}',
        logo_url=logo_url,
        dark_logo_url=dark_logo_url,
        brand_color=brand_color,
        cleanup_search_params=['error'],
        content=f'''
            {render.title('Verify email', join='for', app_name=app_name)}
            {content}
        ''',
    )


def render_resend_verification_done_page(
    *,
    is_valid: bool,
    verification_token: Optional[str] = None,
    # config
    app_name: Optional[str] = None,
    logo_url: Optional[str] = None,
    dark_logo_url: Optional[str] = None,
    brand_color: Optional[str] = None,
) -> bytes:
    if verification_token is None:
        content = render.error_message(
            f"""
            Missing verification token, please follow the link provided in the
            original email, or on the signin page.
            """,
            False,
        )
    else:
        verification_token = html.escape(verification_token)
        if is_valid:
            content = f'''
            Your verification email has been resent. Please check your email.
            '''
        else:
            content = f'''
            Unable to resend verification email. Please try again.
            '''

    return render.base_page(
        title=(
            f'Email verification resent{f" for {app_name}" if app_name else ""}'
        ),
        logo_url=logo_url,
        dark_logo_url=dark_logo_url,
        brand_color=brand_color,
        cleanup_search_params=['error'],
        content=f'''
            {
            render.title(
                'Email verification resent', join='for', app_name=app_name
            )
        }
            {content}
        ''',
    )


def render_magic_link_sent_page(
    *,
    app_name: Optional[str] = None,
    logo_url: Optional[str] = None,
    dark_logo_url: Optional[str] = None,
    brand_color: Optional[str] = None,
    is_code_flow: bool = False,
    email: Optional[str] = None,
    base_path: Optional[str] = None,
    challenge: Optional[str] = None,
    callback_url: Optional[str] = None,
    error_message: Optional[str] = None,
) -> bytes:
    if is_code_flow and email and base_path:
        content = f'''
            {render.error_message(error_message)}
            <p>We've sent a 6-digit sign-in code to <strong>{
            html.escape(email)
        }</strong></p>
            {
            render.code_input_form(
                action="../magic-link/authenticate",
                email=email,
                provider="builtin::local_magic_link",
                redirect_to=f"{base_path}/ui/magic-link-sent",
                redirect_on_failure=f"{base_path}/ui/magic-link-sent?code=true&email={html.escape(email)}",
                label="Enter sign-in code",
                button_text="Sign In",
                challenge=challenge,
                additional_fields=(
                    f'<input type="hidden" name="callback_url" '
                    f'value="{html.escape(callback_url or "")}" />'
                )
                if callback_url
                else "",
            )
        }
        '''
        title = f'Sign in code sent{f" for {app_name}" if app_name else ""}'
        page_title = 'Sign in code sent'
    else:
        content = render.success_message(
            "A sign in link has been sent to your email. Please check your "
            "email."
        )
        title = f'Sign in link sent{f" for {app_name}" if app_name else ""}'
        page_title = 'Sign in link sent'

    return render.base_page(
        title=title,
        logo_url=logo_url,
        dark_logo_url=dark_logo_url,
        brand_color=brand_color,
        cleanup_search_params=['error'],
        content=f'''
            {render.title(page_title, join='for', app_name=app_name)}
            {content}
        ''',
    )


# emails


def render_password_reset_email(
    *,
    to_addr: str,
    reset_url: str,
    app_name: Optional[str] = None,
    logo_url: Optional[str] = None,
    dark_logo_url: Optional[str] = None,
    brand_color: Optional[str] = render.DEFAULT_BRAND_COLOR,
) -> email.message.EmailMessage:
    brand_color = brand_color or render.DEFAULT_BRAND_COLOR
    msg = email.message.EmailMessage()
    msg["To"] = to_addr
    msg["Subject"] = "Reset password"
    plain_text_content = f"""
Somebody requested a new password for the {app_name or ''} account associated
with {to_addr}.

Please paste the following URL into your browser address bar to verify your
email address:

{reset_url}
        """
    html_content = f"""
<tr>
  <td
    style="
      direction: ltr;
      font-size: 0px;
      padding: 20px 0;
      padding-bottom: 20px;
      padding-top: 20px;
      text-align: center;
    "
  >
    <!--[if mso | IE]><table role="presentation" border="0" cellpadding="0" cellspacing="0"><tr><td class="" style="vertical-align:middle;width:600px;" ><![endif]-->
    <div
      class="mj-column-per-100 mj-outlook-group-fix"
      style="
        font-size: 0px;
        text-align: left;
        direction: ltr;
        display: inline-block;
        vertical-align: middle;
        width: 100%;
      "
    >
      <table
        border="0"
        cellpadding="0"
        cellspacing="0"
        role="presentation"
        style="vertical-align: middle"
        width="100%"
      >
        <tbody>
          <tr>
            <td
              align="left"
              style="
                font-size: 0px;
                padding: 10px 25px;
                padding-top: 50px;
                word-break: break-word;
              "
            >
              <div
                style="
                  font-family: open Sans Helvetica, Arial, sans-serif;
                  font-size: 16px;
                  line-height: 1;
                  text-align: left;
                  color: #000000;
                "
              >
                Somebody requested a new password for the {app_name or ''}
                account associated with {to_addr}.
              </div>
            </td>
          </tr>
          <tr>
            <td
              align="left"
              style="
                font-size: 0px;
                padding: 10px 25px;
                word-break: break-word;
              "
            >
              <div
                style="
                  font-family: open Sans Helvetica, Arial, sans-serif;
                  font-size: 16px;
                  line-height: 1;
                  text-align: left;
                  color: #000000;
                "
              >
                No changes have been made to your account yet.
              </div>
            </td>
          </tr>
          <tr>
            <td
              align="left"
              style="
                font-size: 0px;
                padding: 10px 25px;
                word-break: break-word;
              "
            >
              <div
                style="
                  font-family: open Sans Helvetica, Arial, sans-serif;
                  font-size: 16px;
                  line-height: 1;
                  text-align: left;
                  color: #000000;
                "
              >
                You can reset your password by clicking the button below:
              </div>
            </td>
          </tr>
          <tr>
            <td
              align="center"
              vertical-align="middle"
              style="
                font-size: 0px;
                padding: 10px 25px;
                word-break: break-word;
              "
            >
              <table
                border="0"
                cellpadding="0"
                cellspacing="0"
                role="presentation"
                style="border-collapse: separate; line-height: 100%"
              >
                <tr>
                  <td
                    align="center"
                    bgcolor="#{brand_color}"
                    role="presentation"
                    style="
                      border: none;
                      border-radius: 4px;
                      cursor: auto;
                      mso-padding-alt: 10px 25px;
                      background: #{brand_color};
                    "
                    valign="middle"
                  >
                    <a
                      href="{reset_url}"
                      style="
                        display: inline-block;
                        background: #{brand_color};
                        color: #ffffff;
                        font-family: open Sans Helvetica, Arial, sans-serif;
                        font-size: 18px;
                        font-weight: bold;
                        line-height: 120%;
                        margin: 0;
                        text-decoration: none;
                        text-transform: none;
                        padding: 10px 25px;
                        mso-padding-alt: 0px;
                        border-radius: 4px;
                      "
                      target="_blank"
                    >
                      Reset your password
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td
              align="left"
              style="
                font-size: 0px;
                padding: 10px 25px;
                word-break: break-word;
              "
            >
              <div
                style="
                  font-family: open Sans Helvetica, Arial, sans-serif;
                  font-size: 16px;
                  line-height: 1;
                  text-align: left;
                  color: #000000;
                "
              >
                In case the button didn't work, please paste the following URL
                into your browser address bar:
                <p style="word-break: break-all">{reset_url}</p>
              </div>
            </td>
          </tr>
          <tr>
            <td
              align="left"
              style="
                font-size: 0px;
                padding: 10px 25px;
                word-break: break-word;
              "
            >
              <div
                style="
                  font-family: open Sans Helvetica, Arial, sans-serif;
                  font-size: 16px;
                  line-height: 1;
                  text-align: left;
                  color: #000000;
                "
              >
                If you did not request a new password, please let us know
                immediately by replying to this email.
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </td>
</tr>
    """  # noqa: E501

    msg.set_content(plain_text_content, subtype="plain")
    msg.add_alternative(
        render.base_default_email(
            content=html_content,
            app_name=app_name,
            logo_url=logo_url,
        ),
        subtype="html",
    )
    return msg


def render_verification_email(
    *,
    to_addr: str,
    verify_url: str,
    app_name: Optional[str] = None,
    logo_url: Optional[str] = None,
    dark_logo_url: Optional[str] = None,
    brand_color: Optional[str] = render.DEFAULT_BRAND_COLOR,
) -> email.message.EmailMessage:
    brand_color = brand_color or render.DEFAULT_BRAND_COLOR
    msg = email.message.EmailMessage()
    msg["To"] = to_addr
    msg["Subject"] = (
        f"Verify your email{f' for {app_name}' if app_name else ''}"
    )
    plain_text_content = f"""
Congratulations, you're registered{f' at {app_name}' if app_name else ''}!

Please paste the following URL into your browser address bar to verify your
email address:

{verify_url}
        """
    html_content = f"""
<tr>
  <td
    align="left"
    style="
      font-size: 0px;
      padding: 10px 25px;
      padding-top: 50px;
      word-break: break-word;
    "
  >
    <div
      style="
        font-family:
          open Sans Helvetica,
          Arial,
          sans-serif;
        font-size: 16px;
        line-height: 1;
        text-align: left;
        color: #000000;
      "
    >
      Congratulations, you're registered
      {f'at {app_name}' if app_name else ''}!
    </div>
  </td>
</tr>
<tr>
  <td
    align="left"
    style="font-size: 0px; padding: 10px 25px; word-break: break-word"
  >
    <div
      style="
        font-family:
          open Sans Helvetica,
          Arial,
          sans-serif;
        font-size: 16px;
        line-height: 1;
        text-align: left;
        color: #000000;
      "
    >
      Please press the button below to verify your email address:
    </div>
  </td>
</tr>
<tr>
  <td
    align="center"
    vertical-align="middle"
    style="font-size: 0px; padding: 10px 25px; word-break: break-word"
  >
    <table
      border="0"
      cellpadding="0"
      cellspacing="0"
      role="presentation"
      style="border-collapse: separate; line-height: 100%"
    >
      <tr>
        <td
          align="center"
          bgcolor="#{brand_color}"
          role="presentation"
          style="
            border: none;
            border-radius: 4px;
            cursor: auto;
            mso-padding-alt: 10px 25px;
            background: #{brand_color};
          "
          valign="middle"
        >
          <a
            href="{verify_url}"
            style="
              display: inline-block;
              background: #{brand_color};
              color: #ffffff;
              font-family:
                open Sans Helvetica,
                Arial,
                sans-serif;
              font-size: 18px;
              font-weight: bold;
              line-height: 120%;
              margin: 0;
              text-decoration: none;
              text-transform: none;
              padding: 10px 25px;
              mso-padding-alt: 0px;
              border-radius: 4px;
            "
            target="_blank"
          >
            Verify email address
          </a>
        </td>
      </tr>
    </table>
  </td>
</tr>
<tr>
  <td
    align="left"
    style="font-size: 0px; padding: 10px 25px; word-break: break-word"
  >
    <div
      style="
        font-family:
          open Sans Helvetica,
          Arial,
          sans-serif;
        font-size: 16px;
        line-height: 1;
        text-align: left;
        color: #000000;
      "
    >
      In case the button didn't work, please paste the following URL into
      your browser address bar:
      <p style="word-break: break-all">{verify_url}</p>
    </div>
  </td>
</tr>
    """
    msg.set_content(plain_text_content, subtype="plain")
    msg.set_content(
        render.base_default_email(
            content=html_content,
            app_name=app_name,
            logo_url=logo_url,
        ),
        subtype="html",
    )
    return msg


def render_magic_link_email(
    *,
    to_addr: str,
    link: str,
    app_name: Optional[str] = None,
    logo_url: Optional[str] = None,
    dark_logo_url: Optional[str] = None,
    brand_color: Optional[str] = render.DEFAULT_BRAND_COLOR,
) -> email.message.EmailMessage:
    brand_color = brand_color or render.DEFAULT_BRAND_COLOR
    msg = email.message.EmailMessage()
    msg["To"] = to_addr
    msg["Subject"] = f"Sign in{f' to {app_name}' if app_name else ''}"
    plain_text_content = f"""
Please paste the following URL into your browser address bar to be signed into
your account:

{link}
        """
    html_content = f"""
<tr>
  <td
    align="left"
    style="
      font-size: 0px;
      padding: 10px 25px;
      padding-top: 50px;
      word-break: break-word;
    "
  >
    <div
      style="
        font-family:
          open Sans Helvetica,
          Arial,
          sans-serif;
        font-size: 16px;
        line-height: 1;
        text-align: left;
        color: #000000;
      "
    >
      Click the button below to sign in{f' to {app_name}' if app_name else ''}:
    </div>
  </td>
</tr>
<tr>
  <td
    align="center"
    vertical-align="middle"
    style="
      font-size: 0px;
      padding: 10px 25px;
      word-break: break-word;
    "
  >
    <table
      border="0"
      cellpadding="0"
      cellspacing="0"
      role="presentation"
      style="border-collapse: separate; line-height: 100%"
    >
      <tr>
        <td
          align="center"
          bgcolor="#{brand_color}"
          role="presentation"
          style="
            border: none;
            border-radius: 4px;
            cursor: auto;
            mso-padding-alt: 10px 25px;
            background: #{brand_color};
          "
          valign="middle"
        >
          <a
            href="{link}"
            style="
              display: inline-block;
              background: #{brand_color};
              color: #ffffff;
              font-family: open Sans Helvetica, Arial, sans-serif;
              font-size: 18px;
              font-weight: bold;
              line-height: 120%;
              margin: 0;
              text-decoration: none;
              text-transform: none;
              padding: 10px 25px;
              mso-padding-alt: 0px;
              border-radius: 4px;
            "
            target="_blank"
          >
            Sign in
          </a>
        </td>
      </tr>
    </table>
  </td>
</tr>
<tr>
  <td
    align="left"
    style="
      font-size: 0px;
      padding: 10px 25px;
      word-break: break-word;
    "
  >
    <div
      style="
        font-family: open Sans Helvetica, Arial, sans-serif;
        font-size: 16px;
        line-height: 1;
        text-align: left;
        color: #000000;
      "
    >
      In case the button didn't work, please paste the following URL
      into your browser address bar:
      <p style="word-break: break-all">{link}</p>
    </div>
  </td>
</tr>
    """  # noqa: E501

    msg.set_content(plain_text_content, subtype="plain")
    msg.add_alternative(
        render.base_default_email(
            content=html_content,
            app_name=app_name,
            logo_url=logo_url,
        ),
        subtype="html",
    )
    return msg


def render_one_time_code_email(
    *,
    to_addr: str,
    code: str,
    app_name: Optional[str] = None,
    logo_url: Optional[str] = None,
    dark_logo_url: Optional[str] = None,
    brand_color: Optional[str] = render.DEFAULT_BRAND_COLOR,
) -> email.message.EmailMessage:
    """Renders an email containing a one-time verification code."""
    brand_color = brand_color or render.DEFAULT_BRAND_COLOR
    msg = email.message.EmailMessage()
    msg["To"] = to_addr
    msg["Subject"] = (
        f"Your verification code{f' for {app_name}' if app_name else ''}"
    )
    plain_text_content = f"""
Your verification code{f' for {app_name}' if app_name else ''} is:

{code}

This code will expire in 10 minutes.
        """
    html_content = f"""
<tr>
  <td
    align="left"
    style="
      font-size: 0px;
      padding: 10px 25px;
      padding-top: 50px;
      word-break: break-word;
    "
  >
    <div
      style="
        font-family:
          open Sans Helvetica,
          Arial,
          sans-serif;
        font-size: 16px;
        line-height: 1;
        text-align: left;
        color: #000000;
      "
    >
      Your verification code{f' for {app_name}' if app_name else ''} is:
    </div>
  </td>
</tr>
<tr>
  <td
    align="center"
    vertical-align="middle"
    style="
      font-size: 0px;
      padding: 20px 25px;
      word-break: break-word;
    "
  >
    <div
      style="
        font-family: open Sans Helvetica, Arial, sans-serif;
        font-size: 32px;
        font-weight: bold;
        line-height: 1;
        text-align: center;
        color: #{brand_color};
        letter-spacing: 8px;
        padding: 20px;
        border: 2px solid #{brand_color};
        border-radius: 8px;
        background: #f8f9fa;
      "
    >
      {code}
    </div>
  </td>
</tr>
<tr>
  <td
    align="left"
    style="
      font-size: 0px;
      padding: 10px 25px;
      word-break: break-word;
    "
  >
    <div
      style="
        font-family: open Sans Helvetica, Arial, sans-serif;
        font-size: 16px;
        line-height: 1;
        text-align: left;
        color: #000000;
      "
    >
      This code will expire in 10 minutes for your security.
    </div>
  </td>
</tr>
    """  # noqa: E501

    msg.set_content(plain_text_content, subtype="plain")
    msg.add_alternative(
        render.base_default_email(
            content=html_content,
            app_name=app_name,
            logo_url=logo_url,
        ),
        subtype="html",
    )
    return msg


def render_password_reset_code_email(
    *,
    to_addr: str,
    code: str,
    app_name: Optional[str] = None,
    logo_url: Optional[str] = None,
    dark_logo_url: Optional[str] = None,
    brand_color: Optional[str] = render.DEFAULT_BRAND_COLOR,
) -> email.message.EmailMessage:
    """Renders an email containing a one-time code for password reset."""
    brand_color = brand_color or render.DEFAULT_BRAND_COLOR
    msg = email.message.EmailMessage()
    msg["To"] = to_addr
    msg["Subject"] = (
        f"Password reset code{f' for {app_name}' if app_name else ''}"
    )
    plain_text_content = f"""
Your password reset code{f' for {app_name}' if app_name else ''} is:

{code}

This code will expire in 10 minutes. If you didn't request a password reset, you can safely ignore this email.
        """  # noqa: E501
    html_content = f"""
<tr>
  <td
    align="left"
    style="
      font-size: 0px;
      padding: 10px 25px;
      padding-top: 50px;
      word-break: break-word;
    "
  >
    <div
      style="
        font-family:
          open Sans Helvetica,
          Arial,
          sans-serif;
        font-size: 16px;
        line-height: 1;
        text-align: left;
        color: #000000;
      "
    >
      Your password reset code{f' for {app_name}' if app_name else ''} is:
    </div>
  </td>
</tr>
<tr>
  <td
    align="center"
    vertical-align="middle"
    style="
      font-size: 0px;
      padding: 20px 25px;
      word-break: break-word;
    "
  >
    <div
      style="
        font-family: open Sans Helvetica, Arial, sans-serif;
        font-size: 32px;
        font-weight: bold;
        line-height: 1;
        text-align: center;
        color: #{brand_color};
        letter-spacing: 8px;
        padding: 20px;
        border: 2px solid #{brand_color};
        border-radius: 8px;
        background: #f8f9fa;
      "
    >
      {code}
    </div>
  </td>
</tr>
<tr>
  <td
    align="left"
    style="
      font-size: 0px;
      padding: 10px 25px;
      word-break: break-word;
    "
  >
    <div
      style="
        font-family: open Sans Helvetica, Arial, sans-serif;
        font-size: 16px;
        line-height: 1;
        text-align: left;
        color: #000000;
      "
    >
      This code will expire in 10 minutes for your security. If you didn't request a password reset, you can safely ignore this email.
    </div>
  </td>
</tr>
    """  # noqa: E501

    msg.set_content(plain_text_content, subtype="plain")
    msg.add_alternative(
        render.base_default_email(
            content=html_content,
            app_name=app_name,
            logo_url=logo_url,
        ),
        subtype="html",
    )
    return msg
