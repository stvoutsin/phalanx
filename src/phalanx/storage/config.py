"""Parsing and analysis of Phalanx configuration."""

from __future__ import annotations

import re
from collections import defaultdict
from contextlib import suppress
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from ..constants import HELM_DOCLINK_ANNOTATION
from ..exceptions import (
    ApplicationExistsError,
    InvalidApplicationConfigError,
    InvalidSecretConfigError,
    UnknownEnvironmentError,
)
from ..models.applications import (
    Application,
    ApplicationConfig,
    ApplicationInstance,
    DocLink,
)
from ..models.environments import (
    Environment,
    EnvironmentConfig,
    EnvironmentDetails,
    GafaelfawrScope,
    IdentityProvider,
    PhalanxConfig,
)
from ..models.helm import HelmStarter
from ..models.secrets import ConditionalSecretConfig, Secret

__all__ = ["ConfigStorage"]


def _merge_overrides(
    base: dict[str, Any], overrides: dict[str, Any]
) -> dict[str, Any]:
    """Merge values settings with overrides.

    Parameters
    ----------
    base
        Base settings.
    overrides
        Overrides that should take precedence.

    Returns
    -------
    dict
        Merged dictionary.
    """
    new = base.copy()
    for key, value in overrides.items():
        if key in new:
            if isinstance(new[key], dict) and isinstance(value, dict):
                new[key] = _merge_overrides(new[key], value)
            else:
                new[key] = value
        else:
            new[key] = value
    return new


