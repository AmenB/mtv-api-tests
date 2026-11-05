from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest
from ocp_resources.copy_appliance_template import CopyApplianceTemplate
from ocp_resources.forklift_controller import ForkliftController
from ocp_resources.provider import Provider
from ocp_resources.resource import ResourceEditor
from simple_logger.logger import get_logger

from utilities.resources import create_and_store_resource
from utilities.utils import resolve_providers_json_path

# Same controller object as utilities.copyoffload_constants; kept local so the toehold
# feature does not depend on the copy-offload module.
FORKLIFT_CONTROLLER_NAME = "forklift-controller"

# Template build (libguestfs customize, image upload, vSphere clone) takes minutes; the
# provider's appliance check pod runs only after the template is ready.
COPY_APPLIANCE_TEMPLATE_TIMEOUT = 1800
COPY_APPLIANCE_CHECK_TIMEOUT = 600

TOEHOLD_REQUIRED_CONFIG_KEYS = (
    "datastore",
    "folder",
    "network",
    "resource_pool",
    "base_disk_container_image",
)

LOGGER = get_logger(__name__)


@pytest.fixture(scope="session")
def toehold_config(
    source_provider,
    source_provider_data: dict[str, Any],
    request: pytest.FixtureRequest,
) -> dict[str, Any]:
    """Validate toehold configuration before running toehold tests.

    Args:
        source_provider (BaseProvider): The source provider to validate.
        source_provider_data (dict[str, Any]): Source provider configuration data.
        request (pytest.FixtureRequest): Pytest request object to access CLI options.

    Returns:
        dict[str, Any]: The validated toehold configuration.

    Raises:
        ValueError: If the provider type is not vSphere, the toehold configuration is
            missing, or required toehold parameters are missing.
    """
    providers_path = resolve_providers_json_path(cli_path=request.config.getoption("providers_json"))

    if source_provider.type != Provider.ProviderType.VSPHERE:
        raise ValueError(
            f"Toehold tests require vSphere provider, but got '{source_provider.type}'. "
            f"Check your provider configuration in {providers_path}"
        )

    if "toehold" not in source_provider_data:
        raise ValueError(
            f"Toehold configuration not found in source provider data. Add a 'toehold' section "
            f"to your provider in {providers_path}"
        )

    toehold_config_data: dict[str, Any] = source_provider_data["toehold"]
    missing_params = [param for param in TOEHOLD_REQUIRED_CONFIG_KEYS if not toehold_config_data.get(param)]
    if missing_params:
        raise ValueError(
            f"Missing required toehold parameters in config: {missing_params}. "
            f"Add them to the 'toehold' section in {providers_path}"
        )

    LOGGER.info("Toehold configuration validated successfully")
    return toehold_config_data


@pytest.fixture(scope="class")
def copy_appliance_template(
    ocp_admin_client,
    source_provider,
    toehold_config: dict[str, Any],
    fixture_store: dict[str, Any],
    target_namespace: str,
    mtv_namespace: str,
) -> Generator[CopyApplianceTemplate, None, None]:
    """Create a CopyApplianceTemplate for the source provider and wait until the appliance check passes.

    Enables the copy appliance feature flag on the ForkliftController and patches the provider
    with the copy appliance placement settings; both are restored on teardown. The template
    build (build pod, vSphere template clone) and the provider's CopyApplianceChecked
    condition are the product evidence that the toehold chain is functional.

    Args:
        ocp_admin_client (DynamicClient): OpenShift admin client.
        source_provider (BaseProvider): Source provider instance.
        toehold_config (dict[str, Any]): Validated toehold configuration.
        fixture_store (dict[str, Any]): Session fixture store for resource tracking.
        target_namespace (str): Namespace for the migration resources.
        mtv_namespace (str): Namespace where the ForkliftController is installed.

    Yields:
        CopyApplianceTemplate: The ready CopyApplianceTemplate resource.

    Raises:
        ValueError: If the copy appliance feature flag cannot be enabled.
    """
    feature_editor: ResourceEditor | None = None
    forklift_controller = ForkliftController(
        client=ocp_admin_client,
        name=FORKLIFT_CONTROLLER_NAME,
        namespace=mtv_namespace,
        ensure_exists=True,
    )
    feature_enabled = str(getattr(forklift_controller.instance.spec, "feature_copy_appliance", "false"))
    if feature_enabled != "true":
        LOGGER.info("Enabling feature_copy_appliance on the ForkliftController")
        feature_editor = ResourceEditor(patches={forklift_controller: {"spec": {"feature_copy_appliance": "true"}}})
        feature_editor.update(backup_resources=True)
        forklift_controller.wait_for_condition(
            status=forklift_controller.Condition.Status.TRUE,
            condition=forklift_controller.Condition.Type.RUNNING,
            timeout=300,
        )
        feature_enabled = str(getattr(forklift_controller.instance.spec, "feature_copy_appliance", "false"))
    if feature_enabled != "true":
        raise ValueError("Failed to enable feature_copy_appliance on the ForkliftController")

    settings_editor = ResourceEditor(
        patches={
            source_provider.ocp_resource: {
                "spec": {
                    "settings": {
                        "copyApplianceDatastore": toehold_config["datastore"],
                        "copyApplianceFolder": toehold_config["folder"],
                        "copyApplianceNetwork": toehold_config["network"],
                        "copyApplianceResourcePool": toehold_config["resource_pool"],
                    }
                }
            }
        }
    )
    try:
        settings_editor.update(backup_resources=True)

        template_name = f"{fixture_store['base_resource_name']}-cat"
        copy_appliance_template = create_and_store_resource(
            fixture_store=fixture_store,
            resource=CopyApplianceTemplate,
            client=ocp_admin_client,
            name=template_name,
            namespace=target_namespace,
            provider={"name": source_provider.name, "namespace": target_namespace},
            base_disk={"containerImage": toehold_config["base_disk_container_image"]},
            datastore=toehold_config["datastore"],
            folder=toehold_config["folder"],
            network=toehold_config["network"],
            template_name=template_name,
            builder_image=toehold_config.get("builder_image"),
            resources=_appliance_template_resources(toehold_config=toehold_config),
        )

        LOGGER.info(f"Waiting for CopyApplianceTemplate {template_name} to build")
        copy_appliance_template.wait_for_status(status="Succeeded", timeout=COPY_APPLIANCE_TEMPLATE_TIMEOUT)

        source_provider.ocp_resource.wait_for_condition(
            condition="CopyApplianceChecked",
            status="True",
            timeout=COPY_APPLIANCE_CHECK_TIMEOUT,
        )
        yield copy_appliance_template

    finally:
        settings_editor.restore()
        if feature_editor:
            feature_editor.restore()


def _appliance_template_resources(toehold_config: dict[str, Any]) -> dict[str, int] | None:
    """Build the OVF hardware descriptor override for the appliance template.

    Args:
        toehold_config (dict[str, Any]): Validated toehold configuration.

    Returns:
        dict[str, int] | None: The resources override, or None when neither cpu nor
            memory_mib is configured.
    """
    cpu = toehold_config.get("cpu")
    memory_mib = toehold_config.get("memory_mib")
    if cpu is None and memory_mib is None:
        return None
    resources: dict[str, int] = {}
    if cpu is not None:
        resources["cpu"] = cpu
    if memory_mib is not None:
        resources["memoryMiB"] = memory_mib
    return resources
