"""Utilities for ClusterRole-based migration tests (e.g. ConfigMap/Secret verification)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from ocp_resources.config_map import ConfigMap
from ocp_resources.secret import Secret
from ocp_resources.virtual_machine import VirtualMachine
from simple_logger.logger import get_logger

from utilities.mtv_migration import (
    create_plan_resource,
    execute_migration,
    get_network_migration_map,
    get_storage_migration_map,
)
from utilities.utils import populate_vm_ids

if TYPE_CHECKING:
    from kubernetes.dynamic import DynamicClient

    from libs.base_provider import BaseProvider
    from libs.forklift_inventory import ForkliftInventory
    from libs.providers.openshift import OCPProvider

LOGGER = get_logger(__name__)


def run_clusterrole_migration(
    ocp_admin_client: "DynamicClient",
    fixture_store: dict[str, Any],
    source_provider: "BaseProvider",
    destination_provider: "OCPProvider",
    prepared_plan: dict[str, Any],
    source_provider_inventory: "ForkliftInventory",
    target_namespace: str,
    multus_network_name: dict[str, str],
    cut_over: datetime | None = None,
) -> None:
    """Run the full migration flow for ClusterRole tests: maps, plan, execute.

    Creates StorageMap, NetworkMap, Plan, runs execute_migration, and waits for completion.

    Args:
        ocp_admin_client (DynamicClient): OpenShift/Kubernetes client.
        fixture_store (dict[str, Any]): Fixture store for resource tracking.
        source_provider (BaseProvider): Source provider instance.
        destination_provider (OCPProvider): Token-based OCP destination provider.
        prepared_plan (dict[str, Any]): Plan configuration with virtual_machines list.
        source_provider_inventory (ForkliftInventory): Forklift inventory for the source provider.
        target_namespace (str): Target namespace for migration resources.
        multus_network_name (dict[str, str]): Multus network name mapping.
        cut_over (datetime | None): Optional cutover datetime for warm migrations.

    Raises:
        AssertionError: If migration fails or resources are not created.
    """
    vms = [vm["name"] for vm in prepared_plan["virtual_machines"]]
    storage_map = get_storage_migration_map(
        fixture_store=fixture_store,
        target_namespace=target_namespace,
        source_provider=source_provider,
        destination_provider=destination_provider,
        ocp_admin_client=ocp_admin_client,
        source_provider_inventory=source_provider_inventory,
        vms=vms,
    )
    network_map = get_network_migration_map(
        fixture_store=fixture_store,
        source_provider=source_provider,
        destination_provider=destination_provider,
        multus_network_name=multus_network_name,
        ocp_admin_client=ocp_admin_client,
        target_namespace=target_namespace,
        source_provider_inventory=source_provider_inventory,
        vms=vms,
    )
    populate_vm_ids(prepared_plan, source_provider_inventory)
    plan_resource = create_plan_resource(
        ocp_admin_client=ocp_admin_client,
        fixture_store=fixture_store,
        source_provider=source_provider,
        destination_provider=destination_provider,
        storage_map=storage_map,
        network_map=network_map,
        virtual_machines_list=prepared_plan["virtual_machines"],
        target_namespace=target_namespace,
        warm_migration=prepared_plan.get("warm_migration", False),
    )
    execute_migration(
        ocp_admin_client=ocp_admin_client,
        fixture_store=fixture_store,
        plan=plan_resource,
        target_namespace=target_namespace,
        cut_over=cut_over,
    )


def verify_vms_running(
    ocp_admin_client: "DynamicClient",
    prepared_plan: dict[str, Any],
    target_namespace: str,
) -> None:
    """Assert each VM in the plan is Running in the target namespace.

    Args:
        ocp_admin_client (DynamicClient): OpenShift/Kubernetes client.
        prepared_plan (dict[str, Any]): Plan configuration with virtual_machines list.
        target_namespace (str): Target namespace to check VMs in.

    Raises:
        AssertionError: If any VM is not in Running status.
    """
    for vm_config in prepared_plan["virtual_machines"]:
        vm = VirtualMachine(
            client=ocp_admin_client,
            name=vm_config["name"],
            namespace=target_namespace,
        )
        vm.wait(timeout=300)
        assert vm.instance.status.printableStatus == VirtualMachine.Status.RUNNING, (
            f"VM {vm.name} is not Running after migration. Status: {vm.instance.status.printableStatus}"
        )


def verify_configmap_migrated(
    client: "DynamicClient",
    source_namespace: str,
    target_namespace: str,
    configmap_name: str,
) -> None:
    """Verify that a ConfigMap was migrated from source to target namespace.

    Asserts the ConfigMap exists in the target namespace and that its data
    matches the source ConfigMap.

    Args:
        client (DynamicClient): OpenShift/Kubernetes client.
        source_namespace (str): Namespace where the ConfigMap was created before migration.
        target_namespace (str): Namespace where the ConfigMap should exist after migration.
        configmap_name (str): Name of the ConfigMap.

    Raises:
        AssertionError: If ConfigMap is missing in target or data does not match.
    """
    source_cm = ConfigMap(
        client=client,
        name=configmap_name,
        namespace=source_namespace,
    )
    assert source_cm.exists, f"Source ConfigMap {configmap_name} not found in namespace {source_namespace}"

    target_cm = ConfigMap(
        client=client,
        name=configmap_name,
        namespace=target_namespace,
    )
    assert target_cm.exists, f"ConfigMap {configmap_name} was not migrated to target namespace {target_namespace}"

    source_data = source_cm.instance.data or {}
    target_data = target_cm.instance.data or {}
    assert source_data == target_data, (
        f"ConfigMap {configmap_name} data mismatch: source {source_data} != target {target_data}"
    )
    LOGGER.info(f"ConfigMap {configmap_name} verified in target namespace {target_namespace}")


def verify_secret_migrated(
    client: "DynamicClient",
    source_namespace: str,
    target_namespace: str,
    secret_name: str,
) -> None:
    """Verify that a Secret was migrated from source to target namespace.

    Asserts the Secret exists in the target namespace and that its data
    matches the source Secret (compares raw Secret.data, base64-encoded).

    Args:
        client (DynamicClient): OpenShift/Kubernetes client.
        source_namespace (str): Namespace where the Secret was created before migration.
        target_namespace (str): Namespace where the Secret should exist after migration.
        secret_name (str): Name of the Secret.

    Raises:
        AssertionError: If Secret is missing in target or data does not match.
    """
    source_secret = Secret(
        client=client,
        name=secret_name,
        namespace=source_namespace,
    )
    assert source_secret.exists, f"Source Secret {secret_name} not found in namespace {source_namespace}"

    target_secret = Secret(
        client=client,
        name=secret_name,
        namespace=target_namespace,
    )
    assert target_secret.exists, f"Secret {secret_name} was not migrated to target namespace {target_namespace}"

    source_data = source_secret.instance.data or {}
    target_data = target_secret.instance.data or {}
    assert source_data == target_data, f"Secret {secret_name} data mismatch between source and target"
    LOGGER.info(f"Secret {secret_name} verified in target namespace {target_namespace}")
