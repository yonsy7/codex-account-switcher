"""macOS menu bar application using rumps."""

import threading
from pathlib import Path

import rumps
from codex_switcher.config import load_accounts, get_active_account, DEFAULT_CONFIG_PATH
from codex_switcher.core import (
    check_codex_cli,
    import_current_account,
    switch_account,
    add_new_account,
    remove_saved_account,
)
from codex_switcher.usage import fetch_usage_for_account, fetch_active_usage, format_usage


class CodexSwitcherApp(rumps.App):
    def __init__(self):
        icon_path = Path(__file__).parent / "resources" / "icon.png"
        super().__init__("", icon=str(icon_path), template=True, quit_button=None)
        self.config_path = DEFAULT_CONFIG_PATH
        self._usage_cache = {}
        self._usage_items = {}
        self._first_launch()
        self._rebuild_menu()
        self._fetch_all_usage()

    def _first_launch(self):
        if not self.config_path.exists():
            if not check_codex_cli():
                rumps.alert(
                    title="Codex CLI not found",
                    message="Please install Codex CLI before using Codex Switcher.",
                )
                return
            imported = import_current_account(self.config_path)
            if imported:
                rumps.notification(
                    title="Codex Switcher",
                    subtitle="Account imported",
                    message=f"{imported.email} ({imported.subscription_type})",
                )

    def _rebuild_menu(self):
        accounts = load_accounts(self.config_path)
        active = get_active_account(self.config_path)

        self.menu.clear()

        if active:
            header = rumps.MenuItem(f"Active: {active.email} ({active.subscription_type})")
            header.set_callback(None)
            self.menu.add(header)
            self.menu.add(rumps.separator)

        from codex_switcher import keychain
        for acc in accounts:
            has_creds = keychain.read_credentials(f"codex-switcher:{acc.email}") is not None
            if has_creds:
                prefix = "✓ " if acc.active else "  "
                item = rumps.MenuItem(f"{prefix}{acc.email} ({acc.subscription_type})", callback=self._on_account_click)
            else:
                item = rumps.MenuItem(f"  {acc.email} (unavailable)", callback=None)
            item._email = acc.email
            self.menu.add(item)

            if has_creds:
                cached = self._usage_cache.get(acc.email, "Loading...")
                usage_label = rumps.MenuItem(f"      {cached}", callback=None)
                usage_label._email = acc.email
                self._usage_items[acc.email] = usage_label
                self.menu.add(usage_label)

        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("Add account...", callback=self._on_add_account))
        self.menu.add(rumps.MenuItem("Refresh usage", callback=self._on_refresh_usage))

        if accounts:
            remove_menu = rumps.MenuItem("Remove account")
            for acc in accounts:
                remove_item = rumps.MenuItem(acc.email, callback=self._on_remove_account)
                remove_item._email = acc.email
                remove_menu.add(remove_item)
            self.menu.add(remove_menu)

        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("Quit", callback=rumps.quit_application))

    def _on_account_click(self, sender):
        email = sender._email
        active = get_active_account(self.config_path)
        if active and active.email == email:
            return

        try:
            switch_account(email, self.config_path)
            rumps.notification(title="Codex Switcher", subtitle="Account switched", message=email)
        except Exception as e:
            rumps.alert(title="Error", message=str(e))

        self._rebuild_menu()

    def _on_add_account(self, _):
        if not check_codex_cli():
            rumps.alert(
                title="Codex CLI not found",
                message="Please install Codex CLI before adding an account.",
            )
            return

        try:
            result = add_new_account(self.config_path)
            if result:
                rumps.notification(
                    title="Codex Switcher",
                    subtitle="Account added",
                    message=f"{result.email} ({result.subscription_type})",
                )
            else:
                rumps.notification(
                    title="Codex Switcher",
                    subtitle="Cancelled",
                    message="Login was cancelled or failed.",
                )
        except Exception as e:
            rumps.alert(title="Error", message=str(e))

        self._rebuild_menu()

    def _fetch_all_usage(self):
        accounts = load_accounts(self.config_path)
        active = get_active_account(self.config_path)

        def _fetch():
            for acc in accounts:
                if active and acc.email == active.email:
                    usage = fetch_active_usage()
                else:
                    usage = fetch_usage_for_account(acc.email)
                self._usage_cache[acc.email] = format_usage(usage)
            self._update_usage_labels()

        threading.Thread(target=_fetch, daemon=True).start()

    def _update_usage_labels(self):
        for email, item in self._usage_items.items():
            usage_text = self._usage_cache.get(email, "Usage unavailable")
            item.title = f"      {usage_text}"

    def _on_refresh_usage(self, _):
        self._fetch_all_usage()

    def _on_remove_account(self, sender):
        email = sender._email
        active = get_active_account(self.config_path)

        if active and active.email == email:
            rumps.alert(
                title="Cannot remove",
                message="You cannot remove the active account. Switch to another account first.",
            )
            return

        remove_saved_account(email, self.config_path)
        rumps.notification(title="Codex Switcher", subtitle="Account removed", message=email)
        self._rebuild_menu()


def main():
    CodexSwitcherApp().run()


if __name__ == "__main__":
    main()