class ConfigStorage:
    """Analyze Phalanx configuration and convert it to models.

    Parameters
    ----------
    path
        Path to the root of the Phalanx configuration.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    def add_application_setting(self, application: str, setting: str) -> None:
        """Add the setting for a new application to the environments chart.

        Adds a block for a new application to :file:`values.yaml` in the
        environments directory in the correct alphabetical location.

        Parameters
        ----------
        application
            Name of the new application.
        setting
            Setting block for the new application. Indentation will be added.
        """
        key = re.compile(r" +(?P<application>[^:]+): +")
        setting = "\n".join("  " + line for line in setting.split("\n"))

        # Add the new setting in correct alphabetical order. This is the sort
        # of operation that Python is very bad at, so this code is rather
        # tedious and complicated.
        #
        # First, copy the old file to the new file until the start of the
        # applications block is found. Then, capture each block of blank lines
        # and comments leading up to the setting for an application. If that
        # application sorts after the one we're adding, add our setting before
        # that block to the new file, and then add that block and the rest of
        # the file. If it sorts after, add the block to the new file and keep
        # searching. If we fall off the end without finding a setting that
        # sorts alphabetically after ours, add our setting to the end of the
        # file.
        #
        # This makes a lot of assumptions about the structure of the
        # values.yaml file that ideally we wouldn't make, but the alternative
        # requires doing something complicated with ruamel.yaml and inserting
        # a new setting in a specific order. There are no great solutions
        # here if one cares about retaining the alphabetical ordering.
        path = self._path / "environments" / "values.yaml"
        path_new = path.parent / "values.yaml.new"
        old_values = path.read_text().split("\n")
        old_values.reverse()
        with path_new.open("w") as new:
            while old_values:
                line = old_values.pop()
                new.write(line + "\n")
                if line.startswith("applications:"):
                    break
            found = False
            first = True
            block = ""
            while old_values:
                line = old_values.pop()
                m = key.match(line)
                if not m:
                    block += line + "\n"
                    continue
                if m.group("application") == application:
                    raise ApplicationExistsError(application)
                if m.group("application") > application:
                    if first:
                        new.write(setting + "\n\n")
                    else:
                        new.write("\n" + setting + "\n")
                    found = True
                    block += line + "\n"
                    break
                new.write(block + line + "\n")
                block = ""
                first = False
            if block:
                new.write(block)
            if found:
                old_values.reverse()
                new.write("\n".join(old_values))
            else:
                new.write(setting + "\n")
        path_new.rename(path)

    def get_application_chart_path(self, application: str) -> Path:
        """Determine the path to an application Helm chart.

        The application and path may not exist, since this function is also
        used to generate the path to newly-created applications.

        Parameters
        ----------
        application
            Name of the application.

        Returns
        -------
        pathlib.Path
            Path to that application's chart.
        """
        return self._path / "applications" / application

    def get_starter_path(self, starter: HelmStarter) -> Path:
        """Determine the path to a Helm starter template.

        Parameters
        ----------
        starter
            Name of the Helm starter template.

        Returns
        -------
        pathlib.Path
            Path to that Helm starter template.
        """
        return self._path / "starters" / starter.value

    def load_environment(self, environment_name: str) -> Environment:
        """Load the configuration of a Phalanx environment from disk.

        Parameters
        ----------
        environment_name
            Name of the environment.

        Returns
        -------
        Environment
            Environment configuration.

        Raises
        ------
        UnknownEnvironmentError
            Raised if the named environment has no configuration.
        """
        config = self.load_environment_config(environment_name)
        applications = [
            self._load_application_config(a)
            for a in config.enabled_applications
        ]
        instances = {
            a.name: self._resolve_application(a, environment_name)
            for a in applications
        }
        return Environment(
            **config.dict(exclude={"applications"}), applications=instances
        )

    def load_environment_config(
        self, environment_name: str
    ) -> EnvironmentConfig:
        """Load the top-level configuration for a Phalanx environment.

        Unlike `load_environment`, this only loads the top-level environment
        configuration and its list of enabled applications. It does not load
        the configuration for all of the applications themselves.

        Parameters
        ----------
        environment_name
            Name of the environent.

        Returns
        -------
        Environment
            Loaded environment.

        Raises
        ------
        InvalidEnvironmentConfigError
            Raised if the configuration for an environment is invalid.
        UnknownEnvironmentError
            Raised if the named environment has no configuration.
        """
        values_base = self._path / "environments"
        with (values_base / "values.yaml").open() as fh:
            values = yaml.safe_load(fh)
        env_values_path = values_base / f"values-{environment_name}.yaml"
        if not env_values_path.exists():
            raise UnknownEnvironmentError(environment_name)
        with env_values_path.open() as fh:
            env_values = yaml.safe_load(fh)
            values = _merge_overrides(values, env_values)
        return EnvironmentConfig.parse_obj(values)

    def load_phalanx_config(self) -> PhalanxConfig:
        """Load the full Phalanx configuration.

        Used primarily for generating docuemntation.

        Returns
        -------
        PhalanxConfig
            Phalanx configuration for all environments.

        Raises
        ------
        InvalidApplicationConfigError
            Raised if the namespace for the application could not be found.
        InvalidEnvironmentConfigError
            Raised if the configuration for an environment is invalid.
        """
        environments_path = self._path / "environments"
        environments = []
        for values_path in sorted(environments_path.glob("values-*.yaml")):
            environment_name = values_path.stem.removeprefix("values-")
            environments.append(self.load_environment_config(environment_name))

        # Load the configurations of all applications.
        all_applications: set[str] = set()
        enabled_for: defaultdict[str, list[str]] = defaultdict(list)
        for environment in environments:
            for name in environment.enabled_applications:
                enabled_for[name].append(environment.name)
            all_applications.update(environment.applications.keys())
        applications = {}
        for name in all_applications:
            application_config = self._load_application_config(name)
            application = Application(
                active_environments=enabled_for[name],
                **application_config.dict(),
            )
            applications[name] = application

        # Build the environment details, which augments the environment config
        # with some information from Argo CD and Gafaelfawr configuration for
        # that environment.
        environment_details = []
        for environment in environments:
            name = environment.name
            if environment.applications.get("gafaelfawr", False):
                gafaelfawr = self._resolve_application(
                    applications["gafaelfawr"], name
                )
            else:
                gafaelfawr = None
            details = self._build_environment_details(
                environment,
                [applications[a] for a in environment.enabled_applications],
                self._resolve_application(applications["argocd"], name),
                gafaelfawr,
            )
            environment_details.append(details)

        # Return the resulting configuration.
        return PhalanxConfig(
            environments=environment_details,
            applications=sorted(applications.values(), key=lambda a: a.name),
        )

    def write_application_template(self, name: str, template: str) -> None:
        """Write the Argo CD application template for a new application.

        Parameters
        ----------
        name
            Name of the application.
        template
            Contents of the Argo CD application and namespace Helm template
            for the new application.

        Raises
        ------
        ApplicationExistsError
            Raised if the application being created already exists.
        """
        template_name = f"{name}-application.yaml"
        path = self._path / "environments" / "templates" / template_name
        if path.exists():
            raise ApplicationExistsError(name)
        path.write_text(template)

    def _build_environment_details(
        self,
        config: EnvironmentConfig,
        applications: list[Application],
        argocd: ApplicationInstance,
        gafaelfawr: ApplicationInstance | None,
    ) -> EnvironmentDetails:
        """Construct the details of an environment.

        This is the environment configuration enhanced with some configuration
        details from the Argo CD and Gafaelfawr applications.

        Parameters
        ----------
        config
            Configuration for the environment.
        applications
            All enabled applications for that environment.
        argocd
            Argo CD application configuration.
        gafaelfawr
            Gafaelfawr application configuration, if Gafaelfawr is enabled for
            this environment.

        Returns
        -------
        EnvironmentDetails
            Fleshed-out details for that environment.

        Raises
        ------
        InvalidApplicationConfigError
            Raised if the Gafaelfawr or Argo CD configuration is invalid.
        """
        # Public URL of Argo CD (or none for environments like minikube).
        argocd_url = None
        with suppress(KeyError):
            argocd_url = argocd.values["argo-cd"]["server"]["config"]["url"]

        # Argo CD role-based access control configuration.
        argocd_rbac = []
        with suppress(KeyError):
            rbac_config = argocd.values["argo-cd"]["server"]["rbacConfig"]
            rbac_csv = rbac_config["policy.csv"]
            argocd_rbac = [
                [i.strip() for i in line.split(",")]
                for line in rbac_csv.splitlines()
            ]

        # Type of identity provider used for Gafaelfawr.
        if gafaelfawr:
            if gafaelfawr.values["config"]["cilogon"]["clientId"]:
                identity_provider = IdentityProvider.CILOGON
            elif gafaelfawr.values["config"]["github"]["clientId"]:
                identity_provider = IdentityProvider.GITHUB
            elif gafaelfawr.values["config"]["oidc"]["clientId"]:
                identity_provider = IdentityProvider.OIDC
            else:
                raise InvalidApplicationConfigError(
                    "gafaelfawr",
                    "Cannot determine identity provider",
                    environment=config.name,
                )
        else:
            identity_provider = IdentityProvider.NONE

        # Gafaelfawr scopes. Restructure the data to let Pydantic do most of
        # the parsing.
        gafaelfawr_scopes = []
        if gafaelfawr:
            try:
                group_mapping = gafaelfawr.values["config"]["groupMapping"]
                for scope, groups in group_mapping.items():
                    raw = {"scope": scope, "groups": groups}
                    gafaelfawr_scope = GafaelfawrScope.parse_obj(raw)
                    gafaelfawr_scopes.append(gafaelfawr_scope)
            except KeyError as e:
                raise InvalidApplicationConfigError(
                    "gafaelfawr",
                    "No config.groupMapping",
                    environment=config.name,
                ) from e
            except ValidationError as e:
                raise InvalidApplicationConfigError(
                    "gafaelfawr",
                    "Invalid config.groupMapping",
                    environment=config.name,
                ) from e

        # Return the resulting model.
        return EnvironmentDetails(
            **config.dict(exclude={"applications"}),
            applications=applications,
            argocd_url=argocd_url,
            argocd_rbac=argocd_rbac,
            identity_provider=identity_provider,
            gafaelfawr_scopes=sorted(gafaelfawr_scopes, key=lambda s: s.scope),
        )

    def _find_application_namespace(self, application: str) -> str:
        """Determine what namespace an application will be deployed into.

        This information is present in the Argo CD ``Application`` resource,
        which by convention in Phalanx is named :file:`{app}-application.yaml`
        in the :file:`environments/templates` directory.

        Parameters
        ----------
        application
            Name of the application.

        Returns
        -------
        str
            Namespace into which the application will be deployed.

        Raises
        ------
        InvalidApplicationConfigError
            Raised if the namespace for the application could not be found.
        """
        template_path = (
            self._path
            / "environments"
            / "templates"
            / f"{application}-application.yaml"
        )
        template = template_path.read_text()

        # Helm templates are unfortunately not valid YAML, so do this the hard
        # way with a regular expression.
        pattern = (
            r"destination:\n"
            r"\s+namespace:\s*\"?(?P<namespace>[a-zA-Z][\w-]+)\"?\s"
        )
        match = re.search(pattern, template, flags=re.MULTILINE | re.DOTALL)
        if not match:
            msg = f"Namespace not found in {template_path!s}"
            raise InvalidApplicationConfigError(application, msg)
        return match.group("namespace")

    def _is_condition_satisfied(
        self, instance: ApplicationInstance, condition: str | None
    ) -> bool:
        """Evaluate a secret condition on an application instance.

        This is a convenience wrapper around
        `ApplicationInstance.is_is_values_setting_true` that also treats a
        `None` condition parameter as true.

        Parameters
        ----------
        instance
            Application instance for a specific environment.
        condition
            Condition, or `None` if there is no condition.

        Returns
        -------
        bool
            `True` if condition is `None` or corresponds to a values setting
            whose value is true, `False` otherwise.
        """
        if not condition:
            return True
        else:
            return instance.is_values_setting_true(condition)

    def _load_application_config(self, name: str) -> ApplicationConfig:
        """Load the configuration for an application from disk.

        Parameters
        ----------
        name
            Name of the application.

        Returns
        -------
        ApplicationConfig
            Application configuration.
        """
        base_path = self._path / "applications" / name
        with (base_path / "Chart.yaml").open("r") as fh:
            chart = yaml.safe_load(fh)

        # Load main values file.
        values_path = base_path / "values.yaml"
        if values_path.exists():
            with values_path.open("r") as fh:
                values = yaml.safe_load(fh)
        else:
            values = {}

        # Load environment-specific values files.
        environment_values = {}
        for path in base_path.glob("values-*.yaml"):
            env_name = path.stem.removeprefix("values-")
            with path.open("r") as fh:
                env_values = yaml.safe_load(fh)
                if env_values:
                    environment_values[env_name] = env_values

        # Load the secrets configuration.
        secrets_path = base_path / "secrets.yaml"
        secrets = {}
        if secrets_path.exists():
            with secrets_path.open("r") as fh:
                raw_secrets = yaml.safe_load(fh)
            secrets = {
                k: ConditionalSecretConfig.parse_obj(s)
                for k, s in raw_secrets.items()
            }

        # Load the environment-specific secrets configuration.
        environment_secrets = {}
        for path in base_path.glob("secrets-*.yaml"):
            env_name = path.stem[len("secrets-") :]
            with path.open("r") as fh:
                raw_secrets = yaml.safe_load(fh)
            environment_secrets[env_name] = {
                k: ConditionalSecretConfig.parse_obj(s)
                for k, s in raw_secrets.items()
            }

        # Return the resulting application.
        return ApplicationConfig(
            name=name,
            namespace=self._find_application_namespace(name),
            chart=chart,
            doc_links=self._parse_doclinks(chart),
            values=values,
            environment_values=environment_values,
            secrets=secrets,
            environment_secrets=environment_secrets,
        )

    def _parse_doclinks(self, chart: dict[str, Any]) -> list[DocLink]:
        """Parse documentation links from Helm chart annotations.

        We use the ``phalanx.lsst.io/docs`` annotation to store documentation
        links in :file:`Chart.yaml`. This method extracts them.

        Parameters
        ----------
        chart
            Parsed :file:`Chart.yaml` for an application's main chart.

        Returns
        -------
        list of DocLink
            Documentation links, if any.
        """
        key = HELM_DOCLINK_ANNOTATION
        if key in chart.get("annotations", {}):
            links = yaml.safe_load(chart["annotations"][key])
            return [DocLink(**link) for link in links]
        else:
            return []

    def _resolve_application(
        self, application: ApplicationConfig, environment_name: str
    ) -> ApplicationInstance:
        """Resolve an application to its environment-specific configuration.

        Parameters
        ----------
        application
            Application to resolve.
        environment_name
            Name of the environment the application should be configured for.

        Returns
        -------
        ApplicationInstance
            Resolved application.

        Raises
        ------
        InvalidSecretConfigError
            Raised if the secret configuration has conflicting rules.
        """
        # Merge values with any environment overrides.
        env_values = application.environment_values.get(environment_name, {})
        values = _merge_overrides(application.values, env_values)

        # Create an initial application instance without secrets so that we
        # can use its class methods.
        instance = ApplicationInstance(
            name=application.name,
            environment=environment_name,
            chart=application.chart,
            values=values,
        )

        # Merge secrets with any environment secrets.
        secrets = application.secrets
        if environment_name in application.environment_secrets:
            secrets = application.secrets.copy()
            secrets.update(application.environment_secrets[environment_name])

        # Evaluate the conditions on all of the secrets. Both the top-level
        # condition and any conditions on the copy and generate rules will be
        # resolved, so that any subsequent processing based on the instance no
        # longer needs to worry about conditions.
        required_secrets = []
        for key, config in secrets.items():
            if not self._is_condition_satisfied(instance, config.condition):
                continue
            copy = config.copy_rules
            if copy:
                condition = copy.condition
                if not self._is_condition_satisfied(instance, condition):
                    copy = None
            generate = config.generate
            if generate:
                condition = generate.condition
                if not self._is_condition_satisfied(instance, condition):
                    generate = None
            if copy and generate:
                msg = "Copy and generate rules conflict"
                raise InvalidSecretConfigError(instance.name, key, msg)
            secret = Secret(
                application=application.name,
                key=key,
                description=config.description,
                copy_rules=copy,
                generate=generate,
                onepassword=config.onepassword,
                value=config.value,
            )
            required_secrets.append(secret)

        # Add the secrets to the new instance and return it.
        instance.secrets = {
            s.key: s for s in sorted(required_secrets, key=lambda s: s.key)
        }
        return instance
