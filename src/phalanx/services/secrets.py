"""Service to manipulate Phalanx secrets."""

from __future__ import annotations

import json
from base64 import b64decode
from collections import defaultdict
from pathlib import Path

import yaml
from pydantic import SecretStr

from ..exceptions import NoOnepasswordConfigError, UnresolvedSecretsError
from ..models.applications import ApplicationInstance
from ..models.environments import Environment
from ..models.secrets import (
    ResolvedSecret,
    Secret,
    SourceSecretGenerateRules,
    StaticSecrets,
)
from ..storage.config import ConfigStorage
from ..storage.onepassword import OnepasswordStorage
from ..storage.vault import VaultClient, VaultStorage
from ..yaml import YAMLFoldedString

__all__ = ["SecretsService"]


class SecretsService:
    """Service to manipulate Phalanx secrets.

    Parameters
    ----------
    config_storage
        Storage object for the Phalanx configuration.
    onepassword_storage
        Storage object for 1Password.
    vault_storage
        Storage object for Vault.
    """

    def __init__(
        self,
        config_storage: ConfigStorage,
        onepassword_storage: OnepasswordStorage,
        vault_storage: VaultStorage,
    ) -> None:
        self._config = config_storage
        self._onepassword = onepassword_storage
        self._vault = vault_storage

    def audit(
        self,
        env_name: str,
        static_secrets: StaticSecrets | None = None,
    ) -> str:
        """Compare existing secrets to configuration and report problems.

        Parameters
        ----------
        env_name
            Name of the environment to audit.
        static_secrets
            User-provided static secrets.

        Returns
        -------
        str
            Audit report as a text document.
        """
        environment = self._config.load_environment(env_name)
        if not static_secrets:
            static_secrets = self._get_onepassword_secrets(environment)
        vault_client = self._vault.get_vault_client(environment)

        # Retrieve all the current secrets from Vault and resolve all of the
        # secrets.
        secrets = environment.all_secrets()
        vault_secrets = vault_client.get_environment_secrets()
        resolved = self._resolve_secrets(
            secrets=secrets,
            environment=environment,
            vault_secrets=vault_secrets,
            static_secrets=static_secrets,
        )

        # Compare the resolved secrets to the Vault data.
        missing = []
        mismatch = []
        unknown = []
        for app_name, values in resolved.items():
            for key, value in values.items():
                if key not in vault_secrets.get(app_name, {}):
                    missing.append(f"{app_name} {key}")
                    continue
                if value.value:
                    expected = value.value.get_secret_value()
                else:
                    expected = None
                vault = vault_secrets[app_name][key].get_secret_value()
                if expected != vault:
                    mismatch.append(f"{app_name} {key}")
                del vault_secrets[app_name][key]
        unknown = [f"{a} {k}" for a, lv in vault_secrets.items() for k in lv]

        # Generate the textual report.
        report = ""
        if missing:
            report += "Missing secrets:\n• " + "\n• ".join(missing) + "\n"
        if mismatch:
            report += "Incorrect secrets:\n• " + "\n• ".join(mismatch) + "\n"
        if unknown:
            unknown_str = "\n• ".join(unknown)
            report += "Unknown secrets in Vault:\n• " + unknown_str + "\n"
        return report

    def generate_static_template(self, env_name: str) -> str:
        """Generate a template for providing static secrets.

        The template provides space for all static secrets required for a
        given environment. The resulting file, once the values have been
        added, can be used as input to other secret commands instead of an
        external secret source such as 1Password.

        Parameters
        ----------
        env_name
            Name of the environment.

        Returns
        -------
        dict
            YAML template the user can fill out, as a string.
        """
        environment = self._config.load_environment(env_name)
        template: defaultdict[str, dict[str, dict[str, str | None]]]
        template = defaultdict(dict)
        for application in environment.all_applications():
            for secret in application.all_static_secrets():
                template[secret.application][secret.key] = {
                    "description": YAMLFoldedString(secret.description),
                    "value": None,
                }
        return yaml.dump(template, width=72)

    def list_secrets(self, env_name: str) -> list[Secret]:
        """List all required secrets for the given environment.

        Parameters
        ----------
        env_name
            Name of the environment.

        Returns
        -------
        list of Secret
            Secrets required for the given environment.
        """
        environment = self._config.load_environment(env_name)
        return environment.all_secrets()

    def save_onepassword_secrets(self, env_name: str, path: Path) -> None:
        """Generate JSON files of the 1Password secrets for an environment.

        One file per application with secrets will be written to the provided
        path. Each file will be named after the application with ``.json``
        appended, and will contain the secret values for that application.
        Secrets that are required but have no known value will be written as
        null.
        """
        environment = self._config.load_environment(env_name)
        onepassword_secrets = self._get_onepassword_secrets(environment)
        if not onepassword_secrets:
            msg = f"Environment {env_name} not configured to use 1Password"
            raise NoOnepasswordConfigError(msg)
        for app_name, values in onepassword_secrets.items():
            app_secrets = {
                k: v.value.get_secret_value() if v.value else None
                for k, v in values.items()
            }
            with (path / f"{app_name}.json").open("w") as fh:
                json.dump(app_secrets, fh, indent=2)

    def save_vault_secrets(self, env_name: str, path: Path) -> None:
        """Generate JSON files of the Vault secrets for an environment.

        One file per application with secrets will be written to the provided
        path. Each file will be named after the application with ``.json``
        appended, and will contain the secret values for that application.
        Secrets that are required but have no known value will be written as
        null.

        Parameters
        ----------
        env_name
            Name of the environment.
        path
            Output path.
        """
        environment = self._config.load_environment(env_name)
        vault_client = self._vault.get_vault_client(environment)
        vault_secrets = vault_client.get_environment_secrets()
        for app_name, values in vault_secrets.items():
            app_secrets: dict[str, str | None] = {}
            for key, secret in values.items():
                if secret:
                    app_secrets[key] = secret.get_secret_value()
                else:
                    app_secrets[key] = None
            with (path / f"{app_name}.json").open("w") as fh:
                json.dump(app_secrets, fh, indent=2)

    def sync(
        self,
        env_name: str,
        static_secrets: StaticSecrets | None = None,
        *,
        regenerate: bool = False,
        delete: bool = False,
    ) -> None:
        """Synchronize secrets for an environment with Vault.

        Any incorrect secrets will be replaced with the correct value and any
        missing secrets with generate rules will be generated. For generated
        secrets that already have a value in Vault, that value will be kept
        and not replaced.

        Parameters
        ----------
        env_name
            Name of the environment.
        static_secrets
            User-provided static secrets.
        regenerate
            Whether to regenerate any generated secrets.
        delete
            Whether to delete unknown Vault secrets.
        """
        environment = self._config.load_environment(env_name)
        if not static_secrets:
            static_secrets = self._get_onepassword_secrets(environment)
        vault_client = self._vault.get_vault_client(environment)
        secrets = environment.all_secrets()
        vault_secrets = vault_client.get_environment_secrets()

        # Resolve all of the secrets, regenerating if desired.
        resolved = self._resolve_secrets(
            secrets=secrets,
            environment=environment,
            vault_secrets=vault_secrets,
            static_secrets=static_secrets,
            regenerate=regenerate,
        )

        # Replace any Vault secrets that are incorrect.
        for application, values in resolved.items():
            if application not in vault_secrets:
                to_store = {k: v.value for k, v in values.items()}
                vault_client.store_application_secret(application, to_store)
                print("Created Vault secret for", application)
                continue
            vault_app_secrets = vault_secrets[application]
            for key, value in values.items():
                expected = value.value.get_secret_value()
                if key in vault_app_secrets:
                    seen = vault_app_secrets[key].get_secret_value()
                else:
                    seen = None
                if expected != seen:
                    vault_client.update_application_secret(
                        application, key, value.value
                    )
                    print("Updated Vault secret for", application, key)

        # Optionally delete any unrecognized Vault secrets.
        if delete:
            self._clean_vault_secrets(vault_client, vault_secrets, resolved)

    def _clean_vault_secrets(
        self,
        vault_client: VaultClient,
        vault_secrets: dict[str, dict[str, SecretStr]],
        resolved: dict[str, dict[str, ResolvedSecret]],
    ) -> None:
        """Delete any unrecognized Vault secrets.

        Parameters
        ----------
        vault_client
            Client for talking to Vault for this environment.
        vault_secrets
            Current secrets in Vault for this environment.
        resolved
            Resolved secrets for this environment.
        """
        for application, values in vault_secrets.items():
            if application not in resolved:
                print("Deleted Vault secret for", application)
                vault_client.delete_application_secret(application)
                continue
            expected = resolved[application]
            to_delete = set(values.keys()) - set(expected.keys())
            if to_delete:
                for key in to_delete:
                    del values[key]
                vault_client.store_application_secret(application, values)
                for key in sorted(to_delete):
                    print("Deleted Vault secret for", application, key)

    def _get_onepassword_secrets(
        self, environment: Environment
    ) -> StaticSecrets | None:
        """Get static secrets for an environment from 1Password.

        Parameters
        ----------
        environment
            Environment for which to get static secrets.

        Returns
        -------
        dict of StaticSecret or None
            Static secrets for this environment retrieved from 1Password, or
            `None` if this environment doesn't use 1Password.

        Raises
        ------
        NoOnepasswordCredentialsError
            Raised if the environment uses 1Password but no 1Password
            credentials were available in the environment.
        """
        if not environment.onepassword:
            return None
        onepassword = self._onepassword.get_onepassword_client(environment)
        query = {}
        encoded = {}
        for application in environment.all_applications():
            static_secrets = application.all_static_secrets()
            query[application.name] = [s.key for s in static_secrets]
            encoded[application.name] = {
                s.key for s in static_secrets if s.onepassword.encoded
            }
        result = onepassword.get_secrets(query)

        # Fix any secrets that were encoded in base64 in 1Password.
        for app_name, secrets in encoded.items():
            for key in secrets:
                secret = result[app_name][key]
                if secret.value:
                    value = secret.value.get_secret_value().encode()
                    secret.value = SecretStr(b64decode(value).decode())
        return result

    def _resolve_secrets(
        self,
        *,
        secrets: list[Secret],
        environment: Environment,
        vault_secrets: dict[str, dict[str, SecretStr]],
        static_secrets: StaticSecrets | None = None,
        regenerate: bool = False,
    ) -> dict[str, dict[str, ResolvedSecret]]:
        """Resolve the secrets for a Phalanx environment.

        Resolving secrets is the process where the secret configuration is
        resolved using per-environment Helm chart values to generate the list
        of secrets required for a given environment and their values.

        Parameters
        ----------
        secrets
            Secret configuration by application and key.
        environment
            Phalanx environment for which to resolve secrets.
        vault_secrets
            Current values from Vault. These will be used if compatible with
            the secret definitions.
        static_secrets
            User-provided static secrets.
        regenerate
            Whether to regenerate any generated secrets.

        Returns
        -------
        dict
            Resolved secrets by application and secret key.

        Raises
        ------
        UnresolvedSecretsError
            Raised if some secrets could not be resolved.
        """
        if not static_secrets:
            static_secrets = {}
        resolved: defaultdict[str, dict[str, ResolvedSecret]]
        resolved = defaultdict(dict)
        unresolved = list(secrets)
        left = len(unresolved)
        while unresolved:
            secrets = unresolved
            unresolved = []
            for config in secrets:
                vault_values = vault_secrets.get(config.application, {})
                static_values = static_secrets.get(config.application, {})
                static_value = None
                if config.key in static_values:
                    static_value = static_values[config.key].value
                secret = self._resolve_secret(
                    config=config,
                    instance=environment.applications[config.application],
                    resolved=resolved,
                    current_value=vault_values.get(config.key),
                    static_value=static_value,
                    regenerate=regenerate,
                )
                if secret:
                    resolved[secret.application][secret.key] = secret
                else:
                    unresolved.append(config)
            if len(unresolved) >= left:
                raise UnresolvedSecretsError(unresolved)
            left = len(unresolved)
        return resolved

    def _resolve_secret(
        self,
        *,
        config: Secret,
        instance: ApplicationInstance,
        resolved: dict[str, dict[str, ResolvedSecret]],
        current_value: SecretStr | None,
        static_value: SecretStr | None,
        regenerate: bool = False,
    ) -> ResolvedSecret | None:
        """Resolve a single secret.

        Parameters
        ----------
        config
            Configuration of the secret.
        instance
            Application instance owning this secret.
        resolved
            Other secrets for that environment that have already been
            resolved.
        current_value
            Current secret value in Vault, if known.
        static_value
            User-provided static secret value, if any.
        regenerate
            Whether to regenerate any generated secrets.

        Returns
        -------
        ResolvedSecret or None
            Resolved value of the secret, or `None` if the secret cannot yet
            be resolved (because, for example, the secret from which it is
            copied has not yet been resolved).
        """
        value = None

        # See if the value comes from configuration, either hard-coded or via
        # copy or generate rules. If not, it must be a static secret, in which
        # case use the value from a static secret source, if available. If
        # none is available from a static secret source but we have a current
        # value, use that. Only fail if there is no static secret source and
        # no current value.
        if config.value:
            value = config.value
        elif config.copy_rules:
            application = config.copy_rules.application
            other = resolved.get(application, {}).get(config.copy_rules.key)
            if not other:
                return None
            value = other.value
        elif config.generate:
            if current_value and not regenerate:
                value = current_value
            elif isinstance(config.generate, SourceSecretGenerateRules):
                other_key = config.generate.source
                other = resolved.get(config.application, {}).get(other_key)
                if not (other and other.value):
                    return None
                value = config.generate.generate(other.value)
            else:
                value = config.generate.generate()
        else:
            value = static_value or current_value

        # Return the resolved secret.
        if value:
            return ResolvedSecret(
                key=config.key, application=config.application, value=value
            )
        else:
            return None
