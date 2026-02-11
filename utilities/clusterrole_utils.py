"""Utilities for ClusterRole-based migration tests (e.g. ConfigMap/Secret verification)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ocp_resources.config_map import ConfigMap
from ocp_resources.secret import Secret
from simple_logger.logger import get_logger

if TYPE_CHECKING:
    from kubernetes.dynamic import DynamicClient

LOGGER = get_logger(__name__)


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
        client: OpenShift/Kubernetes client.
        source_namespace: Namespace where the ConfigMap was created before migration.
        target_namespace: Namespace where the ConfigMap should exist after migration.
        configmap_name: Name of the ConfigMap.

    Raises:
        AssertionError: If ConfigMap is missing in target or data does not match.
    """
    source_cm = ConfigMap(
        client=client,
        name=configmap_name,
        namespace=source_namespace,
    )
    if not source_cm.exists:
        raise AssertionError(
            f"Source ConfigMap {configmap_name} not found in namespace {source_namespace}"
        )

    target_cm = ConfigMap(
        client=client,
        name=configmap_name,
        namespace=target_namespace,
    )
    assert target_cm.exists, (
        f"ConfigMap {configmap_name} was not migrated to target namespace {target_namespace}"
    )

    source_data = source_cm.instance.data or {}
    target_data = target_cm.instance.data or {}
    assert source_data == target_data, (
        f"ConfigMap {configmap_name} data mismatch: source {source_data} != target {target_data}"
    )
    LOGGER.info(
        f"ConfigMap {configmap_name} verified in target namespace {target_namespace}"
    )


def verify_secret_migrated(
    client: "DynamicClient",
    source_namespace: str,
    target_namespace: str,
    secret_name: str,
) -> None:
    """Verify that a Secret was migrated from source to target namespace.

    Asserts the Secret exists in the target namespace and that its data
    matches the source Secret (compares decoded data).

    Args:
        client: OpenShift/Kubernetes client.
        source_namespace: Namespace where the Secret was created before migration.
        target_namespace: Namespace where the Secret should exist after migration.
        secret_name: Name of the Secret.

    Raises:
        AssertionError: If Secret is missing in target or data does not match.
    """
    source_secret = Secret(
        client=client,
        name=secret_name,
        namespace=source_namespace,
    )
    if not source_secret.exists:
        raise AssertionError(
            f"Source Secret {secret_name} not found in namespace {source_namespace}"
        )

    target_secret = Secret(
        client=client,
        name=secret_name,
        namespace=target_namespace,
    )
    assert target_secret.exists, (
        f"Secret {secret_name} was not migrated to target namespace {target_namespace}"
    )

    source_data = source_secret.instance.data or {}
    target_data = target_secret.instance.data or {}
    assert set(source_data.keys()) == set(target_data.keys()), (
        f"Secret {secret_name} keys mismatch: source {list(source_data)} != target {list(target_data)}"
    )
    for key in source_data:
        assert source_data[key] == target_data[key], (
            f"Secret {secret_name} data for key {key} mismatch between source and target"
        )
    LOGGER.info(
        f"Secret {secret_name} verified in target namespace {target_namespace}"
    )
